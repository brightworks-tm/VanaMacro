from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QListWidget, QListWidgetItem, QDialog, QLineEdit, QTextEdit, QLabel,
    QSplitter, QComboBox, QInputDialog, QMessageBox, QCheckBox, QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, QEvent, QSettings
from PyQt6.QtGui import QAction, QActionGroup, QFontMetrics, QKeySequence, QTextCursor
import copy
import json
import os
import subprocess
import sys
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from ui_i18n import get_text


# ---- オプション依存（存在しなくても動作するように） ----
try:
    import storage
except Exception:
    storage = None

try:
    import ffxi_mcr
except Exception:
    ffxi_mcr = None

try:
    from ui_theme import apply_theme, THEMES
except Exception:
    apply_theme = None
    THEMES = {"Base": ""}

try:
    from ffxi_autotrans import load_autotrans_tree, reload_dictionaries
except Exception:
    load_autotrans_tree = None
    reload_dictionaries = None

try:
    import exporter
except Exception:
    exporter = None

# ---- モデル層（既存プロジェクトの model.py を想定） ----
from model import MacroRepository, MacroController, MacroBook, MacroSet

try:
    from ui_editor import MacroEditor
except ImportError:
    # ui_editor がない場合のフォールバック（通常のQTextEdit）
    class MacroEditor(QTextEdit):
        pass



# ========= キャラ管理ダイアログ =========
class CharacterManageDialog(QDialog):
    def __init__(self, parent=None, mode="local"):
        super().__init__(parent)
        self.mode = mode
        self.setWindowTitle(get_text("char_manage_title"))
        self.list = QListWidget()
        btns = QHBoxLayout()
        self.btn_add = QPushButton(get_text("btn_add"))
        self.btn_rename = QPushButton(get_text("btn_rename"))
        self.btn_delete = QPushButton(get_text("btn_delete"))
        for b in (self.btn_add, self.btn_rename, self.btn_delete):
            btns.addWidget(b)

        layout = QVBoxLayout(self)
        layout.addWidget(self.list)
        layout.addLayout(btns)

        # FFXIモードは物理フォルダを増やさない
        if self.mode == "ffxi":
            self.btn_add.setEnabled(False)
            self.btn_delete.setEnabled(False)

        self.btn_add.clicked.connect(self.on_add)
        self.btn_rename.clicked.connect(self.on_rename)
        self.btn_delete.clicked.connect(self.on_delete)

        self.refresh()

    def _list_characters_safe(self):
        try:
            if storage is None:
                return [("sample1", "SampleChar")]
            return storage.list_characters("local")
        except Exception:
            return [("sample1", "SampleChar")]

    def refresh(self):
        self.list.clear()
        for cid, disp in self._list_characters_safe():
            self.list.addItem(f"{disp}   ({cid})")

    def on_add(self):
        if storage is None:
            QMessageBox.information(self, get_text("dlg_info"), get_text("msg_storage_not_set"))
            return
        cid, ok1 = QInputDialog.getText(self, get_text("dlg_folder_add"), get_text("msg_folder_name"))
        if not ok1 or not cid:
            return
        root = storage.ensure_local_root()
        path = root / cid
        if path.exists():
            QMessageBox.information(self, get_text("dlg_info"), get_text("msg_folder_exists"))
            return
        path.mkdir(parents=True, exist_ok=True)
        disp, ok2 = QInputDialog.getText(self, get_text("dlg_display_name"), get_text("msg_display_name_optional"))
        if ok2 and disp:
            storage.set_display_name(cid, disp)
        self.refresh()

    def on_rename(self):
        if storage is None:
            QMessageBox.information(self, get_text("dlg_info"), get_text("msg_storage_not_set_rename"))
            return
        item = self.list.currentItem()
        if not item:
            return
        txt = item.text()
        cid = txt[txt.rfind("(")+1 : txt.rfind(")")]
        current = txt[: txt.rfind("(")].strip()
        disp, ok = QInputDialog.getText(self, get_text("dlg_name_change"), get_text("msg_new_display_name"), text=current)
        if ok and disp:
            storage.set_display_name(cid, disp)
            self.refresh()

    def on_delete(self):
        if storage is None:
            QMessageBox.information(self, get_text("dlg_info"), get_text("msg_storage_not_set_delete"))
            return
        item = self.list.currentItem()
        if not item:
            return
        txt = item.text()
        cid = txt[txt.rfind("(")+1 : txt.rfind(")")]
        if QMessageBox.question(self, get_text("dlg_confirm"), f"「{cid}」{get_text('msg_confirm_delete')}") != QMessageBox.StandardButton.Yes:
            return
        storage.delete_display_name(cid)
        self.refresh()


# ========= 定型文ダイアログ =========
def _katakana_to_hiragana(text: str) -> str:
    """カタカナをひらがなに変換"""
    result = []
    for char in text:
        code = ord(char)
        # カタカナ範囲: 0x30A1-0x30F6 → ひらがな: 0x3041-0x3096
        if 0x30A1 <= code <= 0x30F6:
            result.append(chr(code - 0x60))
        else:
            result.append(char)
    return ''.join(result)


# FFXI固有の読み方カスタム辞書
# {漢字表記: ひらがな読み}
_FFXI_READING_DICT = {
    # 侍WS
    "八之太刀": "はちのたち",
    "燕飛": "えんぴ",
    "月光": "げっこう",
    "雪風": "ゆきかぜ",
    "花車": "かしゃ",
    "陽炎": "かげろう",
    "嵐月": "らんげつ",
    "断雲": "だんうん",
    "天地": "てんち",
    "春風": "はるかぜ",
    "白虎": "びゃっこ",
    "青龍": "せいりゅう",
    "朱雀": "すざく",
    "玄武": "げんぶ",
    # 忍者忍術
    "空蝉": "うつせみ",
    "火遁": "かとん",
    "水遁": "すいとん",
    "風遁": "ふうとん",
    "土遁": "どとん",
    "雷遁": "らいとん",
    "氷遁": "ひょうとん",
    # 侍JA
    "明鏡止水": "めいきょうしすい",
    "黙想": "もくそう",
    "八双": "はっそう",
    "星眼": "せいがん",
    "葉隠": "はがくれ",
    "心眼": "しんがん",
    # その他
    "震天動地": "しんてんどうち",
}

# グローバルなpykakasiインスタンス（初期化コストが高いため1度だけ作成）
_kakasi_instance = None

def _text_to_hiragana(text: str) -> str:
    """漢字・カタカナを含むテキストをひらがなに変換（読み仮名）
    FFXI固有の読み方にも対応"""
    global _kakasi_instance
    
    # カスタム辞書で完全一致を優先チェック
    for kanji, hiragana in _FFXI_READING_DICT.items():
        if kanji in text:
            # 辞書の単語を含む場合、その部分を置き換えて処理
            text = text.replace(kanji, hiragana)
    
    if _kakasi_instance is None:
        try:
            import pykakasi
            _kakasi_instance = pykakasi.kakasi()
        except ImportError:
            # pykakasiがインストールされていない場合はカタカナ変換のみ
            _kakasi_instance = False
    
    if _kakasi_instance is False:
        # pykakasiが使えない場合はカタカナ→ひらがな変換のみ
        return _katakana_to_hiragana(text)
    
    # 漢字・カタカナ・ひらがな すべてをひらがなに変換
    try:
        result = _kakasi_instance.convert(text)
        hiragana_text = ''.join([item['hira'] for item in result])
        return hiragana_text
    except Exception:
        # エラー時はカタカナ→ひらがな変換のみ
        return _katakana_to_hiragana(text)


class AutoTranslateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        from ui_i18n import get_text
        self.setWindowTitle(get_text("autotrans_title"))
        self.resize(480, 360)
        layout = QVBoxLayout(self)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search")
        layout.addWidget(self.search_box)

        body = QHBoxLayout()
        self.category_list = QListWidget()
        self.entry_list = QListWidget()
        
        # 左: カテゴリ, 右: 定型文
        body.addWidget(self.category_list, 1)
        body.addWidget(self.entry_list, 2)
        layout.addLayout(body)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        from ui_i18n import get_text
        self.btn_insert = QPushButton(get_text("btn_insert"))
        self.btn_cancel = QPushButton(get_text("btn_close"))
        btn_row.addWidget(self.btn_insert)
        btn_row.addWidget(self.btn_cancel)
        layout.addLayout(btn_row)

        self.btn_insert.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        self.entry_list.itemDoubleClicked.connect(lambda _: self.accept())
        self.category_list.currentRowChanged.connect(self._on_category_changed)
        self.search_box.textChanged.connect(self._refresh_entries)

        self.tree_data = load_autotrans_tree() if callable(load_autotrans_tree) else []
        if self.tree_data:
            for cat in self.tree_data:
                self.category_list.addItem(cat["name"])
            self.category_list.setCurrentRow(0)
            self.search_box.setEnabled(True)
        else:
            from ui_i18n import get_text
            self.category_list.addItem(get_text("autotrans_no_data"))
            self.category_list.setEnabled(False)
            self.entry_list.setEnabled(False)
            self.btn_insert.setEnabled(False)
            self.search_box.setEnabled(False)

    def has_data(self) -> bool:
        return bool(self.tree_data)

    def _on_category_changed(self, index: int):
        self.entry_list.clear()
        if not (0 <= index < len(self.tree_data)):
            return
        self._refresh_entries()
        if self.entry_list.count() > 0:
            self.entry_list.setCurrentRow(0)

    def _refresh_entries(self):
        self.entry_list.clear()
        index = self.category_list.currentRow()
        if not (0 <= index < len(self.tree_data)):
            return
        keyword_raw = self.search_box.text().strip()
        keyword = keyword_raw.lower()
        # ひらがな検索対応：キーワードをひらがなに変換
        keyword_hiragana = _text_to_hiragana(keyword)
        has_kanji = any("一" <= ch <= "龯" or "㐀" <= ch <= "䶵" for ch in keyword_raw)

        # 重複除去用のセット
        seen_entries = set()

        def _add_item(label: str, value: str):
            # 既に追加済みの項目はスキップ
            if value in seen_entries:
                return
            seen_entries.add(value)
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, value)
            self.entry_list.addItem(item)

        def _matches(text: str) -> bool:
            """キーワードがテキストにマッチするか判定（ひらがな/漢字/カタカナ対応）"""
            text_lower = text.lower()
            if has_kanji:
                # 漢字入力時は表記一致のみ（読みヒットは無効化）
                return keyword_raw in text or keyword_raw in text_lower
            # テキスト全体（漢字含む）をひらがなに変換
            text_hiragana = _text_to_hiragana(text_lower)
            # 通常の検索 または ひらがな読み仮名での検索
            return keyword in text_lower or keyword_hiragana in text_hiragana

        if keyword:
            for cat in self.tree_data:
                for entry in cat["entries"]:
                    if _matches(entry) or _matches(cat["name"]):
                        _add_item(f"{cat['name']} - {entry}", entry)
            return

        if not (0 <= index < len(self.tree_data)):
            return
        for entry in self.tree_data[index]["entries"]:
            _add_item(entry, entry)

    def selected_snippet(self) -> str:
        item = self.entry_list.currentItem()
        if not item:
            return ""
        raw = item.data(Qt.ItemDataRole.UserRole) or item.text()
        text = str(raw).strip()
        if not text:
            return ""
        if text.startswith("<<") and text.endswith(">>"):
            return text
        return f"<<{text}>>"





class ExportCenterDialog(QDialog):
    """Launcher-style dialog that summarizes export-related information."""

    def __init__(self, character_id: str, repo: MacroRepository | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(get_text("export_title"))
        self.character_id = character_id
        self.repo = repo

        layout = QVBoxLayout(self)

        self.header_label = QLabel()
        self.header_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.header_label)

        info_group = QGroupBox(get_text("export_group_edit_data"))
        info_layout = QVBoxLayout(info_group)
        self.json_path_label = QLabel()
        self.json_path_label.setWordWrap(True)
        self.json_status_label = QLabel()
        info_layout.addWidget(self.json_path_label)
        info_layout.addWidget(self.json_status_label)
        layout.addWidget(info_group)

        template_group = QGroupBox(get_text("export_group_template"))
        template_layout = QVBoxLayout(template_group)
        self.template_label = QLabel()
        self.template_label.setWordWrap(True)
        template_layout.addWidget(self.template_label)
        template_row = QHBoxLayout()
        self.btn_open_template = QPushButton(get_text("export_btn_open_folder"))
        self.btn_open_template.clicked.connect(self._open_template_folder)
        template_row.addWidget(self.btn_open_template)
        template_row.addStretch()
        template_layout.addLayout(template_row)
        layout.addWidget(template_group)

        history_group = QGroupBox(get_text("export_group_history"))
        history_layout = QVBoxLayout(history_group)
        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self._open_selected_history)
        history_layout.addWidget(self.history_list)
        row = QHBoxLayout()
        self.btn_open_history = QPushButton(get_text("export_btn_open_folder"))
        self.btn_open_history.clicked.connect(self._open_selected_history)
        row.addWidget(self.btn_open_history)
        row.addStretch()
        history_layout.addLayout(row)
        layout.addWidget(history_group, 1)

        actions_group = QGroupBox(get_text("export_group_actions"))
        actions_layout = QVBoxLayout(actions_group)
        self.run_hint = QLabel(get_text("export_hint_run"))
        self.run_hint.setWordWrap(True)
        actions_layout.addWidget(self.run_hint)
        self.btn_run_export = QPushButton(get_text("export_execute"))
        self.btn_run_export.clicked.connect(self._on_run_export)
        actions_layout.addWidget(self.btn_run_export)
        layout.addWidget(actions_group)

        # FFXI USER フォルダへコピーボタン（別途、目立つように配置）
        self.btn_copy_to_ffxi = QPushButton(get_text("export_to_ffxi"))
        self.btn_copy_to_ffxi.setMinimumHeight(50)
        self.btn_copy_to_ffxi.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.btn_copy_to_ffxi.clicked.connect(self._on_copy_to_ffxi)
        if storage is None:
            self.btn_copy_to_ffxi.setEnabled(False)
            self.btn_copy_to_ffxi.setToolTip(get_text("export_tooltip_storage_unavailable"))
        layout.addWidget(self.btn_copy_to_ffxi)

        layout.addStretch()
        self._refresh_state()

    def _json_path(self) -> Path:
        if self.repo and self.repo.character_id == self.character_id:
            return self.repo.json_path
        base = getattr(self.repo, "base_dir", Path.cwd() / "macros") if self.repo else Path.cwd() / "macros"
        return Path(base) / f"macros_{self.character_id}.json"

    def _template_folder(self) -> Optional[Path]:
        if storage is None:
            return None
        candidates: list[Path] = []
        try:
            candidates.append(storage.character_folder("local", self.character_id))
        except Exception:
            pass
        for mode in ("ffxi", "ffxi_usr"):
            try:
                candidates.append(storage.character_folder(mode, self.character_id))
            except Exception:
                continue
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0] if candidates else None

    def _refresh_state(self) -> None:
        self._refresh_character_label()
        path = self._json_path()
        if path.exists():
            mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            self.json_path_label.setText(f"{get_text('export_json_label')} {path}")
            self.json_status_label.setText(f"{get_text('export_last_modified')} {mtime}")
        else:
            self.json_path_label.setText(f"{get_text('export_json_label')} {path}")
            self.json_status_label.setText(get_text("msg_file_not_exist") if "msg_file_not_exist" in dir() else "File does not exist yet.")

        template = self._template_folder()
        if template and template.exists():
            self.template_label.setText(f"{get_text('export_template_label')} {template}")
            self.btn_open_template.setEnabled(True)
        else:
            self.template_label.setText(f"{get_text('export_template_label')} " + (get_text("msg_template_not_detected") if "msg_template_not_detected" in dir() else "Cannot detect from data/edit or USER folder."))
            self.btn_open_template.setEnabled(False)

        self._refresh_history()

    def _refresh_character_label(self) -> None:
        display = None
        if storage is not None:
            try:
                display = storage.get_display_name(self.character_id)
            except Exception:
                display = None
        display = display or self.character_id
        from ui_i18n import get_text
        char_label = get_text("label_character").rstrip(":")
        self.header_label.setText(f"{char_label} {display} ({self.character_id})")

    def _refresh_history(self) -> None:
        self.history_list.clear()
        self.btn_open_history.setEnabled(False)
        if storage is None:
            self.history_list.addItem("storage モジュールを読み込めないため履歴を表示できません。")
            return
        try:
            root = storage.character_export_root(self.character_id)
        except Exception as exc:
            self.history_list.addItem(f"{get_text('export_cannot_prepare')} {exc}")
            return
        entries = sorted([p for p in root.iterdir() if p.is_dir()], reverse=True)
        if not entries:
            self.history_list.addItem(get_text("export_no_history"))
            return
        for folder in entries:
            status = self._manifest_status(folder)
            item = QListWidgetItem(f"{folder.name}  ({status})")
            item.setData(Qt.ItemDataRole.UserRole, str(folder.resolve()))
            self.history_list.addItem(item)
        self.btn_open_history.setEnabled(True)

    def _manifest_status(self, folder: Path) -> str:
        manifest = folder / "manifest.json"
        if not manifest.exists():
            return get_text("export_no_manifest")
        try:
            info = json.loads(manifest.read_text(encoding="utf-8"))
        except Exception:
            return get_text("export_load_error")
        if info.get("verified"):
            return get_text("export_verified")
        warn = info.get("verification_warning")
        return warn or get_text("export_skipped")

    def _selected_history_path(self) -> Optional[Path]:
        item = self.history_list.currentItem()
        if not item:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return None
        return Path(str(data))

    def _open_folder(self, target: Path) -> None:
        try:
            if sys.platform.startswith("win") and hasattr(os, "startfile"):
                os.startfile(str(target))
            else:
                opener = "open" if sys.platform == "darwin" else "xdg-open"
                subprocess.Popen([opener, str(target)])
        except Exception as exc:
            QMessageBox.warning(self, get_text("dlg_error"), f"{get_text('msg_cannot_open_folder')} {exc}")

    def _open_selected_history(self) -> None:
        target = self._selected_history_path()
        if not target or not target.exists():
            QMessageBox.information(self, get_text("dlg_folder"), get_text("msg_select_folder"))
            return
        self._open_folder(target)

    def _open_template_folder(self) -> None:
        folder = self._template_folder()
        if not folder or not folder.exists():
            QMessageBox.information(self, get_text("dlg_template"), get_text("msg_template_not_found"))
            return
        self._open_folder(folder)

    def _on_run_export(self) -> None:
        if exporter is None:
            QMessageBox.warning(self, get_text("dlg_export"), get_text("msg_exporter_not_loaded"))
            return
        template = self._template_folder()
        if not template or not template.exists():
            QMessageBox.warning(self, get_text("dlg_template"), get_text("msg_template_not_found_export"))
            return

        # 実際のエクスポート処理を呼び出し、resultを取得
        try:
            result = exporter.export_character_macros(
                character_id=self.character_id,
                template_folder=template,
                macros_base=getattr(self.repo, "base_dir", None) if self.repo else None,
            )
        except Exception as exc:
            QMessageBox.warning(self, get_text("dlg_export"), f"{get_text('msg_export_error')} {exc}")
            return

        self._last_export_dest = Path(result["destination"])
        self._refresh_state()
        
        message = [f"{get_text('export_complete_msg')} {self._last_export_dest}"]
        message.append(get_text("export_verification_ok") if result.get("verified") else get_text("export_verification_check"))
        if result.get("verification_warning"):
            message.append(f"{get_text('export_warning')} {result['verification_warning']}")
        QMessageBox.information(self, get_text("export_complete"), "\n".join(message))

    def _on_copy_to_ffxi(self) -> None:
        """最新のエクスポート結果を FFXI USER フォルダへコピー"""
        if not hasattr(self, "_last_export_dest") or not self._last_export_dest:
            # 履歴から最新を取得
            target = self._selected_history_path()
            if not target:
                QMessageBox.information(
                    self,
                    get_text("dlg_copy"),
                    get_text("msg_select_export_or_run")
                )
                return
            source = target
        else:
            source = self._last_export_dest

        if not source.exists():
            QMessageBox.warning(self, get_text("dlg_copy"), get_text("msg_source_folder_not_found"))
            return

        if storage is None:
            QMessageBox.warning(self, get_text("dlg_copy"), get_text("msg_storage_not_available"))
            return

        target_root = storage.ffxi_user_root()
        target_path = target_root / self.character_id
        reply = QMessageBox.question(
            self,
            get_text("dlg_copy_to_ffxi"),
            get_text("msg_copy_to_ffxi_confirm").format(source=source, target=target_path),
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Ok:
            return

        try:
            self._copy_to_ffxi(source, target_path)
            QMessageBox.information(self, get_text("dlg_copy_complete"), get_text("msg_copy_complete").format(target=target_path))
        except PermissionError as exc:
            QMessageBox.warning(
                self,
                get_text("dlg_copy_failed"),
                get_text("msg_copy_failed_permission").format(error=exc)
            )
        except Exception as exc:
            QMessageBox.warning(self, get_text("dlg_copy_failed"), get_text("msg_copy_failed").format(error=exc))

    def _copy_to_ffxi(self, source: Path, destination: Path | None = None) -> None:
        target = destination
        if target is None:
            if storage is None:
                raise RuntimeError("storage モジュールが利用できません。")
            target = storage.ffxi_user_root() / self.character_id
        target.mkdir(parents=True, exist_ok=True)
        
        copied_files = []
        for item in source.iterdir():
            if not item.is_file():
                continue
            name = item.name.lower()
            # .dat ファイルまたは .ttl ファイルのみコピー
            is_dat = name.startswith("mcr") and name.endswith(".dat")
            is_ttl = name in {"mcr.ttl", "mcr_2.ttl"}
            if not (is_dat or is_ttl):
                continue
            dest = target / item.name
            
            # コピー前のファイルサイズ
            src_size = item.stat().st_size
            
            # コピー先のファイルが読み取り専用なら解除する
            if dest.exists():
                try:
                    import stat
                    os.chmod(dest, stat.S_IWRITE)
                except Exception as e:
                    print(f"警告: {item.name} の属性変更に失敗しました: {e}")

            # ファイルをコピー
            shutil.copy2(item, dest)
            
            # コピー後の検証
            if dest.exists():
                dest_size = dest.stat().st_size
                if src_size == dest_size:
                    copied_files.append(f"{item.name} ({src_size} bytes)")
                else:
                    print(f"警告: {item.name} のサイズが一致しません (元: {src_size}, 先: {dest_size})")
            else:
                print(f"エラー: {item.name} のコピーに失敗しました")
        
        if copied_files:
            print(f"コピー完了: {len(copied_files)} ファイル")
            for f in copied_files:
                print(f"  - {f}")
# ========= メインウィンドウ =========
class VanaMacroUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VanaMacro")
        self.resize(1280, 760)

        # モデル
        self.repo: MacroRepository | None = None
        self.controller: MacroController | None = None

        # 現在位置
        self.current_book_index = 0
        self.current_set_index = 0
        self.current_slot: tuple[str, int] | None = None  # ("ctrl"/"alt", idx)

        # クリップボード（Set/Book）
        self._set_clipboard = None
        self._book_clipboard = None

        # UI補助
        self.theme_combo: QComboBox | None = None
        self._theme_actions: dict[str, QAction] = {}
        self._theme_action_group: QActionGroup | None = None
        self._theme_syncing = False
        self.action_macro_paste: QAction | None = None

        # --- メニューバー & ツールバー ---
        self._create_toolbar()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter = splitter

        def _double_height(btn: QPushButton) -> None:
            """Set a button's height to roughly double its size hint."""
            # 標準的なボタンの高さは約30px前後なので、2倍なら60px程度
            target_height = 36
            btn.setMinimumHeight(target_height)
            btn.setMaximumHeight(target_height)

        # 左：Book（リスト＋右に縦ボタン）
        book_group = QGroupBox("Book")
        book_layout = QVBoxLayout(book_group)
        book_layout.setContentsMargins(6, 6, 6, 6)
        book_layout.setSpacing(6)

        self.book_list = QListWidget()
        self.book_list.currentRowChanged.connect(self.on_book_changed)
        self.book_list.setMinimumWidth(140)

        row = QHBoxLayout()
        row.addWidget(self.book_list, 1)

        from ui_i18n import get_text
        self.btn_book_rename = QPushButton(get_text("label_book_rename"))
        self.btn_book_copy   = QPushButton(get_text("btn_copy"))
        self.btn_book_paste  = QPushButton(get_text("btn_paste"))
        self.btn_book_clear  = QPushButton(get_text("btn_clear"))
        for b in (self.btn_book_rename, self.btn_book_copy, self.btn_book_paste, self.btn_book_clear):
            _double_height(b)
        self.btn_book_rename.clicked.connect(self.on_book_rename)
        self.btn_book_copy.clicked.connect(self.on_book_copy)
        self.btn_book_paste.clicked.connect(self.on_book_paste)
        self.btn_book_clear.clicked.connect(self.on_book_clear)

        btn_col = QVBoxLayout()
        btn_col.setSpacing(4)
        for b in (self.btn_book_rename, self.btn_book_copy, self.btn_book_paste, self.btn_book_clear):
            btn_col.addWidget(b)
        btn_col.addStretch()
        row.addLayout(btn_col)
        book_layout.addLayout(row)
        splitter.addWidget(book_group)

        # 右：Set/マクロ
        right = QWidget()
        right_layout = QVBoxLayout(right)

        # --- Setエリア ---
        set_group = QGroupBox("Set")
        set_layout = QVBoxLayout(set_group)
        self.set_buttons = []  # ボタンには Set名（空なら SetN）を表示
        set_row = QHBoxLayout()
        for i in range(10):
            col = QVBoxLayout(); col.setSpacing(2)
            lbl = QLabel(f"Set{i+1}"); lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            btn = QPushButton("")  # 後で Set名を反映
            f = btn.font(); f.setPointSize(int(f.pointSize() * 1.2)); btn.setFont(f)
            btn.clicked.connect(lambda _, x=i: self.on_set_changed(x))
            self.set_buttons.append(btn)
            col.addWidget(lbl); col.addWidget(btn); set_row.addLayout(col)
        set_layout.addLayout(set_row)

        set_btn_row = QHBoxLayout(); set_btn_row.addStretch()
        from ui_i18n import get_text
        self.btn_set_rename = QPushButton(get_text("btn_set_rename"))
        self.btn_set_copy = QPushButton(get_text("btn_copy"))
        self.btn_set_paste = QPushButton(get_text("btn_paste"))
        self.btn_set_clear = QPushButton(get_text("btn_clear"))
        for b in (self.btn_set_rename, self.btn_set_copy, self.btn_set_paste, self.btn_set_clear):
            _double_height(b)
        self.btn_set_rename.clicked.connect(self.on_set_rename)
        self.btn_set_copy.clicked.connect(self.on_set_copy)
        self.btn_set_paste.clicked.connect(self.on_set_paste)
        self.btn_set_clear.clicked.connect(self.on_set_clear)
        for b in (self.btn_set_rename, self.btn_set_copy, self.btn_set_paste, self.btn_set_clear):
            set_btn_row.addWidget(b)
        set_layout.addLayout(set_btn_row)
        right_layout.addWidget(set_group)

        # --- マクロエリア ---
        macro_group = QGroupBox("マクロ")
        macro_layout = QVBoxLayout(macro_group)
        macro_layout.setContentsMargins(6, 6, 6, 6)
        macro_layout.setSpacing(6)

        # マクロボタン（Ctrl/Alt）。上に固定ラベル、ボタンはマクロ名表示（1.5倍）
        self.macro_buttons = {"ctrl": [], "alt": []}

        ctrl_row = QHBoxLayout()
        for i in range(10):
            col = QVBoxLayout(); col.setSpacing(2)
            lbl = QLabel(f"Ctrl{i+1}"); lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            btn = QPushButton("")
            f = btn.font(); f.setPointSize(int(f.pointSize() * 1.2)); btn.setFont(f)
            btn.clicked.connect(lambda _, x=i: self.on_macro_selected("ctrl", x))
            self.macro_buttons["ctrl"].append(btn)
            col.addWidget(lbl); col.addWidget(btn); ctrl_row.addLayout(col)
        macro_layout.addLayout(ctrl_row)

        alt_row = QHBoxLayout()
        for i in range(10):
            col = QVBoxLayout(); col.setSpacing(2)
            lbl = QLabel(f"Alt{i+1}"); lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            btn = QPushButton("")
            f = btn.font(); f.setPointSize(int(f.pointSize() * 1.2)); btn.setFont(f)
            btn.clicked.connect(lambda _, x=i: self.on_macro_selected("alt", x))
            self.macro_buttons["alt"].append(btn)
            col.addWidget(lbl); col.addWidget(btn); alt_row.addLayout(col)
        macro_layout.addLayout(alt_row)

        # マクロ操作（右端揃え・保存→コピー→ペースト→クリア）
        macro_btn_row = QHBoxLayout(); macro_btn_row.addStretch()
        from ui_i18n import get_text
        self.btn_macro_save = QPushButton(get_text("btn_macro_save"))
        self.btn_macro_copy = QPushButton(get_text("btn_macro_copy"))
        self.btn_macro_paste = QPushButton(get_text("btn_macro_paste"))
        self._set_macro_paste_enabled(False)
        self.btn_macro_clear = QPushButton(get_text("btn_macro_clear"))
        for b in (self.btn_macro_save, self.btn_macro_copy, self.btn_macro_paste, self.btn_macro_clear):
            _double_height(b)
        for b in (self.btn_macro_save, self.btn_macro_copy, self.btn_macro_paste, self.btn_macro_clear):
            macro_btn_row.addWidget(b)
        macro_layout.addLayout(macro_btn_row)

        # --- マクロ編集（6行＋一括） ---
        name_row = QHBoxLayout()
        name_row.setSpacing(6)
        from ui_i18n import get_text
        name_row.addWidget(QLabel(get_text("label_macro_name")))
        self.macro_name = QLineEdit()
        fn = self.macro_name.font()
        fn.setPointSize(int(fn.pointSize() * 1.4))
        self.macro_name.setFont(fn)
        metrics = QFontMetrics(self.macro_name.font())
        self.macro_name.setFixedWidth(metrics.horizontalAdvance("W" * 4) + 16)
        name_row.addWidget(self.macro_name)
        name_row.addStretch()
        macro_layout.addLayout(name_row)

        # 一括テキストのラベルと定型文ボタンをエリア外の行に出す
        controls_row = QHBoxLayout()
        controls_row.addStretch()
        self.label_bulk_text = QLabel(get_text("label_bulk_text"))
        controls_row.addWidget(self.label_bulk_text)
        controls_row.addSpacing(8)
        self.btn_autotrans_tree = QPushButton(get_text("label_autotrans"))
        controls_row.addWidget(self.btn_autotrans_tree)
        macro_layout.addLayout(controls_row)

        editor_row = QHBoxLayout(); editor_row.setSpacing(6)
        self.macro_lines = []
        self._last_text_widget = None
        self._macro_syncing = False
        self._dirty = False
        left_col = QVBoxLayout(); left_col.setSpacing(0)
        for i in range(6):
            lr = QHBoxLayout(); lr.setSpacing(2); lr.addWidget(QLabel(f"{i+1}:"))
            le = QLineEdit(); fl = le.font(); fl.setPointSize(int(fl.pointSize() * 1.1)); le.setFont(fl)
            le.installEventFilter(self)
            self.macro_lines.append(le); lr.addWidget(le); left_col.addLayout(lr)
        left_panel = QWidget(); left_panel.setLayout(left_col)
        editor_row.addWidget(left_panel, 2)

        right_col = QVBoxLayout()
        right_col.setContentsMargins(5, 5, 5, 5)
        right_col.setSpacing(0)
        self.bulk_editor = MacroEditor(); fb = self.bulk_editor.font(); fb.setPointSize(int(fb.pointSize() * 1.4)); self.bulk_editor.setFont(fb)
        self.bulk_editor.installEventFilter(self)
        self.bulk_editor.setPlaceholderText("6行のマクロ内容をまとめて入力"); right_col.addWidget(self.bulk_editor)
        right_panel = QWidget(); right_panel.setLayout(right_col)
        editor_row.addWidget(right_panel, 3)
        macro_layout.addLayout(editor_row)

        # 左6行の高さを下限に設定し、上下ラインが揃うようにする
        target_bulk_height = left_panel.sizeHint().height()
        if target_bulk_height > 0:
            self.bulk_editor.setMinimumHeight(target_bulk_height)

        self.macro_name.textChanged.connect(self._mark_dirty)
        for le in self.macro_lines:
            le.textChanged.connect(self.on_lines_join_to_bulk)
            le.textChanged.connect(self._mark_dirty)
        self.bulk_editor.textChanged.connect(self.on_bulk_apply_to_lines)
        self.bulk_editor.textChanged.connect(self._mark_dirty)

        right_layout.addWidget(macro_group)
        splitter.addWidget(right)

        # 分割の初期サイズ（左細く／右広く）
        splitter.setStretchFactor(0, 0); splitter.setStretchFactor(1, 1)
        splitter.setSizes([200, 1080])

        # 中央ウィジェット
        central = QWidget(); central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(10, 15, 10, 10)
        central_layout.addWidget(splitter)
        self.setCentralWidget(central)

        self._build_menu_bar()

        # 配線
        self.btn_macro_save.clicked.connect(self.on_macro_save)
        self.btn_autotrans_tree.clicked.connect(self.on_insert_autotrans)
        self.btn_macro_copy.clicked.connect(self.on_macro_copy)
        self.btn_macro_paste.clicked.connect(self.on_macro_paste)
        self.btn_macro_clear.clicked.connect(self.on_macro_clear)
        # Book/Set は上で接続済み（縦ボタン部）

        # 初期表示
        self.refresh_characters(); self.refresh_books()
        self.book_list.setCurrentRow(0); self.on_set_changed(0); self.on_macro_selected("ctrl", 0)
        self._refresh_set_button_labels(); self._refresh_macro_button_labels(); self._sync_action_button_sizes(); self._apply_theme_styles()
        
        # 設定を復元
        self._restore_settings()

    # ====== 設定の保存と復元 ======
    def _restore_settings(self):
        """ウィンドウサイズ・位置・スプリッター状態を復元"""
        settings = QSettings("VanaMacro", "VanaMacro")
        
        # ウィンドウジオメトリ
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        # スプリッターサイズ
        splitter_sizes = settings.value("splitter_sizes")
        if splitter_sizes:
            try:
                # QSettingsはリストを文字列として保存することがあるので変換
                if isinstance(splitter_sizes, str):
                    sizes = [int(x) for x in splitter_sizes.split(',')]
                else:
                    sizes = [int(x) for x in splitter_sizes]
                self.splitter.setSizes(sizes)
            except Exception:
                # 変換に失敗した場合はデフォルト値を使用
                self.splitter.setSizes([200, 1080])

    def _save_settings(self):
        """ウィンドウサイズ・位置・スプリッター状態を保存"""
        settings = QSettings("VanaMacro", "VanaMacro")
        
        # ウィンドウジオメトリ
        settings.setValue("geometry", self.saveGeometry())
        
        # スプリッターサイズ
        sizes = self.splitter.sizes()
        settings.setValue("splitter_sizes", sizes)

    def closeEvent(self, event):
        """ウィンドウを閉じる際に設定を保存"""
        if not self._check_unsaved_changes():
            event.ignore()
            return
        self._save_settings()
        super().closeEvent(event)

    # ====== 共通：現在モード＆モード変更 ======
    def on_theme_changed(self, theme_name: str):
        if apply_theme and storage:
            app = QApplication.instance()
            if app:
                apply_theme(app, theme_name)
            storage.set_theme(theme_name)

        # Theme change may alter highlight colors/QSS.
        self._apply_theme_styles()
        self._ensure_theme_controls(theme_name)

    def _current_theme(self) -> str:
        app = QApplication.instance()
        if app:
            name = app.property("vanamacro_theme")
            if name:
                return str(name)
        try:
            if storage:
                return storage.get_theme()
        except Exception:
            pass
        return "Base"

    def _apply_theme_styles(self):
        theme = self._current_theme()
        # Book list selection colors per theme
        if theme == "Game":
            bg, fg, border = "#403019", "#f5e9c8", "#c6a35a"
        elif theme == "Dark":
            bg, fg, border = "#094771", "#ffffff", "#007acc"
        else:
            bg, fg, border = "#334b70", "#eef2f9", "#486591"
        self.book_list.setStyleSheet(
            f"QListWidget::item:selected{{background-color:{bg};color:{fg};border:1px solid {border};}}"
            f"QListWidget{{selection-background-color:{bg};selection-color:{fg};}}"
        )
        # Refresh button highlights to match theme
        self._update_selection_highlight()
        
        # アクションボタンの高さを再設定（テーマ適用後にサイズが変わる問題を防ぐ）
        target_height = 36
        for btn in [
            self.btn_book_rename, self.btn_book_copy, self.btn_book_paste, self.btn_book_clear,
            self.btn_set_rename, self.btn_set_copy, self.btn_set_paste, self.btn_set_clear,
            self.btn_macro_save, self.btn_macro_copy, self.btn_macro_paste, self.btn_macro_clear
        ]:
            btn.setMinimumHeight(target_height)
            btn.setMaximumHeight(target_height)

    # ====== 見た目ユーティリティ ======
    def _update_selection_highlight(self):
        # 強調色は背景＋縁取り＋文字色をセットで指定し、文字が埋もれないようにする
        theme = self._current_theme()
        if theme == "Game":
            selection_style = "background-color: #403019; border: 1px solid #c6a35a; color: #f5e9c8;"
        elif theme == "Dark":
            selection_style = "background-color: #0e639c; border: 1px solid #007acc; color: #ffffff;"
        else:
            selection_style = "background-color: #334b70; border: 1px solid #486591; color: #eef2f9;"
        # Setボタン
        for i, btn in enumerate(self.set_buttons):
            btn.setStyleSheet(selection_style if i == self.current_set_index else "")
        # マクロ（Ctrl/Alt）
        for i, btn in enumerate(self.macro_buttons["ctrl"]):
            active = self.current_slot == ("ctrl", i)
            btn.setStyleSheet(selection_style if active else "")
        for i, btn in enumerate(self.macro_buttons["alt"]):
            active = self.current_slot == ("alt", i)
            btn.setStyleSheet(selection_style if active else "")

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.FocusIn:
            if obj in getattr(self, "macro_lines", []) or obj is getattr(self, "bulk_editor", None):
                self._last_text_widget = obj
        return super().eventFilter(obj, event)

    def _current_text_widget(self):
        last = getattr(self, "_last_text_widget", None)
        text_widgets = list(getattr(self, "macro_lines", []))
        bulk = getattr(self, "bulk_editor", None)
        if bulk:
            text_widgets.append(bulk)
        if last in text_widgets:
            return last
        focus = self.focusWidget()
        for le in getattr(self, "macro_lines", []):
            if focus is le:
                return le
        if focus is getattr(self, "bulk_editor", None):
            return self.bulk_editor
        return self.macro_lines[0] if self.macro_lines else None

    def _cursor_snapshot(self, widget):
        if isinstance(widget, QLineEdit):
            return {"type": "line", "pos": widget.cursorPosition()}
        if isinstance(widget, QTextEdit):
            cursor = widget.textCursor()
            return {
                "type": "text",
                "start": cursor.selectionStart(),
                "end": cursor.selectionEnd(),
            }
        return None

    def _insert_text_into_widget(self, widget, text: str, snapshot=None):
        if not widget or not text:
            return
        if isinstance(widget, QLineEdit):
            pos = widget.cursorPosition()
            if snapshot and snapshot.get("type") == "line":
                pos = snapshot.get("pos", pos)
            cur = widget.text()
            widget.setText(cur[:pos] + text + cur[pos:])
            widget.setCursorPosition(pos + len(text))
        elif isinstance(widget, QTextEdit):
            cursor = widget.textCursor()
            if snapshot and snapshot.get("type") == "text":
                start = snapshot.get("start", cursor.position())
                end = snapshot.get("end", start)
                cursor.setPosition(start)
                cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            cursor.insertText(text)
            widget.setTextCursor(cursor)

    def on_insert_autotrans(self):
        if load_autotrans_tree is None:
            QMessageBox.information(self, "定型文", "定型文データが利用できません。")
            return
        target = self._current_text_widget()
        if not target:
            return
        snapshot = self._cursor_snapshot(target)
        dlg = AutoTranslateDialog(self)
        if not dlg.has_data():
            from pathlib import Path
            db_path = Path(__file__).resolve().parent / "autotrans_data" / "autotrans.db"
            if not db_path.exists():
                QMessageBox.warning(
                    self, 
                    "定型文", 
                    f"定型文データベースが見つかりません。\n\n"
                    f"パス: {db_path}\n\n"
                    f"autotrans_data/tools/sync_auto_tables.py を実行して\n"
                    f"データベースを生成してください。"
                )
            else:
                QMessageBox.warning(
                    self, 
                    "定型文", 
                    "定型文データの読み込みに失敗しました。\n\n"
                    "データベースファイルが破損している可能性があります。"
                )
            return
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        snippet = dlg.selected_snippet()
        if not snippet:
            return
        target.setFocus()
        self._insert_text_into_widget(target, snippet, snapshot)

    def _refresh_set_button_labels(self):
        """Setボタンに Set名（空なら SetN）を表示。"""
        if not self.repo:
            for i, btn in enumerate(self.set_buttons):
                btn.setText(f"Set{i+1}")
            return
        b = self.current_book_index
        if not (0 <= b < 40):
            return
        for i in range(10):
            nm = self.repo.books[b].sets[i].name.strip()
            self.set_buttons[i].setText(nm if nm else f"Set{i+1}")

    def _refresh_macro_button_labels(self):
        """現在の Book/Set の各マクロボタンにマクロ名を表示。空なら CtrlN/AltN 表示。"""
        if not self.repo:
            for i, btn in enumerate(self.macro_buttons["ctrl"]):
                btn.setText(f"Ctrl{i+1}")
            for i, btn in enumerate(self.macro_buttons["alt"]):
                btn.setText(f"Alt{i+1}")
            return
        b, s = self.current_book_index, self.current_set_index
        ok = (0 <= b < 40) and (0 <= s < 10)
        if not ok:
            return
        mset = self.repo.books[b].sets[s]
        for i in range(10):
            nm = (mset.ctrl[i].name if i < len(mset.ctrl) else "").strip()
            self.macro_buttons["ctrl"][i].setText(nm if nm else f"Ctrl{i+1}")
            nm = (mset.alt[i].name if i < len(mset.alt) else "").strip()
            self.macro_buttons["alt"][i].setText(nm if nm else f"Alt{i+1}")

    def _sync_action_button_sizes(self):
        """Set/マクロ/Book の操作ボタンを、Set/Ctrl ボタン高さに揃える"""
        try:
            base_h = None
            if self.set_buttons:
                base_h = self.set_buttons[0].sizeHint().height()
            elif self.macro_buttons["ctrl"]:
                base_h = self.macro_buttons["ctrl"][0].sizeHint().height()
            if base_h:
                for b in (self.btn_set_rename, self.btn_set_copy, self.btn_set_paste, self.btn_set_clear):
                    b.setFixedHeight(base_h)
                for b in (self.btn_macro_save, self.btn_macro_copy, self.btn_macro_paste, self.btn_macro_clear):
                    b.setFixedHeight(base_h)
                for b in (self.btn_book_rename, self.btn_book_copy, self.btn_book_paste, self.btn_book_clear):
                    b.setFixedHeight(base_h)
        except Exception:
            pass

    def _set_macro_paste_enabled(self, enabled: bool):
        self.btn_macro_paste.setEnabled(enabled)
        if self.action_macro_paste is not None:
            self.action_macro_paste.setEnabled(enabled)

    def _create_toolbar(self):
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)
        toolbar.setStyleSheet("QToolBar { padding: 8px 5px; spacing: 10px; border: none; margin-top: 5px; }")

        # キャラ選択
        self.toolbar_char_label = QLabel("  " + get_text("label_character") + " ")
        toolbar.addWidget(self.toolbar_char_label)
        self.character_combo = QComboBox()
        self.character_combo.setMinimumWidth(120)
        self.character_combo.currentIndexChanged.connect(self.on_character_changed)
        toolbar.addWidget(self.character_combo)

        # FFXI取り込みボタン
        toolbar.addSeparator()
        self.btn_import = QPushButton(get_text("action_import"))
        self.btn_import.clicked.connect(self.on_ffxi_import)
        toolbar.addWidget(self.btn_import)

        # エクスポートセンターボタン
        self.btn_export_center = QPushButton(get_text("btn_export_center"))
        self.btn_export_center.clicked.connect(self.on_open_export_center)
        toolbar.addWidget(self.btn_export_center)

        # スペーサー
        empty = QWidget()
        empty.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(empty)

    def _build_menu_bar(self):
        menu_bar = self.menuBar()
        menu_bar.clear()
        
        # メニューバーのスタイル設定：項目間隔を広げる
        menu_bar.setStyleSheet("""
            QMenuBar {
                spacing: 10px;
                padding: 8px 5px;
            }
            QMenuBar::item {
                padding: 5px 12px;
                margin: 0px 3px;
            }
        """)

        file_menu = menu_bar.addMenu(get_text("menu_file"))
        self.action_import_menu = QAction(get_text("action_import") + "...", self)
        self.action_import_menu.setShortcut(QKeySequence("Ctrl+I"))
        self.action_import_menu.triggered.connect(self.on_ffxi_import)
        file_menu.addAction(self.action_import_menu)

        action_export_center = QAction(get_text("action_export_center"), self)
        action_export_center.setShortcut(QKeySequence("Ctrl+E"))
        action_export_center.triggered.connect(self.on_open_export_center)
        file_menu.addAction(action_export_center)

        file_menu.addSeparator()
        action_exit = QAction(get_text("action_exit"), self)
        action_exit.setShortcut(QKeySequence("Ctrl+Q"))
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)

        edit_menu = menu_bar.addMenu(get_text("menu_edit"))

        book_menu = edit_menu.addMenu(get_text("menu_book"))
        action_book_rename = QAction(get_text("action_rename"), self)
        action_book_rename.triggered.connect(self.on_book_rename)
        book_menu.addAction(action_book_rename)
        action_book_copy = QAction(get_text("action_copy"), self)
        action_book_copy.triggered.connect(self.on_book_copy)
        book_menu.addAction(action_book_copy)
        action_book_paste = QAction(get_text("action_paste"), self)
        action_book_paste.triggered.connect(self.on_book_paste)
        book_menu.addAction(action_book_paste)
        action_book_clear = QAction(get_text("action_clear"), self)
        action_book_clear.triggered.connect(self.on_book_clear)
        book_menu.addAction(action_book_clear)

        set_menu = edit_menu.addMenu(get_text("menu_set"))
        action_set_rename = QAction(get_text("action_rename"), self)
        action_set_rename.triggered.connect(self.on_set_rename)
        set_menu.addAction(action_set_rename)
        action_set_copy = QAction(get_text("action_copy"), self)
        action_set_copy.triggered.connect(self.on_set_copy)
        set_menu.addAction(action_set_copy)
        action_set_paste = QAction(get_text("action_paste"), self)
        action_set_paste.triggered.connect(self.on_set_paste)
        set_menu.addAction(action_set_paste)
        action_set_clear = QAction(get_text("action_clear"), self)
        action_set_clear.triggered.connect(self.on_set_clear)
        set_menu.addAction(action_set_clear)

        view_menu = menu_bar.addMenu(get_text("menu_view"))
        if THEMES:
            theme_menu = view_menu.addMenu(get_text("menu_theme"))
            self._theme_actions.clear()
            if self._theme_action_group is None:
                self._theme_action_group = QActionGroup(self)
            else:
                for action in list(self._theme_action_group.actions()):
                    self._theme_action_group.removeAction(action)
            self._theme_action_group.setExclusive(True)
            for theme_name in THEMES.keys():
                action = QAction(theme_name, self)
                action.setCheckable(True)
                action.triggered.connect(lambda _, name=theme_name: self._on_theme_action_selected(name))
                theme_menu.addAction(action)
                self._theme_action_group.addAction(action)
                self._theme_actions[theme_name] = action
            view_menu.addSeparator()
        action_reset_layout = QAction(get_text("action_reset_layout"), self)
        action_reset_layout.setShortcut(QKeySequence("Ctrl+0"))
        action_reset_layout.triggered.connect(self._reset_layout)
        view_menu.addAction(action_reset_layout)

        macro_menu = menu_bar.addMenu(get_text("menu_macro"))
        action_macro_save = QAction(get_text("action_save"), self)
        action_macro_save.setShortcut(QKeySequence("Ctrl+S"))
        action_macro_save.triggered.connect(self.on_macro_save)
        macro_menu.addAction(action_macro_save)

        action_macro_copy = QAction(get_text("action_copy"), self)
        action_macro_copy.setShortcut(QKeySequence("Ctrl+Shift+C"))
        action_macro_copy.triggered.connect(self.on_macro_copy)
        macro_menu.addAction(action_macro_copy)

        self.action_macro_paste = QAction(get_text("action_paste"), self)
        self.action_macro_paste.setShortcut(QKeySequence("Ctrl+Shift+V"))
        self.action_macro_paste.triggered.connect(self.on_macro_paste)
        macro_menu.addAction(self.action_macro_paste)

        action_macro_clear = QAction(get_text("action_clear"), self)
        action_macro_clear.setShortcut(QKeySequence("Ctrl+Shift+D"))
        action_macro_clear.triggered.connect(self.on_macro_clear)
        macro_menu.addAction(action_macro_clear)

        macro_menu.addSeparator()
        self.action_autotrans_menu = QAction(get_text("action_autotrans"), self)
        self.action_autotrans_menu.setShortcut(QKeySequence("Ctrl+T"))
        self.action_autotrans_menu.triggered.connect(self.on_insert_autotrans)
        macro_menu.addAction(self.action_autotrans_menu)

        tools_menu = menu_bar.addMenu(get_text("menu_tools"))
        action_char_manager = QAction(get_text("action_char_manage"), self)
        action_char_manager.triggered.connect(self.on_open_char_manager)
        tools_menu.addAction(action_char_manager)
        
        action_settings = QAction(get_text("action_lang_settings"), self)
        action_settings.triggered.connect(self.on_open_settings)
        tools_menu.addAction(action_settings)

        help_menu = menu_bar.addMenu(get_text("menu_help"))
        action_shortcuts = QAction(get_text("action_shortcuts"), self)
        action_shortcuts.triggered.connect(self.on_show_shortcuts)
        help_menu.addAction(action_shortcuts)
        help_menu.addSeparator()
        action_about = QAction(get_text("action_about"), self)
        action_about.triggered.connect(self.on_show_about)
        help_menu.addAction(action_about)

        self._set_macro_paste_enabled(self.btn_macro_paste.isEnabled())
        self._ensure_theme_controls(self._current_theme())

    def _ensure_theme_controls(self, theme_name: str):
        if not theme_name:
            return
        if self.theme_combo:
            current = self.theme_combo.currentText()
            if current != theme_name:
                block = self.theme_combo.blockSignals(True)
                index = self.theme_combo.findText(theme_name)
                if index >= 0:
                    self.theme_combo.setCurrentIndex(index)
                self.theme_combo.blockSignals(block)
        for name, action in self._theme_actions.items():
            action.setChecked(name == theme_name)

    def _on_theme_action_selected(self, theme_name: str):
        if not theme_name:
            return
        if self._current_theme() == theme_name:
            self._ensure_theme_controls(theme_name)
            return
        if self.theme_combo:
            block = self.theme_combo.blockSignals(True)
            index = self.theme_combo.findText(theme_name)
            if index >= 0:
                self.theme_combo.setCurrentIndex(index)
            else:
                self.theme_combo.setCurrentText(theme_name)
            self.theme_combo.blockSignals(block)
        self.on_theme_changed(theme_name)

    def _reset_layout(self):
        """レイアウトをデフォルトに戻す"""
        if hasattr(self, "splitter") and self.splitter:
            self.splitter.setSizes([200, 1080])
        
        # デフォルトのウィンドウサイズに戻す
        self.resize(1280, 760)
        
        # 設定をすぐに保存
        self._save_settings()

    def on_show_about(self):
        QMessageBox.information(
            self,
            get_text("about_title"),
            get_text("about_text"),
        )

    def on_show_shortcuts(self):
        """ショートカット一覧ダイアログを表示"""
        QMessageBox.information(
            self,
            get_text("shortcuts_title"),
            get_text("shortcuts_text"),
        )

    # ====== Book 操作 ======
    def refresh_books(self):
        self.book_list.blockSignals(True)
        self.book_list.clear()
        for i in range(40):
            label = f"Book {i+1}"
            if self.repo and 0 <= i < len(self.repo.books):
                nm = self.repo.books[i].name.strip()
                if nm:
                    label = f"{label} — {nm}"
            self.book_list.addItem(label)
        self.book_list.blockSignals(False)
        self.book_list.setCurrentRow(self.current_book_index)
        self._refresh_set_button_labels()

    def on_book_copy(self):
        if not self.repo:
            return
        b = self.current_book_index
        self._book_clipboard = copy.deepcopy(self.repo.books[b].to_dict())
        self.statusBar().showMessage(get_text("status_copied"), 1000)

    def on_book_paste(self):
        if not self.repo or not self._book_clipboard:
            return
        b = self.current_book_index
        self.repo.books[b] = MacroBook.from_dict(copy.deepcopy(self._book_clipboard))
        self.repo.save()
        self.refresh_books(); self._reload_current_macro_into_editor(); self._refresh_set_button_labels(); self._refresh_macro_button_labels()
        self.statusBar().showMessage(get_text("status_pasted"), 1000)

    def on_book_clear(self):
        if not self.repo:
            return
        b = self.current_book_index
        self.repo.books[b] = MacroBook()
        self.repo.books[b].name = f"Book{b+1}"
        self.repo.save()
        self.refresh_books(); self._reload_current_macro_into_editor(); self._refresh_set_button_labels(); self._refresh_macro_button_labels()
        self.statusBar().showMessage(get_text("status_cleared"), 1000)

    def on_book_rename(self):
        if not self.repo:
            return
        cur = self.repo.books[self.current_book_index].name
        text, ok = QInputDialog.getText(self, get_text("dlg_book_rename"), get_text("msg_new_book_name"), text=cur)
        if ok:
            self.repo.rename_book(self.current_book_index, text)
            self.refresh_books()

    # ====== Set 操作 ======
    def on_set_copy(self):
        if not self.repo:
            return
        b, s = self.current_book_index, self.current_set_index
        self._set_clipboard = copy.deepcopy(self.repo.books[b].sets[s].to_dict())
        self.statusBar().showMessage(get_text("status_copied"), 1000)

    def on_set_paste(self):
        if not self.repo or not self._set_clipboard:
            return
        b, s = self.current_book_index, self.current_set_index
        self.repo.books[b].sets[s] = MacroSet.from_dict(copy.deepcopy(self._set_clipboard))
        self.repo.save()
        self._reload_current_macro_into_editor(); self._refresh_set_button_labels(); self._refresh_macro_button_labels()
        self.statusBar().showMessage(get_text("status_pasted"), 1000)

    def on_set_clear(self):
        if not self.repo:
            return
        b, s = self.current_book_index, self.current_set_index
        self.repo.books[b].sets[s] = MacroSet()
        self.repo.save()
        self._reload_current_macro_into_editor(); self._refresh_set_button_labels(); self._refresh_macro_button_labels()
        self.statusBar().showMessage(get_text("status_cleared"), 1000)

    def on_set_rename(self):
        if not self.repo:
            return
        cur = self.repo.books[self.current_book_index].sets[self.current_set_index].name
        text, ok = QInputDialog.getText(
            self,
            get_text("dlg_set_rename"),
            get_text("msg_new_set_name"),
            text=cur,
        )
        if ok:
            self.repo.rename_set(self.current_book_index, self.current_set_index, text)
            self._refresh_set_button_labels()

    # ====== マクロ操作 ======
    def on_macro_save(self):
        if not self.current_slot or not self.controller:
            return
        name = self.macro_name.text()
        lines = [le.text() for le in self.macro_lines]
        self.controller.write_current_macro(name=name, lines=lines)
        self._dirty = False
        self._refresh_macro_button_labels()
        from ui_i18n import get_text
        self.statusBar().showMessage(get_text("status_saved"), 1200)

    def on_macro_copy(self):
        if not self.controller or not self.current_slot:
            return
        # UI内容を一時反映（保存なし）→ コピー
        if self.repo:
            name = self.macro_name.text(); lines = [le.text() for le in self.macro_lines]
            self.repo.set_macro(
                self.controller.book_idx,
                self.controller.set_idx,
                self.controller.side,
                self.controller.macro_idx,
                name=name,
                lines=lines,
                save=False,
            )
        self.controller.copy_current(); self._set_macro_paste_enabled(True)
        self.statusBar().showMessage(get_text("status_copied"), 1000)

    def on_macro_paste(self):
        if not self.controller or not self.current_slot:
            return
        if self.controller.paste_current():
            self._reload_current_macro_into_editor(); self._refresh_macro_button_labels()
            self.statusBar().showMessage(get_text("status_pasted"), 1000)

    def on_macro_clear(self):
        if not self.controller or not self.current_slot:
            return
        self.controller.clear_current(); self._reload_current_macro_into_editor(); self._refresh_macro_button_labels()
        self.statusBar().showMessage(get_text("status_cleared"), 1000)

    # ====== 選択イベント ======
    def on_book_changed(self, row: int):
        if not self._check_unsaved_changes():
            self.book_list.blockSignals(True)
            self.book_list.setCurrentRow(self.current_book_index)
            self.book_list.blockSignals(False)
            return

        if 0 <= row < 40:
            self.current_book_index = row
            if self.controller:
                self.controller.book_idx = row
        self._reload_current_macro_into_editor(); self._refresh_set_button_labels(); self._refresh_macro_button_labels(); self._update_selection_highlight()

    def on_set_changed(self, index: int):
        self._save_current_macro_to_memory()
        self.current_set_index = index
        if self.controller:
            self.controller.set_idx = index
        self._reload_current_macro_into_editor(); self._refresh_set_button_labels(); self._refresh_macro_button_labels(); self._update_selection_highlight()

    def on_macro_selected(self, group: str, index: int):
        self._save_current_macro_to_memory()
        self.current_slot = (group, index)
        if not self.controller:
            self._macro_syncing = True
            try:
                self.macro_name.setText("")
                for i in range(6):
                    self.macro_lines[i].setText("")
                self.bulk_editor.setPlainText("")
            finally:
                self._macro_syncing = False
            self._update_selection_highlight(); return
        self.controller.side = group; self.controller.macro_idx = index
        enabled = self.repo.can_paste() if self.repo else False
        self._reload_current_macro_into_editor()
        self._set_macro_paste_enabled(enabled)
        self._refresh_macro_button_labels(); self._update_selection_highlight()

    def _reload_current_macro_into_editor(self):
        if not self.controller or self.current_slot is None:
            return
        data = self.controller.read_current_macro()
        lines = list(data.get("lines", []))
        while len(lines) < 6:
            lines.append("")
        lines = lines[:6]
        self._macro_syncing = True
        try:
            self.macro_name.setText(data.get("name", ""))
            for i in range(6):
                self.macro_lines[i].setText(lines[i])
            self.bulk_editor.setPlainText("\n".join(lines))
        finally:
            self._macro_syncing = False

    # ====== 一括テキスト ⇄ 6行 ======
    def on_bulk_apply_to_lines(self):
        if getattr(self, "_macro_syncing", False):
            return
        self._macro_syncing = True
        try:
            text = (
                self.bulk_editor.toPlainText()
                .replace("\r\n", "\n")
                .replace("\r", "\n")
            )
            parts = text.split("\n")
            for i in range(6):
                new_val = parts[i] if i < len(parts) else ""
                if self.macro_lines[i].text() != new_val:
                    self.macro_lines[i].setText(new_val)
        finally:
            self._macro_syncing = False

    def on_lines_join_to_bulk(self, _text=None):
        if getattr(self, "_macro_syncing", False):
            return
        self._macro_syncing = True
        try:
            joined = "\n".join(le.text() for le in self.macro_lines)
            if self.bulk_editor.toPlainText() != joined:
                self.bulk_editor.setPlainText(joined)
        finally:
            self._macro_syncing = False

    # ====== キャラ関連 ======
    def refresh_characters(self):
        before = self.character_combo.currentData()
        self.character_combo.blockSignals(True)
        self.character_combo.clear()
        options = []
        try:
            if storage is None:
                options = [("sample1", "SampleChar")]
            else:
                options = storage.list_characters("local")
        except Exception:
            options = [("sample1", "SampleChar")]
        if not options:
            options = [("sample1", "SampleChar")]
        selected = -1
        for idx, (cid, disp) in enumerate(options):
            self.character_combo.addItem(disp, cid)
            if before and cid == before:
                selected = idx
        self.character_combo.blockSignals(False)
        if self.character_combo.count() > 0:
            self.character_combo.setCurrentIndex(selected if selected >= 0 else 0)
            self.on_character_changed(self.character_combo.currentIndex())
        else:
            self.repo = None
            self.controller = None

    def _mark_dirty(self):
        if not getattr(self, "_macro_syncing", False):
            self._dirty = True

    def _save_current_macro_to_memory(self):
        """現在のエディタ内容をメモリ上のRepoに反映（ファイル保存はしない）"""
        if not self.repo or not self.controller or not self.current_slot:
            return
        
        name = self.macro_name.text()
        lines = [le.text() for le in self.macro_lines]
        
        self.repo.set_macro(
            self.controller.book_idx,
            self.controller.set_idx,
            self.controller.side,
            self.controller.macro_idx,
            name=name,
            lines=lines,
            save=False
        )

    def _check_unsaved_changes(self) -> bool:
        """未保存の変更があるか確認し、あれば保存するか尋ねる。
        Return:
            True: 処理続行（保存した、または保存不要、または破棄を選択）
            False: キャンセル（移動中止）
        """
        if not self._dirty:
            return True
            
        # メモリ上の最新状態を確実にRepoに入れておく
        self._save_current_macro_to_memory()
        
        ret = QMessageBox.question(
            self,
            "未保存の変更",
            "変更が保存されていません。\n保存しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes
        )
        
        if ret == QMessageBox.StandardButton.Yes:
            self.repo.save()
            self._dirty = False
            from ui_i18n import get_text
            self.statusBar().showMessage(get_text("status_saved"), 1200)
            return True
        elif ret == QMessageBox.StandardButton.No:
            self._dirty = False # 破棄
            return True
        else:
            return False

    def on_character_changed(self, _index: int):
        if not self._check_unsaved_changes():
            self.character_combo.blockSignals(True)
            if self.repo:
                idx = self.character_combo.findData(self.repo.character_id)
                if idx >= 0:
                    self.character_combo.setCurrentIndex(idx)
            self.character_combo.blockSignals(False)
            return

        cid = self.character_combo.currentData() or "sample1"
        self.repo = MacroRepository.load_or_create(character_id=str(cid))
        self.controller = MacroController(self.repo)
        self.controller.book_idx = self.current_book_index
        self.controller.set_idx = self.current_set_index
        self.controller.side = "ctrl"
        self.controller.macro_idx = 0
        self.current_slot = ("ctrl", 0)
        self.refresh_books(); self._refresh_set_button_labels(); self._reload_current_macro_into_editor(); self._refresh_macro_button_labels()
        try:
            self._set_macro_paste_enabled(self.repo.can_paste())
        except Exception:
            pass

    def on_open_char_manager(self):
        if not self._check_unsaved_changes():
            return
        before_id = self.character_combo.currentData()
        dlg = CharacterManageDialog(self)
        dlg.setModal(True); dlg.exec()
        # 再読込
        self.refresh_characters()
        # 直前のIDを再選択（無ければ先頭）
        picked = False
        for i in range(self.character_combo.count()):
            if self.character_combo.itemData(i) == before_id:
                self.character_combo.setCurrentIndex(i); picked = True; break
        if not picked and self.character_combo.count() > 0:
            self.character_combo.setCurrentIndex(0)
        self.on_character_changed(0)

    def on_open_settings(self):
        """設定ダイアログを開く"""
        from ui_settings import SettingsDialog
        dlg = SettingsDialog(self)
        dlg.exec()
        # 言語が変更された場合、UIを即時更新
        if dlg.language_changed():
            self._update_ui_texts()
    
    def _update_ui_texts(self):
        """言語変更時にUIテキストを更新"""
        from ui_i18n import get_text
        
        # 定型文辞書のキャッシュをクリア（次回開く時に新しい言語でロード）
        if reload_dictionaries is not None:
            reload_dictionaries()
        
        # ウィンドウタイトル
        self.setWindowTitle("VanaMacro")
        
        # Bookエリアのボタン
        self.btn_book_rename.setText(get_text("label_book_rename"))
        self.btn_book_copy.setText(get_text("btn_copy"))
        self.btn_book_paste.setText(get_text("btn_paste"))
        self.btn_book_clear.setText(get_text("btn_clear"))
        
        # Setエリアのボタン
        self.btn_set_rename.setText(get_text("btn_set_rename"))
        self.btn_set_copy.setText(get_text("btn_copy"))
        self.btn_set_paste.setText(get_text("btn_paste"))
        self.btn_set_clear.setText(get_text("btn_clear"))
        
        # マクロエリアのボタン
        self.btn_macro_save.setText(get_text("btn_macro_save"))
        self.btn_macro_copy.setText(get_text("btn_macro_copy"))
        self.btn_macro_paste.setText(get_text("btn_macro_paste"))
        self.btn_macro_clear.setText(get_text("btn_macro_clear"))
        
        # ツールバーとその他のラベル
        self.toolbar_char_label.setText("  " + get_text("label_character") + " ")
        self.btn_import.setText(get_text("action_import"))
        self.btn_export_center.setText(get_text("btn_export_center"))
        self.label_bulk_text.setText(get_text("label_bulk_text"))
        self.btn_autotrans_tree.setText(get_text("label_autotrans"))
        
        # メニューバーを再構築（全メニューアイテムの言語を更新）
        self._build_menu_bar()

    def on_open_export_center(self):
        if not self._check_unsaved_changes():
            return
        cid = self.character_combo.currentData()
        if not cid:
            QMessageBox.information(self, "エクスポート", "先にキャラクターを選択してください。")
            return
        dlg = ExportCenterDialog(str(cid), self.repo, self)
        dlg.setModal(True)
        dlg.exec()

    def _resolve_ffxi_folder(self, cid: str) -> Optional[Path]:
        if storage is None:
            return None
        candidates: list[Path] = []
        try:
            candidates.append(storage.ffxi_user_root() / cid)
        except Exception:
            pass
        try:
            doc_alt = storage.ffxi_user_root("ffxi_usr") / cid
            if doc_alt not in candidates:
                candidates.append(doc_alt)
        except Exception:
            pass
        try:
            candidates.append(storage.character_folder("local", cid))
        except Exception:
            pass
        for path in candidates:
            if path.exists():
                return path
        return candidates[0] if candidates else None


    # ====== FFXI 取り込み（枠） ======
    def on_ffxi_import(self):
        if not self._check_unsaved_changes():
            return
        try:
            if storage is None:
                QMessageBox.information(self, "FFXI取り込み", "storage モジュールを読み込めません。")
                return
            if self.character_combo.count() == 0:
                QMessageBox.information(self, "FFXI取り込み", "先にキャラクターを追加してください。")
                return
            cid = self.character_combo.currentData()
            if not cid:
                QMessageBox.information(self, "FFXI取り込み", "キャラクターが選択されていません。")
                return
            char_dir = self._resolve_ffxi_folder(str(cid))
            if not char_dir or not char_dir.exists():
                QMessageBox.information(self, get_text("dlg_ffxi_import_title"), f"{get_text('msg_ffxi_folder_not_found')} {char_dir}")
                return
            if ffxi_mcr is None:
                QMessageBox.information(self, get_text("dlg_ffxi_import_title"), get_text("msg_ffxi_mcr_not_loaded"))
                return

            # 警告と確認
            ret = QMessageBox.warning(
                self,
                get_text("dlg_ffxi_import"),
                get_text("msg_ffxi_import_confirm"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if ret != QMessageBox.StandardButton.Yes:
                return

            # ユーザーの要望: 内部的にマクロ保存 -> エクスポート(バックアップ) -> 取り込み
            # 現在編集中のマクロをメモリに保存
            self._save_current_macro_to_memory()
            # リポジトリをディスクに保存（エクスポート機能が最新のJSONを参照できるようにするため）
            if self.repo:
                self.repo.save()

            # バックアップ作成 (エクスポート機能を利用してスナップショットを保存)
            if not self.repo:
                self.repo = MacroRepository.load_or_create(character_id=str(cid))
            
            try:
                if exporter:
                    # 現在の状態をエクスポートフォルダに保存（JSONも含まれる）
                    exporter.export_character_macros(
                        character_id=str(cid),
                        destination=None, # デフォルトのエクスポート先を使用
                        include_snapshot=True,
                        verify=False # バックアップなので検証はスキップ
                    )
            except Exception as e:
                print(f"Backup export failed: {e}")
                # エクスポート失敗しても取り込みは続行するが、ログには残す

            snap = ffxi_mcr.import_ffxi_macros(char_dir)
            if not snap:
                QMessageBox.information(self, get_text("dlg_ffxi_import_title"), get_text("msg_ffxi_mcr_not_found"))
                return
            if not self.repo:
                self.repo = MacroRepository.load_or_create(character_id=str(cid))
            self.repo.apply_external_snapshot(snap, save=True)
            self.refresh_books()
            self._refresh_set_button_labels()
            self._refresh_macro_button_labels()
            self._reload_current_macro_into_editor()
            QMessageBox.information(self, get_text("dlg_complete"), get_text("msg_ffxi_import_complete"))
        except Exception as e:
            QMessageBox.warning(self, get_text("dlg_ffxi_import_error"), str(e))


