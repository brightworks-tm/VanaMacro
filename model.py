from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Literal, Optional, Dict, Any
import datetime
import json
import tempfile

try:
    from ffxi_autotrans import decode_macro_text
except Exception:
    def decode_macro_text(text: str) -> str:  # type: ignore
        return text

Side = Literal["ctrl", "alt"]


def _six_lines(lines: Optional[List[str]]) -> List[str]:
    """Return exactly six lines, padding/truncating as needed."""
    base = ["", "", "", "", "", ""]
    if not lines:
        return list(base)
    normalized: List[str] = []
    for i in range(6):
        if i < len(lines) and lines[i] is not None:
            normalized.append(str(lines[i]).replace("\r\n", "\n").replace("\r", "\n"))
        else:
            normalized.append("")
    return normalized


@dataclass
class Macro:
    name: str = ""
    lines: List[str] = field(default_factory=lambda: [""] * 6)

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "lines": _six_lines(self.lines)}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Macro":
        if not isinstance(data, dict):
            return Macro()
        name = str(data.get("name", ""))
        lines = [decode_macro_text(line) for line in _six_lines(data.get("lines"))]
        return Macro(name=name, lines=lines)

    def clone(self) -> "Macro":
        return Macro(self.name, list(self.lines))


@dataclass
class MacroSet:
    name: str = ""
    ctrl: List[Macro] = field(default_factory=lambda: [Macro() for _ in range(10)])
    alt: List[Macro] = field(default_factory=lambda: [Macro() for _ in range(10)])

    def _target(self, side: Side) -> List[Macro]:
        return self.ctrl if side == "ctrl" else self.alt

    def get(self, side: Side, idx: int) -> Macro:
        return self._target(side)[idx]

    def set(self, side: Side, idx: int, macro: Optional[Macro]) -> None:
        target = self._target(side)
        target[idx] = macro.clone() if isinstance(macro, Macro) else Macro()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "ctrl": [m.to_dict() for m in self.ctrl],
            "alt": [m.to_dict() for m in self.alt],
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "MacroSet":
        if not isinstance(data, dict):
            return MacroSet()
        name = str(data.get("name", ""))

        def _load_list(key: str) -> List[Macro]:
            raw = data.get(key, [{} for _ in range(10)])
            macros = [
                Macro.from_dict(entry) if isinstance(entry, dict) else Macro()
                for entry in raw[:10]
            ]
            while len(macros) < 10:
                macros.append(Macro())
            return macros

        ctrl = _load_list("ctrl")
        alt = _load_list("alt")
        return MacroSet(name=name, ctrl=ctrl, alt=alt)


@dataclass
class MacroBook:
    name: str = ""
    sets: List[MacroSet] = field(default_factory=lambda: [MacroSet() for _ in range(10)])

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "sets": [s.to_dict() for s in self.sets]}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "MacroBook":
        if not isinstance(data, dict):
            return MacroBook()
        name = str(data.get("name", ""))
        raw_sets = data.get("sets", [{} for _ in range(10)])
        sets: List[MacroSet] = [
            MacroSet.from_dict(entry) if isinstance(entry, dict) else MacroSet()
            for entry in raw_sets[:10]
        ]
        while len(sets) < 10:
            sets.append(MacroSet())
        return MacroBook(name=name, sets=sets)


class MacroRepository:
    """Manage 40 books x 10 sets x (ctrl/alt) x 10 macros per slot for a character."""

    VERSION = 1

    def __init__(
        self,
        character_id: str,
        books: Optional[List[MacroBook]] = None,
        base_dir: Optional[Path] = None,
    ) -> None:
        self.character_id = str(character_id)
        self.base_dir = Path(base_dir) if base_dir else Path.cwd() / "macros"
        self.books: List[MacroBook] = books if books is not None else [
            MacroBook() for _ in range(40)
        ]
        self._clipboard: Optional[Macro] = None

    # -------------------------- helpers --------------------------
    @staticmethod
    def _check_index(book_idx: int, set_idx: int, side: Side, macro_idx: int) -> None:
        assert 0 <= book_idx < 40, f"book_idx out of range: {book_idx}"
        assert 0 <= set_idx < 10, f"set_idx out of range: {set_idx}"
        assert side in ("ctrl", "alt"), f"side must be 'ctrl' or 'alt': {side}"
        assert 0 <= macro_idx < 10, f"macro_idx out of range: {macro_idx}"

    @property
    def json_path(self) -> Path:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        return self.base_dir / f"macros_{self.character_id}.json"

    # -------------------------- persistence --------------------------
    def save(self) -> Path:
        payload = {
            "version": self.VERSION,
            "character_id": self.character_id,
            "updated_at": datetime.datetime.now().isoformat(),
            "books": [b.to_dict() for b in self.books],
        }
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        path = self.json_path
        tmp_fd, tmp_path = tempfile.mkstemp(prefix=path.name, dir=str(path.parent))
        try:
            with open(tmp_fd, "w", encoding="utf-8") as handle:
                handle.write(text)
            Path(tmp_path).replace(path)
        finally:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass
        return path

    @classmethod
    def load_or_create(cls, character_id: str, base_dir: Optional[Path] = None) -> "MacroRepository":
        inst = cls(character_id=character_id, base_dir=base_dir)
        path = inst.json_path
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
            if int(raw.get("version", 0)) != cls.VERSION:
                # Future schema migrations can be handled here.
                pass
            books_raw = raw.get("books", [])
            books: List[MacroBook] = []
            for entry in books_raw[:40]:
                books.append(MacroBook.from_dict(entry))
            while len(books) < 40:
                books.append(MacroBook())
            inst.books = books
        else:
            inst.save()
        return inst

    # -------------------------- macro operations --------------------------
    def get_macro(self, book_idx: int, set_idx: int, side: Side, macro_idx: int) -> Macro:
        self._check_index(book_idx, set_idx, side, macro_idx)
        macro_set = self.books[book_idx].sets[set_idx]
        return macro_set.get(side, macro_idx)

    def set_macro(
        self,
        book_idx: int,
        set_idx: int,
        side: Side,
        macro_idx: int,
        name: Optional[str] = None,
        lines: Optional[List[str]] = None,
        save: bool = True,
    ) -> Macro:
        macro = self.get_macro(book_idx, set_idx, side, macro_idx)
        if name is not None:
            macro.name = str(name)
        if lines is not None:
            macro.lines = _six_lines(lines)
        if save:
            self.save()
        return macro

    def clear_macro(
        self, book_idx: int, set_idx: int, side: Side, macro_idx: int, save: bool = True
    ) -> Macro:
        macro = self.get_macro(book_idx, set_idx, side, macro_idx)
        macro.name = ""
        macro.lines = ["", "", "", "", "", ""]
        if save:
            self.save()
        return macro

    def copy_macro(self, book_idx: int, set_idx: int, side: Side, macro_idx: int) -> Macro:
        macro = self.get_macro(book_idx, set_idx, side, macro_idx)
        self._clipboard = macro.clone()
        return self._clipboard

    def can_paste(self) -> bool:
        return self._clipboard is not None

    def paste_macro(
        self, book_idx: int, set_idx: int, side: Side, macro_idx: int, save: bool = True
    ) -> Optional[Macro]:
        if not self._clipboard:
            return None
        pasted = self.set_macro(
            book_idx,
            set_idx,
            side,
            macro_idx,
            name=self._clipboard.name,
            lines=list(self._clipboard.lines),
            save=save,
        )
        return pasted

    def rename_set(self, book_idx: int, set_idx: int, new_name: str, save: bool = True) -> None:
        assert 0 <= book_idx < 40 and 0 <= set_idx < 10
        self.books[book_idx].sets[set_idx].name = str(new_name)
        if save:
            self.save()

    def rename_book(self, book_idx: int, new_name: str, save: bool = True) -> None:
        assert 0 <= book_idx < 40
        self.books[book_idx].name = str(new_name)
        if save:
            self.save()

    def apply_external_snapshot(self, snapshot: Dict[str, Any], save: bool = False) -> None:
        """Replace current books with macros parsed from an external source (e.g. mcr.dat)."""
        books_payload = snapshot.get("books") if isinstance(snapshot, dict) else None
        new_books: List[MacroBook] = []
        if isinstance(books_payload, list):
            for entry in books_payload[:40]:
                new_books.append(MacroBook.from_dict(entry if isinstance(entry, dict) else {}))
        while len(new_books) < 40:
            new_books.append(MacroBook())
        original = getattr(self, "books", [])
        for idx, book in enumerate(new_books):
            if idx < len(original):
                old_book = original[idx]
                if not book.name and old_book.name:
                    book.name = old_book.name
                for set_idx, new_set in enumerate(book.sets):
                    if set_idx < len(old_book.sets):
                        old_set = old_book.sets[set_idx]
                        if not new_set.name and old_set.name:
                            new_set.name = old_set.name
        self.books = new_books
        if save:
            self.save()

    def normalize_autotrans(self, save: bool = True) -> int:
        """全マクロの定型文を現在の言語設定に正規化

        <<Vallation>> → <<ヴァレション>> (言語設定が ja の場合)
        <<スニーク>> → <<Sneak>> (言語設定が en の場合)

        Args:
            save: 正規化後にJSONを保存するかどうか

        Returns:
            変換されたマクロ行の数
        """
        try:
            from ffxi_autotrans import normalize_to_current_language
        except ImportError:
            return 0

        changed_count = 0
        for book in self.books:
            for macro_set in book.sets:
                for macro in macro_set.ctrl + macro_set.alt:
                    for i, line in enumerate(macro.lines):
                        if line:
                            normalized = normalize_to_current_language(line)
                            if normalized != line:
                                macro.lines[i] = normalized
                                changed_count += 1
        if save and changed_count > 0:
            self.save()
        return changed_count


class MacroController:
    """Thin helper that UI code can use without depending on PyQt."""

    def __init__(self, repo: MacroRepository):
        self.repo = repo
        self.book_idx = 0
        self.set_idx = 0
        self.side: Side = "ctrl"
        self.macro_idx = 0

    def read_current_macro(self) -> Dict[str, Any]:
        macro = self.repo.get_macro(self.book_idx, self.set_idx, self.side, self.macro_idx)
        return {"name": macro.name, "lines": list(macro.lines)}

    def write_current_macro(self, name: str, lines: List[str]) -> None:
        self.repo.set_macro(self.book_idx, self.set_idx, self.side, self.macro_idx, name=name, lines=lines)

    def copy_current(self) -> None:
        self.repo.copy_macro(self.book_idx, self.set_idx, self.side, self.macro_idx)

    def paste_current(self) -> bool:
        return self.repo.paste_macro(self.book_idx, self.set_idx, self.side, self.macro_idx) is not None

    def clear_current(self) -> None:
        self.repo.clear_macro(self.book_idx, self.set_idx, self.side, self.macro_idx)


if __name__ == "__main__":
    repository = MacroRepository.load_or_create(character_id="test_char")

    controller = MacroController(repository)
    controller.book_idx = 0
    controller.set_idx = 0
    controller.side = "ctrl"
    controller.macro_idx = 0

    controller.write_current_macro(
        name="MB:Fire",
        lines=["/ma \"Fire VI\" <t>", "/wait 2", "/p MB now!", "", "", ""],
    )

    controller.copy_current()
    controller.macro_idx = 1
    controller.paste_current()

    controller.macro_idx = 0
    controller.clear_current()

    reloaded = MacroRepository.load_or_create(character_id="test_char")
    copied = reloaded.get_macro(0, 0, "ctrl", 1)
    print("Pasted name:", copied.name)
    print("Pasted lines:", copied.lines)
