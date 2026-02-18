# CLAUDE.md — VanaMacro Codebase Guide

This document describes the structure, conventions, and workflows for the VanaMacro project. It is intended for AI assistants (and developers) working in this repository.

---

## Project Overview

**VanaMacro** is a Windows desktop application that lets players edit and manage FFXI (Final Fantasy XI) macros outside of the game. It reads FFXI's binary macro files (`mcr*.dat`, `mcr.ttl`), provides a rich PyQt6 UI to edit them, and exports them back to the binary format for the game to consume.

- **Language**: Python 3.13+
- **UI Framework**: PyQt6
- **Platform**: Windows (requires administrator rights to write to the FFXI USER folder)
- **UI languages**: Japanese (default) and English, switchable at runtime
- **Version**: 1.3.0

---

## Repository Layout

```
VanaMacro/
├── main.py              # Application entry point
├── config.py            # Global language/config management (Config class)
├── model.py             # Core data model: Macro, MacroSet, MacroBook, MacroRepository
├── storage.py           # File-system helpers: backup, export dirs, character discovery
├── exporter.py          # High-level export pipeline (JSON → FFXI binary)
├── ffxi_mcr.py          # Parser: FFXI binary mcr*.dat → Python dicts
├── ffxi_mcr_writer.py   # Writer: Python dicts → FFXI binary mcr*.dat
├── ffxi_autotrans.py    # Auto-translate (定型文) encode/decode via SQLite
├── ui.py                # Main window + all UI dialogs (CharacterManageDialog, etc.)
├── ui_editor.py         # Custom macro text editor with syntax highlighting & autocomplete
├── ui_i18n.py           # i18n string table (Japanese/English)
├── ui_settings.py       # Settings dialog (language selection)
├── ui_theme.py          # Three QSS themes: Base (light), Dark, Game (FFXI-inspired)
├── VanaMacro.vbs        # Admin-privilege launcher (double-click to run)
├── requirements.txt     # PyQt6, pykakasi
├── autotrans_data/
│   ├── autotrans.db     # SQLite: auto-translate & item dictionaries (gitignored)
│   ├── resources.db     # SQLite: FFXI commands for editor autocomplete
│   └── tools/
│       ├── sync_auto_tables.py   # Regenerate autotrans.db from Lua source files
│       └── sync_resources.py     # Regenerate resources.db
└── docs/screenshots/    # UI screenshots referenced in README
```

### Gitignored Runtime Directories

These are created at runtime and are not tracked:

| Path | Purpose |
|---|---|
| `macros/` | Per-character JSON macro snapshots (`macros_<id>.json`) |
| `data/backup/` | Timestamped backups of FFXI USER folder (max 5 generations) |
| `data/edit/` | Working copy of latest backup, used as template for export |
| `data/export/<id>/<timestamp>/` | Timestamped export outputs (`.dat`, `.ttl`, manifest, snapshot) |
| `config.json` | Persisted language setting |
| `names.ini` | Character display names and saved theme setting |

---

## Data Model (`model.py`)

The macro hierarchy maps directly to FFXI's internal structure:

```
MacroRepository          ← one per character (40 books)
  └─ MacroBook [0..39]   ← one book (10 sets)
       └─ MacroSet [0..9] ← ctrl side and alt side, each 10 slots
            ├─ ctrl: List[Macro]  [0..9]
            └─ alt:  List[Macro]  [0..9]
                 └─ Macro
                      ├─ name: str      (max 4 CP932 chars → 8 bytes)
                      └─ lines: List[str]  (always exactly 6 lines)
```

**Key rules:**
- `lines` is always exactly 6 elements; use `_six_lines()` to normalise.
- Each line encodes to ≤ 60 bytes in CP932/Shift-JIS (the game enforces this).
- `Side` is the literal type `"ctrl" | "alt"`.

**Persistence:**
- `MacroRepository.save()` writes atomically via a temp-file rename.
- `MacroRepository.load_or_create(character_id)` reads from `macros/macros_<id>.json` or creates an empty repo.
- JSON schema has a `version` field (currently `1`); future migrations go in `load_or_create`.

**MacroController** is a thin helper that wraps `MacroRepository` and tracks the currently-selected `(book_idx, set_idx, side, macro_idx)` — intended to keep UI code from depending on index arithmetic.

---

## Binary Format (`ffxi_mcr.py`, `ffxi_mcr_writer.py`)

### File naming

```python
# book_idx 0-39, set_idx 0-9
file_index = book_idx * 10 + set_idx
filename = "mcr.dat" if file_index == 0 else f"mcr{file_index}.dat"
```

### `.dat` file layout (7,624 bytes each)

```
Offset  Size     Content
0       24       File header (preserved from template)
24      3800     ctrl side  (10 macros × 380 bytes)
3824    3800     alt side   (10 macros × 380 bytes)

Per macro (380 bytes):
  +0     4        Reserved prefix
  +4     6×61     6 lines, each 61 bytes (60 data + 1 null terminator)
  +370   8        Macro name in CP932 (null-padded, max 4 chars)
  +378   2        Reserved suffix
```

### `.ttl` (title) files

- `mcr.ttl` — book names 0–19
- `mcr_2.ttl` — book names 20–39
- Each entry is 16 bytes with the 8-byte name at offset `+8`.

**Templates**: When exporting, the writer reads existing `.dat`/`.ttl` files from the FFXI USER folder (or `data/edit/<id>`) as templates to preserve headers and reserved bytes.

---

## Auto-translate / 定型文 (`ffxi_autotrans.py`)

### Token format

In the binary files, auto-translate phrases are encoded as 6-byte tokens:
```
FD <type> <lang> <hi> <lo> FD
```
Types: `0x02`, `0x04` (general phrases), `0x07`, `0x0A` (item names).

In the UI and JSON, they are represented as `<<phrase name>>` — e.g. `<<ヴァレション>>` or `<<Vallation>>`.

### Key functions

| Function | Description |
|---|---|
| `encode_macro_text(text)` | Convert UI string (with `<<...>>`) to binary bytes |
| `decode_macro_bytes(raw)` | Convert binary bytes to UI string |
| `decode_macro_text(text)` | Decode a CP932 string that may contain binary tokens |
| `load_autotrans_tree()` | Return category/entry tree for the 定型文 picker (cached) |
| `reload_dictionaries()` | Clear all caches after a language change |
| `normalize_to_current_language(text)` | Round-trip encode→decode to normalise phrase language |

### Dictionary (`autotrans.db`)

SQLite database with tables:
- `categories(id, ja, en)` — phrase categories
- `auto_translates(category_id, entry_id, ja, en)` — phrases
- `items(id, ja, en)` — item names

The decoder builds **bilingual** reverse maps so it can encode phrases regardless of the current UI language.

**Regenerating the DB** (after a game update):
1. Place updated `auto_translates.lua` and `items.lua` in `autotrans_data/res/`.
2. Run `python autotrans_data/tools/sync_auto_tables.py`.

---

## Export Pipeline (`exporter.py`)

The `export_character_macros()` function orchestrates the full export:

1. Load `MacroRepository` from `macros/macros_<id>.json`.
2. Resolve a template folder (FFXI USER folder > `data/edit/<id>`).
3. Call `write_macro_repository()` to write all `.dat` and `.ttl` files to a timestamped destination.
4. Optionally copy the source JSON as a snapshot.
5. Write `manifest.json` with paths, timestamps, and verification status.
6. Verify by re-parsing the written files and comparing canonicalised representations.

**Canonicalisation** ensures the comparison accounts for CP932 encoding limits (macro names truncated to 4 chars, lines truncated at 60 bytes).

---

## Storage / File Management (`storage.py`)

| Function | Description |
|---|---|
| `backup_and_prepare_edit()` | Copy FFXI USER folder → `data/backup/<timestamp>`, then refresh `data/edit/` from latest backup. Keeps max 5 backup generations. Called at startup. |
| `ffxi_user_root()` | Resolve FFXI USER path (Documents/My Games first, then Program Files fallback) |
| `list_characters(mode)` | List character IDs and display names. Modes: `"local"`, `"ffxi"`, `"ffxi_usr"` |
| `get_display_name(folder_id)` | Read display name from `names.ini` |
| `set_display_name(folder_id, display)` | Write display name to `names.ini` |
| `get_theme()` / `set_theme(name)` | Read/write theme from `names.ini` |
| `create_export_destination(folder_id)` | Create a timestamped export directory |

---

## Configuration (`config.py`)

`Config` is a classmethod-only singleton that manages language selection.

```python
Config.load()               # read from config.json (called at startup)
Config.save()               # write to config.json
Config.get_language()       # returns "ja" or "en"
Config.set_language("en")   # validates; raises ValueError for unknown langs
Config.is_japanese()        # convenience bool
Config.is_english()         # convenience bool
```

`config.json` is gitignored (user-local). Default language is `"ja"`.

---

## UI Layer

### `ui.py` — Main Window (`VanaMacroUI`)

The main window wires together all components:

- **Toolbar**: Character selector (QComboBox), "FFXIから取込" button, "エクスポートセンター" button
- **Menu bar**: File / Edit / View / Macro / Tools / Help
- **Left pane**: Book list (QListWidget, 40 entries)
- **Top-right**: Set selector (10 QPushButton)
- **Middle-right**: Ctrl/Alt Macro selector (10 × 2 QPushButton)
- **Editor area**: 6-line individual editors + bulk text edit (bidirectionally synced)

Data protection: the UI keeps an in-memory "dirty" state and prompts before discarding unsaved changes on book/character change or app exit.

### `ui_editor.py` — `MacroEditor`

Custom `QTextEdit` subclass providing:
- **Syntax highlighting** (`MacroHighlighter` using `QSyntaxHighlighter`):
  - Commands (`/ma`, `/ja`, etc.) in one colour
  - Target placeholders (`<t>`, `<me>`, etc.) in another
  - Auto-translate brackets (`<<`, `>>`) highlighted
  - Job abilities, magic, weapon skills, pet commands — priority-ordered to avoid overlap
  - 60-byte line-length / Shift-JIS validation with wavy underline on violations
- **Autocomplete**: triggers on `/`, `<`, or Ctrl+Space; uses the same vocabulary as the highlighter to avoid suggesting invalid strings
- **Fullwidth → halfwidth space** conversion on any input method

### `ui_i18n.py` — i18n

All UI strings live in a two-level dict `_TEXTS["ja"]` / `_TEXTS["en"]`. Call:

```python
from ui_i18n import get_text
label = get_text("btn_save")  # uses Config.get_language() internally
```

Adding a new string: add an entry under both `"ja"` and `"en"` keys.

### `ui_theme.py` — Themes

Three QSS stylesheets:
- `"Base"` — light / system-like
- `"Dark"` — VS Code-inspired dark palette
- `"Game"` — warm brown/gold FFXI RPG palette

Apply with:
```python
from ui_theme import apply_theme
apply_theme(app, "Dark")
```

The active theme name is stored on `QApplication` as `vanamacro_theme` property, and persisted to `names.ini` via `storage.set_theme()`.

### `ui_settings.py` — SettingsDialog

Handles language switching:
1. Changes `Config` language and saves.
2. Calls `reload_dictionaries()` to clear cached auto-translate data.
3. Offers to run `MacroRepository.normalize_autotrans()` to convert existing `<<phrases>>` to the new language.
4. Calls back into the main window to refresh the editor and button labels.

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| Ctrl+I | Import from FFXI |
| Ctrl+E | Open Export Center |
| Ctrl+Q | Quit |
| Ctrl+0 | Reset layout |
| Ctrl+S | Save macro |
| Ctrl+Shift+C | Copy macro |
| Ctrl+Shift+V | Paste macro |
| Ctrl+Shift+D | Clear macro |
| Ctrl+T | Open 定型文 list |
| Ctrl+Space | Trigger autocomplete in editor |

---

## Running the Application

**Windows (recommended):**
```
Double-click VanaMacro.vbs   ← launches pythonw.exe with admin rights
```

**Command line (admin prompt required for FFXI USER folder access):**
```bash
python main.py
```

**Install dependencies:**
```bash
pip install -r requirements.txt
# requirements.txt: PyQt6, pykakasi
```

Python 3.13+ is required.

---

## Development Workflows

### Making UI Text Changes

1. Add/edit entries in both `"ja"` and `"en"` dicts in `ui_i18n.py`.
2. Reference them via `get_text("key")` — never hardcode UI strings.

### Adding a New Theme

1. Add a QSS string constant in `ui_theme.py`.
2. Register it in the `THEMES` dict.
3. Add a menu entry in `ui.py` under the View → Theme submenu.

### Modifying the Data Model

- Any schema change to the JSON format requires bumping `MacroRepository.VERSION` and adding migration logic in `load_or_create()`.
- Keep `Macro.lines` always exactly 6 elements — use `_six_lines()` helper.

### Updating Auto-translate Dictionaries

After a FFXI game update:
```bash
# Place updated Lua files in autotrans_data/res/
python autotrans_data/tools/sync_auto_tables.py
# New autotrans.db is generated automatically
```

Note: `autotrans_data/autotrans.db` is gitignored. Only the generation scripts are tracked.

### Export / Import Flow

```
Import (FFXIから取込):
  FFXI USER folder ──→ ffxi_mcr.parse_mcr_dir() ──→ MacroRepository ──→ macros_<id>.json

Export:
  macros_<id>.json ──→ MacroRepository ──→ ffxi_mcr_writer.write_macro_repository()
                    ──→ mcr*.dat + mcr.ttl ──→ (optional) copy to FFXI USER folder
```

**Important**: FFXI reads macro files at character login and writes them back at logout. Always log out first, then export, then log in again.

---

## Key Conventions

1. **CP932 encoding**: All binary macro data uses Windows Shift-JIS (`cp932`). The 60-byte line limit and 8-byte name field are enforced in the writer and validated in the UI editor.

2. **Atomic saves**: `MacroRepository.save()` writes to a temp file then renames — never write directly to the target JSON.

3. **No direct string hardcoding in UI**: Always use `get_text("key")` from `ui_i18n`.

4. **Bilingual auto-translate encoding**: The encoder's reverse lookup includes both `ja` and `en` entries, so `<<Vallation>>` and `<<ヴァレション>>` both encode correctly regardless of UI language.

5. **Optional imports**: `ui.py` wraps all optional module imports (`storage`, `ffxi_mcr`, `exporter`, etc.) in `try/except` so the UI degrades gracefully if a module fails to load.

6. **Template preservation**: When writing `.dat`/`.ttl` files, always pass a template from the FFXI USER folder or `data/edit/` to preserve vendor headers and reserved bytes.

7. **CLAUDE.md tracking**: This file is listed in `.gitignore` by default; if it needs to be tracked, remove the `CLAUDE.md` entry from `.gitignore` and force-add with `git add -f CLAUDE.md`.
