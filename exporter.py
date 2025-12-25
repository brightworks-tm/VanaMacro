from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ffxi_autotrans import decode_macro_bytes
from ffxi_mcr import parse_mcr_dir
from ffxi_mcr_writer import encode_macro_line, encode_macro_name, write_macro_repository
from model import MacroRepository
try:
    import storage
except ImportError as e:
    storage = None
    print(f"Warning: Failed to import 'storage' module: {e}")

BOOKS_PER_CHARACTER = 40
SETS_PER_BOOK = 10
MACROS_PER_SET = 10
LINES_PER_MACRO = 6
SIDES = ("ctrl", "alt")


def export_character_macros(
    character_id: str,
    *,
    destination: Optional[Path | str] = None,
    template_folder: Optional[Path | str] = None,
    macros_base: Optional[Path | str] = None,
    include_snapshot: bool = True,
    verify: bool = True,
) -> Dict[str, Any]:
    """
    Export macros for a character into FFXI's mcr*.dat structure.

    Args:
        character_id: Target character identifier.
        destination: Optional explicit directory. When omitted, a timestamped folder
            is created under ``data/export/<character_id>/``.
        template_folder: Directory containing existing mcr files to use as a template.
            Defaults to ``data/edit/<character_id>`` when available.
        macros_base: Directory containing ``macros_<id>.json``. Defaults to ``./macros``.
        include_snapshot: Whether to copy the source JSON into the export folder.
        verify: Whether to reparse the written files and compare against the source.

    Returns:
        Dict with keys ``destination``, ``manifest``, ``written``, and verification info.
    """

    repo = MacroRepository.load_or_create(character_id=character_id, base_dir=macros_base)
    snapshot_payload = {
        "version": repo.VERSION,
        "character_id": repo.character_id,
        "exported_at": datetime.now().isoformat(),
        "books": [book.to_dict() for book in repo.books],
    }

    if destination:
        dest = Path(destination)
        dest.mkdir(parents=True, exist_ok=True)
    else:
        dest = storage.create_export_destination(repo.character_id)

    template_path = _resolve_template_folder(template_folder, repo.character_id)
    written_files = write_macro_repository(repo, dest, template_path)

    snapshot_path = None
    if include_snapshot:
        snapshot_path = dest / f"macros_{repo.character_id}.json"
        with snapshot_path.open("w", encoding="utf-8") as handle:
            json.dump(snapshot_payload, handle, ensure_ascii=False, indent=2)

    manifest: Dict[str, Any] = {
        "character_id": repo.character_id,
        "exported_at": snapshot_payload["exported_at"],
        "destination": str(dest.resolve()),
        "template_source": str(template_path) if template_path else None,
        "source_json": str(repo.json_path),
        "files": sorted(written_files.keys()),
        "snapshot": snapshot_path.name if snapshot_path else None,
    }

    verification_note: Optional[str] = None
    if verify:
        parsed = parse_mcr_dir(dest)
        expected = _canonicalize_books(snapshot_payload)
        actual = _canonicalize_books(parsed)
        verification_note = _diff_canonical(expected, actual)
        manifest["verified"] = verification_note is None
        if verification_note:
            manifest["verification_warning"] = verification_note
    else:
        manifest["verified"] = False
        manifest["verification_warning"] = "Verification skipped"

    manifest_path = dest / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)

    result = {
        "destination": dest,
        "manifest": manifest_path,
        "written": written_files,
        "verified": manifest["verified"],
        "verification_warning": manifest.get("verification_warning"),
    }

    if include_snapshot:
        result["snapshot"] = snapshot_path

    return result


def _resolve_template_folder(
    explicit: Optional[Path | str],
    character_id: str,
) -> Optional[Path]:
    if explicit:
        path = Path(explicit)
        return path if path.exists() else None
    
    # 1. FFXI USER フォルダ (最優先: 最新のヘッダー/チェックサムを保持するため)
    if storage:
        ffxi_folder = storage.ffxi_user_root() / character_id
        if ffxi_folder.exists():
            return ffxi_folder

    # 2. ローカルの編集用フォルダ (バックアップ)
    local_folder = storage.character_folder("local", character_id)
    if local_folder.exists():
        return local_folder
        
    return None


def _canonicalize_books(source: Any) -> List[Dict[str, Any]]:
    books = _extract_books(source)
    normalized: List[Dict[str, Any]] = []
    for book_idx in range(BOOKS_PER_CHARACTER):
        book = books[book_idx] if book_idx < len(books) else None
        sets: List[Dict[str, Any]] = []
        for set_idx in range(SETS_PER_BOOK):
            macro_set = _get_set(book, set_idx)
            sets.append(
                {
                    side: [_canonical_macro(_get_macro(macro_set, side, slot)) for slot in range(MACROS_PER_SET)]
                    for side in SIDES
                }
            )
        normalized.append({"name": _canonical_book_name(book), "sets": sets})
    return normalized


def _canonical_book_name(book: Any) -> str:
    name_bytes = encode_macro_name(_string_value(book, "name"))
    return name_bytes.split(b"\x00", 1)[0].decode("cp932", errors="ignore").strip()


def _canonical_macro(macro: Any) -> Dict[str, Any]:
    if macro is None:
        return {"name": "", "lines": [""] * LINES_PER_MACRO}
    name_bytes = encode_macro_name(_string_value(macro, "name"))
    truncated = name_bytes.split(b"\x00", 1)[0].decode("cp932", errors="ignore")[:4]
    lines = []
    for line in _macro_lines(macro):
        encoded = encode_macro_line(line)
        lines.append(decode_macro_bytes(encoded))
    return {"name": truncated, "lines": lines}


def _macro_lines(macro: Any) -> List[str]:
    lines = getattr(macro, "lines", None)
    if lines is None and isinstance(macro, Mapping):
        lines = macro.get("lines")
    if not isinstance(lines, (list, tuple)):
        lines = []
    normalized: List[str] = []
    for idx in range(LINES_PER_MACRO):
        if idx < len(lines):
            value = lines[idx]
        else:
            value = ""
        if value is None:
            normalized.append("")
        else:
            normalized.append(str(value).replace("\r\n", "\n").replace("\r", "\n"))
    return normalized


def _string_value(source: Any, attr: str) -> str:
    if source is None:
        return ""
    if hasattr(source, attr):
        value = getattr(source, attr)
    elif isinstance(source, Mapping):
        value = source.get(attr, "")
    else:
        value = ""
    return str(value or "")


def _extract_books(source: Any) -> List[Any]:
    if hasattr(source, "books"):
        return list(getattr(source, "books"))
    if isinstance(source, Mapping):
        books = source.get("books", [])
        return list(books) if isinstance(books, Sequence) else list(books or [])
    return []


def _get_set(book: Any, idx: int) -> Any:
    if book is None:
        return None
    sets = getattr(book, "sets", None)
    if sets is None and isinstance(book, Mapping):
        sets = book.get("sets")
    if sets is None:
        return None
    if isinstance(sets, Sequence):
        return sets[idx] if idx < len(sets) else None
    try:
        seq = list(sets)
    except TypeError:
        return None
    return seq[idx] if idx < len(seq) else None


def _get_macro(set_obj: Any, side: str, idx: int) -> Any:
    if set_obj is None:
        return None
    seq = getattr(set_obj, side, None)
    if seq is None and isinstance(set_obj, Mapping):
        seq = set_obj.get(side)
    if seq is None:
        return None
    if isinstance(seq, Sequence):
        return seq[idx] if idx < len(seq) else None
    try:
        seq_list = list(seq)
    except TypeError:
        return None
    return seq_list[idx] if idx < len(seq_list) else None


def _diff_canonical(expected: List[Dict[str, Any]], actual: List[Dict[str, Any]]) -> Optional[str]:
    for book_idx in range(BOOKS_PER_CHARACTER):
        exp_book = expected[book_idx]
        act_book = actual[book_idx] if book_idx < len(actual) else {"name": "", "sets": []}
        if exp_book["name"] != act_book.get("name", ""):
            return f"Book {book_idx} name mismatch ('{exp_book['name']}' vs '{act_book.get('name', '')}')"
        exp_sets = exp_book["sets"]
        act_sets = act_book.get("sets", [])
        for set_idx in range(SETS_PER_BOOK):
            if set_idx >= len(exp_sets) or set_idx >= len(act_sets):
                return f"Book {book_idx} set {set_idx} count mismatch"
            for side in SIDES:
                exp_macros = exp_sets[set_idx][side]
                act_macros = act_sets[set_idx][side]
                for macro_idx in range(MACROS_PER_SET):
                    exp_macro = exp_macros[macro_idx]
                    act_macro = act_macros[macro_idx]
                    if exp_macro["name"] != act_macro["name"]:
                        return (
                            f"Book {book_idx} set {set_idx} {side} macro {macro_idx} "
                            f"name mismatch ('{exp_macro['name']}' vs '{act_macro['name']}')"
                        )
                    exp_lines = exp_macro["lines"]
                    act_lines = act_macro["lines"]
                    for line_idx in range(LINES_PER_MACRO):
                        if exp_lines[line_idx] != act_lines[line_idx]:
                            return (
                                f"Book {book_idx} set {set_idx} {side} macro {macro_idx} line {line_idx} "
                                f"diff ('{exp_lines[line_idx]}' vs '{act_lines[line_idx]}')"
                            )
    return None


__all__ = ["export_character_macros"]
