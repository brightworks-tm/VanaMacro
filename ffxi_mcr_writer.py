from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ffxi_autotrans import encode_macro_text

LINE_DATA_BYTES = 60
LINE_STRIDE = 61  # includes trailing 0x00 terminator
LINES_PER_MACRO = 6
MACROS_PER_SET = 10
BOOKS_PER_CHARACTER = 40
SIDES = ("ctrl", "alt")

MACRO_RESERVED_PREFIX = 4
MACRO_RESERVED_SUFFIX = 2
MACRO_BLOCK_SIZE = 380
SIDE_BLOCK_SIZE = MACRO_BLOCK_SIZE * MACROS_PER_SET  # 3800 bytes
FILE_HEADER_SIZE = 24
MCR_FILE_SIZE = FILE_HEADER_SIZE + SIDE_BLOCK_SIZE * 2  # 7,624 bytes

TITLE_HEADER_SIZE = 16
TITLE_ENTRY_SIZE = 16
TITLE_FILE_MIN = TITLE_HEADER_SIZE + 20 * TITLE_ENTRY_SIZE
NAME_BYTES = 8


def write_macro_repository(
    repository: Any,
    dest_folder: Path | str,
    template_root: Optional[Path | str] = None,
) -> Dict[str, Path]:
    """
    Serialize MacroRepository-style data into FFXI macro files.

    Args:
        repository: MacroRepository instance or dict with ``books`` payload.
        dest_folder: Output directory for mcr*.dat and mcr.ttl files.
        template_root: Optional folder containing existing mcr files whose
            headers/reserved fields should be preserved as a template.

    Returns:
        Mapping of filename to the written Path.
    """

    dest = Path(dest_folder)
    dest.mkdir(parents=True, exist_ok=True)
    template_base = Path(template_root) if template_root else None

    written: Dict[str, Path] = {}
    books = _book_list(repository)
    book_titles: List[str] = []

    for book_idx in range(BOOKS_PER_CHARACTER):
        book = books[book_idx] if book_idx < len(books) else None
        book_titles.append(_string_value(book, "name"))
        for set_idx in range(MACROS_PER_SET):
            macro_set = _book_set(book, set_idx)
            filename = _set_filename(book_idx, set_idx)
            template = _load_template(
                template_base, filename, MCR_FILE_SIZE, exact_size=MCR_FILE_SIZE
            )
            payload = _render_set(macro_set, template)
            target = dest / filename
            target.write_bytes(payload)
            written[filename] = target

    first_titles = _render_titles(
        book_titles[:20], _load_template(template_base, "mcr.ttl", TITLE_FILE_MIN)
    )
    ttl_path = dest / "mcr.ttl"
    ttl_path.write_bytes(first_titles)
    written["mcr.ttl"] = ttl_path

    second_titles = _render_titles(
        book_titles[20:], _load_template(template_base, "mcr_2.ttl", TITLE_FILE_MIN)
    )
    ttl2_path = dest / "mcr_2.ttl"
    ttl2_path.write_bytes(second_titles)
    written["mcr_2.ttl"] = ttl2_path

    return written


def _book_list(repository: Any) -> List[Any]:
    books = getattr(repository, "books", None)
    if books is None and isinstance(repository, Mapping):
        books = repository.get("books")
    if books is None:
        return []
    if isinstance(books, list):
        return books
    try:
        return list(books)
    except TypeError:
        return []


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


def _book_set(book: Any, idx: int) -> Any:
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


def _load_template(
    base: Optional[Path],
    filename: str,
    minimum: int,
    exact_size: Optional[int] = None,
) -> bytearray:
    data: Optional[bytearray] = None
    if base:
        path = base / filename
        if path.exists():
            data = bytearray(path.read_bytes())
    if exact_size is not None:
        if data is None:
            return bytearray(exact_size)
        if len(data) < exact_size:
            data.extend(b"\x00" * (exact_size - len(data)))
        elif len(data) > exact_size:
            del data[exact_size:]
        return data
    if data is None:
        return bytearray(minimum)
    if len(data) < minimum:
        data.extend(b"\x00" * (minimum - len(data)))
    return data


def _render_set(set_obj: Any, template: bytearray) -> bytes:
    target = template
    for side_index, side in enumerate(SIDES):
        for macro_idx in range(MACROS_PER_SET):
            macro = _set_macro(set_obj, side, macro_idx)
            _write_macro(target, side_index, macro_idx, macro)
    return bytes(target)


def _set_macro(set_obj: Any, side: str, idx: int) -> Any:
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


def _write_macro(buffer: bytearray, key_index: int, slot_index: int, macro: Any) -> None:
    base = FILE_HEADER_SIZE + (key_index * SIDE_BLOCK_SIZE) + (slot_index * MACRO_BLOCK_SIZE)
    line_base = base + MACRO_RESERVED_PREFIX
    lines = _macro_lines(macro)
    for line_idx, line in enumerate(lines):
        offset = line_base + (line_idx * LINE_STRIDE)
        buffer[offset : offset + LINE_STRIDE] = encode_macro_line(line)
    name_offset = line_base + (LINES_PER_MACRO * LINE_STRIDE)
    buffer[name_offset : name_offset + NAME_BYTES] = encode_macro_name(_string_value(macro, "name"))
    end = name_offset + NAME_BYTES
    if end + MACRO_RESERVED_SUFFIX > len(buffer):
        buffer.extend(b"\x00" * (end + MACRO_RESERVED_SUFFIX - len(buffer)))


def encode_macro_line(text: str) -> bytes:
    payload = encode_macro_text(text or "")
    payload = _truncate_payload(payload, LINE_DATA_BYTES)
    line = bytearray(LINE_STRIDE)
    line[: len(payload)] = payload
    return bytes(line)


def _truncate_payload(payload: bytes, limit: int) -> bytes:
    if len(payload) <= limit:
        return payload
    trimmed = bytearray(payload[:limit])
    i = 0
    while i < len(trimmed):
        if trimmed[i] == 0xFD:
            if i + 5 >= len(trimmed):
                del trimmed[i:]
                break
            if trimmed[i + 1] in (0x02, 0x04, 0x07, 0x0A) and trimmed[i + 5] == 0xFD:
                i += 6
                continue
        i += 1
    return bytes(trimmed)


def encode_macro_name(name: str) -> bytes:
    text = name or ""
    data = bytearray(NAME_BYTES)
    encoded = _encode_cp932(text, NAME_BYTES)
    data[: len(encoded)] = encoded
    return bytes(data)


def _encode_cp932(text: str, max_bytes: int) -> bytes:
    result = bytearray()
    for char in text:
        chunk = char.encode("cp932", errors="ignore")
        if not chunk:
            continue
        if len(result) + len(chunk) > max_bytes:
            break
        result.extend(chunk)
    return bytes(result)


def _macro_lines(macro: Any) -> List[str]:
    if macro is None:
        return [""] * LINES_PER_MACRO
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


def _render_titles(titles: Sequence[str], template: bytearray) -> bytes:
    data = template
    base = TITLE_HEADER_SIZE
    for idx in range(20):
        name = titles[idx] if idx < len(titles) else ""
        offset = base + (idx * TITLE_ENTRY_SIZE) + 8
        data[offset : offset + NAME_BYTES] = encode_macro_name(name)
    return bytes(data)


def _set_filename(book_idx: int, set_idx: int) -> str:
    file_index = book_idx * MACROS_PER_SET + set_idx
    return "mcr.dat" if file_index == 0 else f"mcr{file_index}.dat"


__all__ = ["write_macro_repository", "encode_macro_line", "encode_macro_name"]
