from __future__ import annotations

import os
import shutil
from pathlib import Path
from datetime import datetime
import configparser
from typing import List, Optional, Tuple

CONFIG_FILE = Path("names.ini")
SECTION = "DisplayNames"
SETTINGS_SECTION = "Settings"

DATA_ROOT = Path("./data")
BACKUP_ROOT = DATA_ROOT / "backup"
EDIT_ROOT = DATA_ROOT / "edit"
EXPORT_ROOT = DATA_ROOT / "export"
FFXI_DOC_ROOT = Path(os.path.expanduser("~")) / "Documents" / "My Games" / "FINAL FANTASY XI" / "USER"
FFXI_USR_ROOT = Path(r"C:\Program Files (x86)\PlayOnline\SquareEnix\FINAL FANTASY XI\USER")
MAX_HISTORY = 5


def _load_cfg() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        cfg.read(CONFIG_FILE, encoding="utf-8")
    if SECTION not in cfg:
        cfg[SECTION] = {}
    return cfg


def get_display_name(folder_id: str) -> str:
    cfg = _load_cfg()
    return cfg[SECTION].get(folder_id, folder_id)


def set_display_name(folder_id: str, display: str) -> None:
    cfg = _load_cfg()
    cfg[SECTION][folder_id] = display
    with CONFIG_FILE.open("w", encoding="utf-8") as handle:
        cfg.write(handle)


def delete_display_name(folder_id: str) -> None:
    cfg = _load_cfg()
    if folder_id in cfg[SECTION]:
        del cfg[SECTION][folder_id]
        with CONFIG_FILE.open("w", encoding="utf-8") as handle:
            cfg.write(handle)


def get_theme() -> str:
    """Gets the saved UI theme."""
    cfg = _load_cfg()
    if SETTINGS_SECTION not in cfg:
        return "Base"
    return cfg[SETTINGS_SECTION].get("Theme", "Base")


def set_theme(theme_name: str) -> None:
    """Saves the UI theme."""
    cfg = _load_cfg()
    if SETTINGS_SECTION not in cfg:
        cfg[SETTINGS_SECTION] = {}
    cfg[SETTINGS_SECTION]["Theme"] = theme_name
    with CONFIG_FILE.open("w", encoding="utf-8") as handle:
        cfg.write(handle)



def ffxi_user_root(mode_override: str = "") -> Path:
    if mode_override == "ffxi_usr":
        return FFXI_USR_ROOT
    if FFXI_DOC_ROOT.exists():
        return FFXI_DOC_ROOT
    if FFXI_USR_ROOT.exists():
        return FFXI_USR_ROOT
    return FFXI_DOC_ROOT


def ensure_local_root() -> Path:
    EDIT_ROOT.mkdir(parents=True, exist_ok=True)
    return EDIT_ROOT


def ensure_export_root(base: Optional[Path] = None) -> Path:
    target = Path(base) if base else EXPORT_ROOT
    target.mkdir(parents=True, exist_ok=True)
    return target


def _resolve_mode_root(mode: str) -> Path:
    if mode == "ffxi":
        return ffxi_user_root()
    if mode == "ffxi_usr":
        return ffxi_user_root("ffxi_usr")
    return ensure_local_root()


def enum_character_ids(mode: str) -> List[str]:
    root = _resolve_mode_root(mode)
    if not root.exists():
        return []
    return sorted([p.name for p in root.iterdir() if p.is_dir()])


def character_folder(mode: str, folder_id: str) -> Path:
    return _resolve_mode_root(mode) / folder_id


def character_export_root(folder_id: str, base: Optional[Path] = None) -> Path:
    root = ensure_export_root(base)
    path = root / folder_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_export_destination(
    folder_id: str,
    base: Optional[Path] = None,
    timestamp: Optional[str] = None,
) -> Path:
    root = character_export_root(folder_id, base)
    token = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = root / token
    suffix = 1
    while candidate.exists():
        candidate = root / f"{token}_{suffix:02d}"
        suffix += 1
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


def list_characters(mode: str) -> List[Tuple[str, str]]:
    ids = enum_character_ids(mode)
    out: List[Tuple[str, str]] = []
    for cid in ids:
        out.append((cid, get_display_name(cid)))
    if not out and mode != "ffxi":
        out = [("sample1", "SampleChar")]
    return out


def backup_and_prepare_edit() -> List[str]:
    """Copy Program Files USER to data/backup + data/edit, keeping limited history."""
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    edit_root = ensure_local_root()

    if not FFXI_USR_ROOT.exists():
        return []

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    generation = BACKUP_ROOT / timestamp
    generation.mkdir(parents=True, exist_ok=True)

    backed: List[str] = []
    for child in FFXI_USR_ROOT.iterdir():
        if child.is_dir():
            shutil.copytree(child, generation / child.name, dirs_exist_ok=True)
            backed.append(child.name)

    tig_file = FFXI_USR_ROOT / "tig.dat"
    if tig_file.exists():
        shutil.copy2(tig_file, generation / tig_file.name)

    histories = sorted([p for p in BACKUP_ROOT.iterdir() if p.is_dir()])
    if len(histories) > MAX_HISTORY:
        for old in histories[:-MAX_HISTORY]:
            shutil.rmtree(old, ignore_errors=True)
    histories = sorted([p for p in BACKUP_ROOT.iterdir() if p.is_dir()])
    if not histories:
        return backed

    # Helper to remove read-only files
    import stat
    def remove_readonly(func, path, _):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    for child in edit_root.iterdir():
        if child.is_dir():
            shutil.rmtree(child, onerror=remove_readonly)
        else:
            try:
                child.unlink()
            except PermissionError:
                os.chmod(child, stat.S_IWRITE)
                child.unlink()

    latest = histories[-1]
    for item in latest.iterdir():
        dest = edit_root / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)

    return backed
