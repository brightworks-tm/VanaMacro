import json
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QComboBox, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QTextEdit, QLineEdit, QSplitter, QStatusBar, QMessageBox, QSizePolicy
)

# ============ キャラ一覧を取得する仮の関数 ============
def list_ffxi_characters():
    """
    本来は FFXI のフォルダからキャラファイルを列挙する処理を入れる。
    今は仮のキャラ名を返す。
    """
    return ["Player1", "Player2", "Player3"]


class VanaMacroUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VanaMacro (UI Preview)")
        self.resize(1200, 720)

        # 状態
        self.current_book_index = 0     # 0..39
        self.current_set_index = 0      # 0..9
        self.books = self._make_empty_books()
        self.clipboard_book = None
        self.clipboard_set = None

        # ============ 上部：キャラ名 ============
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("キャラクター名："))

        self.character_combo = QComboBox()
        self.character_combo.setFixedWidth(240)
        top_bar.addWidget(self.character_combo)

        self.btn_char_rename = QPushButton("名前変更")
        self.btn_char_rename.setEnabled(False)  # 初期は無効
        self.btn_char_rename.clicked.connect(self.on_char_rename)
        top_bar.addWidget(self.btn_char_rename)

        top_bar.addStretch(1)

        # ============ 左：Bookリスト + 操作 ============
        book_box = QGroupBox("Book")
        book_layout = QVBoxLayout(book_box)
        self.book_list = QListWidget()
        for i in range(40):
            item = QListWidgetItem(f"Book {i+1}")
            self.book_list.addItem(item)
        self.book_list.setCurrentRow(0)
        self.book_list.currentRowChanged.connect(self.on_book_changed)
        book_layout.addWidget(self.book_list)

        book_btns = QHBoxLayout()
        self.btn_book_rename = QPushButton("ブック名変更")
        self.btn_book_copy = QPushButton("コピー")
        self.btn_book_paste = QPushButton("ペースト")
        self.btn_book_rename.clicked.connect(self.on_book_rename)
        self.btn_book_copy.clicked.connect(self.on_book_copy)
        self.btn_book_paste.clicked.connect(self.on_book_paste)
        book_btns.addWidget(self.btn_book_rename)
        book_btns.addWidget(self.btn_book_copy)
        book_btns.addWidget(self.btn_book_paste)
        book_layout.addLayout(book_btns)

        # ============ 右：Set + Macro + 編集エリア ============
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Setバー
        set_row = QHBoxLayout()
        set_label = QLabel("Set:")
        set_row.addWidget(set_label)
        self.set_buttons = []
        for i in range(10):
            b = QPushButton(f"Set {i+1}")
            b.setCheckable(True)
            if i == 0:
                b.setChecked(True)
            b.clicked.connect(self._make_set_click_handler(i))
            self.set_buttons.append(b)
            set_row.addWidget(b)
        set_row.addStretch(1)

        # Set コピペ
        set_cp_row = QHBoxLayout()
        self.btn_set_copy = QPushButton("コピー")
        self.btn_set_paste = QPushButton("ペースト")
        self.btn_set_copy.clicked.connect(self.on_set_copy)
        self.btn_set_paste.clicked.connect(self.on_set_paste)
        set_cp_row.addWidget(QLabel("Set 操作:"))
        set_cp_row.addWidget(self.btn_set_copy)
        set_cp_row.addWidget(self.btn_set_paste)
        set_cp_row.addStretch(1)

        # Macro グリッド（Ctrl/Alt）
        macro_box = QGroupBox("Macros")
        macro_layout = QGridLayout(macro_box)
        macro_layout.setHorizontalSpacing(10)
        macro_layout.setVerticalSpacing(6)

        # ヘッダ行
        macro_layout.addWidget(QLabel(""), 0, 0, alignment=Qt.AlignmentFlag.AlignCenter)
        for c in range(10):
            macro_layout.addWidget(QLabel(f"{c+1}"), 0, c+1, alignment=Qt.AlignmentFlag.AlignCenter)

        # Ctrl 行
        self.ctrl_buttons = []
        self.ctrl_name_buttons = []
        macro_layout.addWidget(QLabel("Ctrl"), 1, 0, alignment=Qt.AlignmentFlag.AlignCenter)
        for c in range(10):
            col_box = QVBoxLayout()
            run = QPushButton(f"Ctrl-{c+1}")
            run.setEnabled(False)
            name_btn = QPushButton(self._slot_name_text(0, c))
            name_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            name_btn.clicked.connect(self._make_slot_select_handler(0, c))
            self.ctrl_buttons.append(run)
            self.ctrl_name_buttons.append(name_btn)
            col_w = QWidget()
            col_w.setLayout(col_box)
            col_box.addWidget(run)
            col_box.addWidget(name_btn)
            macro_layout.addWidget(col_w, 1, c+1)

        # Alt 行
        self.alt_buttons = []
        self.alt_name_buttons = []
        macro_layout.addWidget(QLabel("Alt"), 2, 0, alignment=Qt.AlignmentFlag.AlignCenter)
        for c in range(10):
            col_box = QVBoxLayout()
            run = QPushButton(f"Alt-{c+1}")
            run.setEnabled(False)
            name_btn = QPushButton(self._slot_name_text(1, c))
            name_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            name_btn.clicked.connect(self._make_slot_select_handler(1, c))
            self.alt_buttons.append(run)
            self.alt_name_buttons.append(name_btn)
            col_w = QWidget()
            col_w.setLayout(col_box)
            col_box.addWidget(run)
            col_box.addWidget(name_btn)
            macro_layout.addWidget(col_w, 2, c+1)

        # 編集エリア
        editor_box = QGroupBox("編集")
        editor_layout = QVBoxLayout(editor_box)
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("マクロ名:"))
        self.edit_name = QLineEdit()
        name_row.addWidget(self.edit_name)
        editor_layout.addLayout(name_row)

        editor_layout.addWidget(QLabel("マクロ内容（最大6行）:"))
        self.edit_text = QTextEdit()
        self.edit_text.setPlaceholderText("/ma \"Cure\" <t>\n/echo Hello\n...")
        self.edit_text.setFixedHeight(150)
        editor_layout.addWidget(self.edit_text)

        save_row = QHBoxLayout()
        self.btn_save = QPushButton("保存")
        self.btn_save.clicked.connect(self.on_save_clicked)
        save_row.addStretch(1)
        save_row.addWidget(self.btn_save)
        editor_layout.addLayout(save_row)

        # 右ペイン組み立て
        right_layout.addLayout(set_row)
        right_layout.addLayout(set_cp_row)
        right_layout.addWidget(macro_box)
        right_layout.addWidget(editor_box)

        # 左右をスプリット
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addLayout(top_bar)
        left_layout.addWidget(book_box)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        # ステータスバー
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

        container = QWidget()
        root = QHBoxLayout(container)
        root.addWidget(splitter)
        self.setCentralWidget(container)

        # キャラ一覧をロード
        self.refresh_character_combo()

        # 初期選択スロット（Ctrl-1）
        self.selected_row = 0
        self.selected_col = 0
        self._load_editor_from_state()

    # ---------- キャラ ----------
    def refresh_character_combo(self):
        self.character_combo.clear()
        for c in list_ffxi_characters():
            self.character_combo.addItem(c)
        self.btn_char_rename.setEnabled(self.character_combo.count() > 0)

    def on_char_rename(self):
        row = self.character_combo.currentIndex()
        if row < 0:
            return
        new_name, ok = self._prompt_text("キャラ名変更", "新しいキャラ名を入力:")
        if ok and new_name.strip():
            self.character_combo.setItemText(row, new_name.strip())

    # ---------- データ初期化 ----------
    def _make_empty_books(self):
        books = []
        for _ in range(40):
            sets = []
            for _ in range(10):
                rows = []
                for _row in range(2):
                    cols = []
                    for _col in range(10):
                        cols.append({"name": "", "lines": [""] * 6})
                    rows.append(cols)
                sets.append(rows)
            books.append(sets)
        return books

    # ---------- ユーティリティ ----------
    def _slot_name_text(self, row, col):
        data = self.books[self.current_book_index][self.current_set_index][row][col]
        return data["name"] if data["name"] else "(no name)"

    def _update_macro_name_buttons(self):
        for c in range(10):
            self.ctrl_name_buttons[c].setText(self._slot_name_text(0, c))
            self.alt_name_buttons[c].setText(self._slot_name_text(1, c))

    def _make_set_click_handler(self, idx):
        def handler():
            for i, b in enumerate(self.set_buttons):
                b.setChecked(i == idx)
            self.current_set_index = idx
            self._update_macro_name_buttons()
            self._load_editor_from_state()
            self.statusBar().showMessage(f"Book {self.current_book_index+1}, Set {self.current_set_index+1} selected")
        return handler

    def _make_slot_select_handler(self, row, col):
        def handler():
            self.selected_row = row
            self.selected_col = col
            self._load_editor_from_state()
            label = "Ctrl" if row == 0 else "Alt"
            self.statusBar().showMessage(f"{label}-{col+1} selected")
        return handler

    def _load_editor_from_state(self):
        data = self.books[self.current_book_index][self.current_set_index][self.selected_row][self.selected_col]
        self.edit_name.setText(data["name"])
        lines = data["lines"][:6] + [""] * (6 - len(data["lines"]))
        self.edit_text.setPlainText("\n".join(lines))

    # ---------- Book/Set ----------
    def on_book_changed(self, row):
        if row < 0:
            return
        self.current_book_index = row
        self._update_macro_name_buttons()
        self._load_editor_from_state()
        self.statusBar().showMessage(f"Book {row+1} selected")

    def on_book_rename(self):
        row = self.book_list.currentRow()
        if row < 0:
            return
        new_name, ok = self._prompt_text("ブック名変更", "新しいブック名を入力:")
        if ok:
            if new_name.strip() == "":
                QMessageBox.warning(self, "警告", "名前が空です。")
                return
            self.book_list.item(row).setText(new_name.strip())

    def on_book_copy(self):
        import copy
        self.clipboard_book = copy.deepcopy(self.books[self.current_book_index])
        self.statusBar().showMessage("Book をコピーしました")

    def on_book_paste(self):
        if self.clipboard_book is None:
            QMessageBox.information(self, "情報", "コピー済みのBookがありません。")
            return
        import copy
        self.books[self.current_book_index] = copy.deepcopy(self.clipboard_book)
        self._update_macro_name_buttons()
        self._load_editor_from_state()
        self.statusBar().showMessage("Book をペーストしました")

    def on_set_copy(self):
        import copy
        self.clipboard_set = copy.deepcopy(self.books[self.current_book_index][self.current_set_index])
        self.statusBar().showMessage("Set をコピーしました")

    def on_set_paste(self):
        if self.clipboard_set is None:
            QMessageBox.information(self, "情報", "コピー済みのSetがありません。")
            return
        import copy
        self.books[self.current_book_index][self.current_set_index] = copy.deepcopy(self.clipboard_set)
        self._update_macro_name_buttons()
        self._load_editor_from_state()
        self.statusBar().showMessage("Set をペーストしました")

    def on_save_clicked(self):
        data = self.books[self.current_book_index][self.current_set_index][self.selected_row][self.selected_col]
        data["name"] = self.edit_name.text().strip()
        text = self.edit_text.toPlainText().splitlines()
        if len(text) < 6:
            text += [""] * (6 - len(text))
        data["lines"] = text[:6]
        self._update_macro_name_buttons()
        self.statusBar().showMessage("保存（メモリ上）しました")
        import storage
        storage.macro_data = {"books": self.books}
        storage.save_to_json()


    # ---------- 小道具 ----------
    def _prompt_text(self, title, label):
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, title, label)
        return text, ok
