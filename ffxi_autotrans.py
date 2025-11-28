from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config import Config

_SENTINEL_BYTE = 0xFD
_SENTINEL_CHAR = "\uf8f1"
_TOKEN_TYPES = {0x02, 0x04, 0x07, 0x0A}

_ROOT_DIR = Path(__file__).resolve().parent
_DATA_BASE = _ROOT_DIR / "autotrans_data"
_DB_PATH = _DATA_BASE / "autotrans.db"

_TREE_CACHE: Optional[List[Dict[str, List[str]]]] = None
_LANGUAGE_CODE = 0x01  # Japanese client marker for tokens


def _get_db_connection() -> sqlite3.Connection:
    if not _DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {_DB_PATH}")
    return sqlite3.connect(_DB_PATH)


def _load_general_dictionary() -> Dict[Tuple[int, int], str]:
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        # 言語に応じたカラムを選択
        lang_col = Config.get_language()
        cursor.execute(f"SELECT category_id, entry_id, {lang_col} FROM auto_translates")
        mapping = {}
        for cat, entry, text in cursor.fetchall():
            mapping[(cat, entry)] = text
        conn.close()
        return mapping
    except Exception:
        return {}


def _load_item_dictionary() -> Dict[int, str]:
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        # 言語に応じたカラムを選択
        lang_col = Config.get_language()
        cursor.execute(f"SELECT id, {lang_col} FROM items")
        mapping = {}
        for item_id, text in cursor.fetchall():
            mapping[item_id] = text
        conn.close()
        return mapping
    except Exception:
        return {}


class AutoTranslateDecoder:
    def __init__(self) -> None:
        self._general_map: Optional[Dict[Tuple[int, int], str]] = None
        self._item_map: Optional[Dict[int, str]] = None
        self._general_reverse: Optional[Dict[str, Tuple[int, int]]] = None
        self._item_reverse: Optional[Dict[str, int]] = None

    def _ensure_general(self) -> Dict[Tuple[int, int], str]:
        if self._general_map is None:
            self._general_map = _load_general_dictionary()
            self._general_reverse = None
        return self._general_map

    def _ensure_items(self) -> Dict[int, str]:
        if self._item_map is None:
            self._item_map = _load_item_dictionary()
            self._item_reverse = None
        return self._item_map

    def _ensure_general_reverse(self) -> Dict[str, Tuple[int, int]]:
        if self._general_reverse is None:
            reverse: Dict[str, Tuple[int, int]] = {}
            for key, value in self._ensure_general().items():
                reverse.setdefault(value, key)
            self._general_reverse = reverse
        return self._general_reverse

    def _ensure_item_reverse(self) -> Dict[str, int]:
        if self._item_reverse is None:
            reverse: Dict[str, int] = {}
            for key, value in self._ensure_items().items():
                reverse.setdefault(value, key)
            self._item_reverse = reverse
        return self._item_reverse

    def decode_bytes(self, raw: bytes) -> str:
        # Find null terminator while skipping tokens
        length = len(raw)
        i = 0
        while i < length:
            if raw[i] == 0x00:
                length = i
                break
            # Skip over tokens to avoid splitting on 0x00 inside them
            if (
                raw[i] == _SENTINEL_BYTE
                and i + 5 < length
                and raw[i + 1] in _TOKEN_TYPES
                and raw[i + 5] == _SENTINEL_BYTE
            ):
                i += 6
            else:
                i += 1
        
        chunk = raw[:length]
        if not chunk:
            return ""
        parts: list[str] = []
        buffer = bytearray()
        general_map: Optional[Dict[Tuple[int, int], str]] = None
        item_map: Optional[Dict[int, str]] = None
        i = 0
        while i < length:
            if (
                chunk[i] == _SENTINEL_BYTE
                and i + 5 < length
                and chunk[i + 1] in _TOKEN_TYPES
                and chunk[i + 5] == _SENTINEL_BYTE
            ):
                if general_map is None or item_map is None:
                    general_map = self._ensure_general()
                    item_map = self._ensure_items()
                if buffer:
                    parts.append(buffer.decode("cp932", errors="ignore"))
                    buffer.clear()
                token_text = self._decode_token(chunk[i : i + 6], general_map, item_map)
                if token_text is None:
                    parts.append(chunk[i : i + 6].decode("cp932", errors="ignore"))
                else:
                    parts.append(token_text)
                i += 6
                continue
            buffer.append(chunk[i])
            i += 1
        if buffer:
            parts.append(buffer.decode("cp932", errors="ignore"))
        return "".join(parts)

    def decode_text(self, text: str) -> str:
        if not text or _SENTINEL_CHAR not in text:
            return text
        raw = text.encode("cp932", errors="ignore")
        if not raw:
            return text
        return self.decode_bytes(raw)

    def encode_text(self, text: str) -> bytes:
        """Encode strings containing <<auto-translate>> tokens back into bytes."""
        if not text:
            return b""

        buffer = bytearray()
        idx = 0
        length = len(text)
        while idx < length:
            start = text.find("<<", idx)
            if start == -1:
                buffer.extend(text[idx:].encode("cp932", errors="ignore"))
                break
            if start > idx:
                buffer.extend(text[idx:start].encode("cp932", errors="ignore"))

            end = text.find(">>", start + 2)
            if end == -1:
                buffer.extend(text[start:].encode("cp932", errors="ignore"))
                break

            token_text = text[start + 2 : end]
            token_bytes = self._encode_token(token_text)
            if token_bytes is None:
                buffer.extend(text[start : end + 2].encode("cp932", errors="ignore"))
            else:
                buffer.extend(token_bytes)
            idx = end + 2
        return bytes(buffer)

    def _encode_token(self, token_text: str) -> Optional[bytes]:
        token_text = token_text.strip()
        if not token_text:
            return None

        entry = self._ensure_general_reverse().get(token_text)
        if entry is not None:
            category, value = entry
            return bytes(
                (0xFD, 0x02, _LANGUAGE_CODE, category & 0xFF, value & 0xFF, 0xFD)
            )

        item_id = self._ensure_item_reverse().get(token_text)
        if item_id is not None:
            hi = (item_id >> 8) & 0xFF
            lo = item_id & 0xFF
            if lo == 0 and item_id != 0:
                token_type = 0x0A
                lo_byte = 0x00
            else:
                token_type = 0x07
                lo_byte = lo
            return bytes((0xFD, token_type, 0x00, hi, lo_byte, 0xFD))

        return None

    def _decode_token(
        self,
        token: bytes,
        general_map: Dict[Tuple[int, int], str],
        item_map: Dict[int, str],
    ) -> Optional[str]:
        if not general_map and not item_map:
            return None
        token_type = token[1]
        hi = token[3]
        lo = token[4]
        if token_type in (0x02, 0x04):
            if general_map:
                value = general_map.get((hi, lo)) or general_map.get((token[2], hi))
                if value:
                    return f"<<{value}>>"
            return None
        if token_type in (0x07, 0x0A):
            if not item_map:
                return None
            if token_type == 0x0A:
                item_id = hi << 8
            else:
                item_id = (hi << 8) + lo
            value = item_map.get(item_id)
            if value:
                return f"<<{value}>>"
            return None
        return None


_DECODER = AutoTranslateDecoder()


def decode_macro_bytes(raw: bytes) -> str:
    return _DECODER.decode_bytes(raw)


def decode_macro_text(text: str) -> str:
    return _DECODER.decode_text(text)


def encode_macro_text(text: str) -> bytes:
    return _DECODER.encode_text(text)


def load_autotrans_tree() -> List[Dict[str, List[str]]]:
    global _TREE_CACHE
    if _TREE_CACHE is not None:
        return _TREE_CACHE
    
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        
        # 言語に応じたカラムを選択
        lang_col = Config.get_language()
        
        # カテゴリ取得
        cursor.execute(f"SELECT id, {lang_col} FROM categories ORDER BY id")
        categories = []
        for cat_id, cat_name in cursor.fetchall():
            # エントリ取得
            cursor.execute(f"SELECT {lang_col} FROM auto_translates WHERE category_id = ? ORDER BY entry_id", (cat_id,))
            entries = [row[0] for row in cursor.fetchall()]
            if entries:
                categories.append({"name": cat_name, "entries": entries})
        
        conn.close()
        _TREE_CACHE = categories
        return categories
    except Exception:
        _TREE_CACHE = []
        return _TREE_CACHE


def reload_dictionaries() -> None:
    """辞書をリロード（言語変更時に使用）
    
    言語設定を変更した後、この関数を呼び出すことで
    キャッシュされた辞書データをクリアし、次回アクセス時に
    新しい言語でデータを再読み込みします。
    """
    global _TREE_CACHE
    _TREE_CACHE = None
    _DECODER._general_map = None
    _DECODER._item_map = None
    _DECODER._general_reverse = None
    _DECODER._item_reverse = None


__all__ = [
    "decode_macro_bytes",
    "decode_macro_text",
    "encode_macro_text",
    "AutoTranslateDecoder",
    "load_autotrans_tree",
    "reload_dictionaries",
]
