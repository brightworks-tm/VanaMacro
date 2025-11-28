from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ffxi_autotrans import decode_macro_bytes


def _decode_sjis(raw: bytes) -> str:
    if not raw:
        return ""
    return raw.split(b"\x00", 1)[0].decode("cp932", errors="ignore")


def _empty_macro() -> Dict[str, List[str]]:
    return {"name": "", "lines": [""] * 6}


def _read_set_file(path: Path) -> Dict[str, List[Dict[str, List[str]]]]:
    data = path.read_bytes()
    result: Dict[str, List[Dict[str, List[str]]]] = {"ctrl": [], "alt": []}
    for key_index, side in enumerate(("ctrl", "alt")):
        for slot in range(10):
            base = 24 + (key_index * 3800) + (slot * 380)
            if base + 380 > len(data):
                result[side].append(_empty_macro())
                continue
            lines: List[str] = []
            for line_idx in range(6):
                offset = 28 + (key_index * 3800) + (slot * 380) + (line_idx * 61)
                chunk = data[offset : offset + 61]
                lines.append(decode_macro_bytes(chunk))
            name_offset = 28 + (key_index * 3800) + (slot * 380) + 366
            name = _decode_sjis(data[name_offset : name_offset + 8])[:4]
            result[side].append({"name": name, "lines": lines})
    return result


def _set_filename(book_idx: int, set_idx: int) -> str:
    file_index = book_idx * 10 + set_idx
    return "mcr.dat" if file_index == 0 else f"mcr{file_index}.dat"


def _read_book_titles(path: Path, count: int) -> List[str]:
    if not path.exists():
        return []
    data = path.read_bytes()
    titles: List[str] = []
    base = 16
    for idx in range(count):
        offset = base + idx * 16
        if offset + 16 > len(data):
            break
        raw_name = data[offset + 8 : offset + 16]
        titles.append(_decode_sjis(raw_name).strip())
    return titles


def _load_book_titles(folder: Path) -> List[str]:
    titles = [""] * 40
    first = _read_book_titles(folder / "mcr.ttl", 20)
    second = _read_book_titles(folder / "mcr_2.ttl", 20)
    for idx, name in enumerate(first):
        titles[idx] = name
    for idx, name in enumerate(second, start=20):
        titles[idx] = name
    return titles


def parse_mcr_dir(folder: Path) -> Dict[str, Any]:
    """Parse all mcr*.dat files under the character folder."""
    book_titles = _load_book_titles(folder)
    books: List[Dict[str, Any]] = []
    for book_idx in range(40):
        sets: List[Dict[str, Any]] = []
        for set_idx in range(10):
            filename = _set_filename(book_idx, set_idx)
            path = folder / filename
            if path.exists():
                macros = _read_set_file(path)
            else:
                macros = {
                    "ctrl": [_empty_macro() for _ in range(10)],
                    "alt": [_empty_macro() for _ in range(10)],
                }
            sets.append({"name": "", "ctrl": macros["ctrl"], "alt": macros["alt"]})
        title = book_titles[book_idx] if book_idx < len(book_titles) else ""
        books.append({"name": title, "sets": sets})
    return {"books": books}


def parse_mcr_dat(path: Path) -> Optional[Dict[str, Any]]:
    """Compatibility shim for legacy callers."""
    if not path.exists():
        return None
    return parse_mcr_dir(path.parent)


def import_ffxi_macros(folder: Path | str) -> Dict[str, Any]:
    """Public helper for UI code; accepts either str or Path."""
    target = Path(folder)
    return parse_mcr_dir(target)
