"""設定ダイアログ

言語設定などのアプリケーション設定を管理するダイアログ
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt

from config import Config
from ui_i18n import get_text


class SettingsDialog(QDialog):
    """設定ダイアログクラス"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(get_text("dlg_settings_title"))
        self.setMinimumWidth(400)
        
        self._original_language = Config.get_language()
        self._language_changed = False
        
        self._setup_ui()
    
    def _setup_ui(self):
        """UIのセットアップ"""
        layout = QVBoxLayout(self)
        
        # 言語設定グループ
        lang_group = QGroupBox(get_text("dlg_settings_language"))
        lang_layout = QVBoxLayout(lang_group)
        
        # 言語選択コンボボックス
        lang_select_layout = QHBoxLayout()
        lang_label = QLabel(get_text("dlg_settings_language"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem(get_text("dlg_settings_japanese"), "ja")
        self.lang_combo.addItem(get_text("dlg_settings_english"), "en")
        
        # 現在の言語を選択
        current_lang = Config.get_language()
        index = 0 if current_lang == "ja" else 1
        self.lang_combo.setCurrentIndex(index)
        
        lang_select_layout.addWidget(lang_label)
        lang_select_layout.addWidget(self.lang_combo, 1)
        lang_layout.addLayout(lang_select_layout)
        
        # 注意書き
        note_label = QLabel(get_text("dlg_settings_note"))
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: gray; font-size: 10px;")
        lang_layout.addWidget(note_label)
        
        layout.addWidget(lang_group)
        
        # ボタン
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.btn_apply = QPushButton(get_text("btn_apply"))
        self.btn_apply.clicked.connect(self._on_apply)
        button_layout.addWidget(self.btn_apply)
        
        self.btn_ok = QPushButton(get_text("btn_ok"))
        self.btn_ok.clicked.connect(self._on_ok)
        self.btn_ok.setDefault(True)
        button_layout.addWidget(self.btn_ok)
        
        self.btn_cancel = QPushButton(get_text("btn_cancel"))
        self.btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(button_layout)
    
    def _on_apply(self):
        """適用ボタンのハンドラ"""
        from config import Config
        selected_lang = self.lang_combo.currentData()
        current_lang = Config.get_language()
        
        if selected_lang != current_lang:
            Config.set_language(selected_lang)
            Config.save()  # 設定を保存
            self._language_changed = True
            
            # 言語変更完了メッセージ（即時反映される）
            QMessageBox.information(
                self,
                get_text("dlg_settings_title"),
                get_text("msg_lang_changed")
            )
    
    def _on_ok(self):
        """OKボタンのハンドラ"""
        self._on_apply()
        self.accept()
    
    def language_changed(self) -> bool:
        """言語が変更されたかどうかを返す"""
        return self._language_changed
        
