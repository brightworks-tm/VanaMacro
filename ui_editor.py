from PyQt6.QtWidgets import QTextEdit, QCompleter
from PyQt6.QtCore import Qt, QRegularExpression
from PyQt6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QKeyEvent, QTextCursor, QAction
)
from pathlib import Path
import logging
import re
import sqlite3

# Module-level logger for optional debug output.
logger = logging.getLogger(__name__)

# FFXI マクロのコマンドリスト（優先度順）
# 頻繁に使用するコマンドを上位に配置
_PRIORITY_COMMANDS = [
    # 最もよく使うコマンド（魔法・アビリティ・WS）
    "/ma", "/magic",
    "/ja", "/jobability",
    "/ws", "/weaponskill",
    
    # 次によく使うコマンド（アイテム・装備・ペット）
    "/item",
    "/equip", "/equipset",
    "/pet",
    
    # コミュニケーション系
    "/p", "/party",
    "/l", "/linkshell",
    "/t", "/tell",
    "/s", "/say",
    "/sh", "/shout",
    "/echo",
    
    # ターゲット・アクション系
    "/attack",
    "/ra", "/range",
    "/assist",
    "/check",
    "/follow",
    
    # その他のコマンド
    "/wait",
    "/em", "/emote",
    "/heal",
    "/sit", "/stand",
    "/recast",
    "/map", "/clock", "/names"
]

def _load_autotrans_commands():
    """resources.dbからコマンドを読み込む"""
    db_path = Path(__file__).resolve().parent / "autotrans_data" / "resources.db"
    if not db_path.exists():
        return set()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT command FROM commands")
        commands = {row[0] for row in cursor.fetchall()}
        conn.close()
        return commands
    except Exception:
        return set()

# 優先度順にコマンドリストを構築
_autotrans_commands = _load_autotrans_commands()
_all_commands = set(_PRIORITY_COMMANDS) | _autotrans_commands
# 優先コマンドを先頭に、その他は後ろに追加（重複を除外）
COMMANDS = _PRIORITY_COMMANDS + [cmd for cmd in sorted(_autotrans_commands) if cmd not in _PRIORITY_COMMANDS]

# ターゲット代名詞リスト（使用頻度順）
TARGETS = [
    "<t>",      # ターゲット（最頻出）
    "<me>",     # 自分
    "<st>",     # サブターゲット
    "<bt>",     # バトルターゲット
    "<p0>", "<p1>", "<p2>", "<p3>", "<p4>", "<p5>",  # パーティメンバー
    "<pet>",    # ペット
    "<lastst>", # 最後のサブターゲット
    "<scan>",   # スキャン
    "<ft>",     # フォーカスターゲット
    "<stnpc>",  # サブターゲットNPC
    "<a10>", "<a11>", "<a12>", "<a20>", "<a21>", "<a22>"  # アライアンス
]
def _load_resource_names_from_db(resource_type, locale=None):
    """resources.dbからリソース名を読み込む"""
    db_path = Path(__file__).resolve().parent / "autotrans_data" / "resources.db"
    if not db_path.exists():
        return set()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        if locale:
            cursor.execute(
                "SELECT name FROM resource_names WHERE type = ? AND locale = ?",
                (resource_type, locale)
            )
        else:
            cursor.execute(
                "SELECT name FROM resource_names WHERE type = ?",
                (resource_type,)
            )
        names = {row[0] for row in cursor.fetchall()}
        conn.close()
        return names
    except Exception:
        return set()


def _safe_names_from_db(resource_type, locale=None):
    """resources.dbからリソース名を安全に読み込む（エラー時は空セットを返す）"""
    try:
        return _load_resource_names_from_db(resource_type, locale)
    except Exception:
        return set()


def _split_locale_lists(names):
    en: list[str] = []
    ja: list[str] = []
    for name in names:
        value = name.strip()
        if not value:
            continue
        if value.isascii():
            en.append(value.lower())
        else:
            ja.append(value)
    en.sort(key=len, reverse=True)
    ja.sort(key=len, reverse=True)
    return en, ja


JOB_ABILITY_EN, JOB_ABILITY_JA = _split_locale_lists(
    _safe_names_from_db("JobAbility")
)

# 条件付きJA（Scholar, CorsairRoll, CorsairShot, Samba, Waltz, Jig, Step, Flourish1~3など）
CONDITIONAL_JA_EN, CONDITIONAL_JA_JA = _split_locale_lists(
    _safe_names_from_db("ConditionalJA")
)

# ペットコマンド（獣使い・召喚士・からくり士・竜騎士）
PET_COMMAND_EN, PET_COMMAND_JA = _split_locale_lists(
    _safe_names_from_db("PetCommand")
)

WEAPON_SKILL_EN, WEAPON_SKILL_JA = _split_locale_lists(
    _safe_names_from_db("WeaponSkill")
)

# 魔法（spells.luaから抽出したもの + 定型文の「ウタ」カテゴリ）
_all_magic_names = _safe_names_from_db("Magic")

# 敵専用魔法を除外（プレイヤーが使えない魔法）
# 「カーズ」(Curse) や「ウィルス」(Virus) など
_enemy_only_spells = {"Curse", "カーズ", "Virus", "ウィルス"}
_all_magic_names = _all_magic_names - _enemy_only_spells

MAGIC_EN, MAGIC_JA = _split_locale_lists(_all_magic_names)

class MacroSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rules = []

        # 1. コマンド (/ma, /ws など) - 青色太字
        # 注意: 正規表現パターンは使用せず、highlightBlockで実際のコマンドリストと照合
        self.cmd_format = QTextCharFormat()
        self.cmd_format.setForeground(QColor("#4488ff"))

        # 2. ターゲット (<t>, <me> など) - 緑色
        # 定型文 <<...>> の中の <...> 部分を誤検出しないよう、前後に < や > がない場合のみマッチ
        target_format = QTextCharFormat()
        target_format.setForeground(QColor("#0c800c"))
        self.rules.append((QRegularExpression(r"(?<!<)<[a-zA-Z0-9]+>(?!>)"), target_format))

        # 3. 引用符で囲まれた文字列 ("Fire IV" など) - 茶色/オレンジ
        quote_format = QTextCharFormat()
        quote_format.setForeground(QColor("#ce9178"))
        self.rules.append((QRegularExpression(r"\".*?\""), quote_format))

        # 4. 定型文 (<< >>) - 括弧の色分け・太字
        trans_start_format = QTextCharFormat()
        trans_start_format.setForeground(QColor("#16B608"))  # 緑色
        trans_start_format.setFontWeight(QFont.Weight.Bold)
        self.rules.append((QRegularExpression(r"<<"), trans_start_format))

        trans_end_format = QTextCharFormat()
        trans_end_format.setForeground(QColor("#C70F0F"))  # 赤色
        trans_end_format.setFontWeight(QFont.Weight.Bold)
        self.rules.append((QRegularExpression(r">>"), trans_end_format))

        # 5. カテゴリ別ハイライト（後段で手動適用）
        self.job_format = QTextCharFormat()
        self.job_format.setForeground(QColor("#797924"))

        self.conditional_ja_format = QTextCharFormat()
        self.conditional_ja_format.setForeground(QColor("#ff8800"))  # オレンジ

        self.pet_command_format = QTextCharFormat()
        self.pet_command_format.setForeground(QColor("#ff66cc"))  # ピンク

        self.ws_format = QTextCharFormat()
        self.ws_format.setForeground(QColor("#4ec9b0"))

        self.magic_format = QTextCharFormat()
        self.magic_format.setForeground(QColor("#c586c0"))

        # 6. コメント (//...) - 灰色（最優先で上書き）
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#808080"))
        self.rules.append((QRegularExpression(r"//.*"), comment_format))

        # エラー警告用フォーマット（背景赤）
        self.error_format = QTextCharFormat()
        self.error_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
        self.error_format.setUnderlineColor(QColor("red"))

    def highlightBlock(self, text):
        # 既にハイライトされた範囲を追跡（重複を避けるため）
        self.highlighted_ranges = set()
        
        # 引用符の位置を記録（カテゴリハイライト時に使用）
        self.quote_ranges = []
        quote_pattern = QRegularExpression(r"\".*?\"")
        match_iter = quote_pattern.globalMatch(text)
        while match_iter.hasNext():
            match = match_iter.next()
            self.quote_ranges.append((match.capturedStart(), match.capturedStart() + match.capturedLength()))
        
        # 基本ルールの適用（ターゲット、定型文括弧、コメントなど）
        # 引用符は後でカテゴリハイライトを上書きするため、ここでは適用しない
        for pattern, fmt in self.rules:
            pattern_str = pattern.pattern()
            # 引用符パターンはスキップ（後でカテゴリハイライト後に適用）
            if pattern_str == r"\".*?\"":
                continue
            match_iter = pattern.globalMatch(text)
            while match_iter.hasNext():
                match = match_iter.next()
                start = match.capturedStart()
                length = match.capturedLength()
                self.setFormat(start, length, fmt)
                # ハイライトされた範囲を記録
                for i in range(start, start + length):
                    self.highlighted_ranges.add(i)

        # コマンドハイライト（定義されたコマンドリストに基づく）
        self._highlight_commands(text)

        # カテゴリ別ハイライト（単独ワードでも適用）
        # 優先順位：JA > Magic > WS > Conditional JA > Pet Command
        # 長い名前から先に処理されるため、部分一致を防げる
        # Magic を Conditional JA より前に処理することで、「ブレイク」が「レイク」より優先される
        lower = text.lower()
        self._highlight_name_set(text, lower, JOB_ABILITY_EN, JOB_ABILITY_JA, self.job_format)
        self._highlight_name_set(text, lower, MAGIC_EN, MAGIC_JA, self.magic_format)
        self._highlight_name_set(text, lower, WEAPON_SKILL_EN, WEAPON_SKILL_JA, self.ws_format)
        self._highlight_name_set(text, lower, CONDITIONAL_JA_EN, CONDITIONAL_JA_JA, self.conditional_ja_format)
        self._highlight_name_set(text, lower, PET_COMMAND_EN, PET_COMMAND_JA, self.pet_command_format)

        # エラー検出: Shift-JIS換算で60バイトを超える場合
        # ここでのハイライトは行わない（QTextEditのExtraSelectionsで処理する）
        pass

    def _highlight_commands(self, text):
        """定義されたコマンドリストに基づいてコマンドをハイライト"""
        lower = text.lower()
        for cmd in COMMANDS:
            cmd_lower = cmd.lower()
            start = 0
            while True:
                idx = lower.find(cmd_lower, start)
                if idx == -1:
                    break
                end = idx + len(cmd)
                # コマンドの前後が適切な区切り文字であることを確認
                # 空白、タブ、行頭/行末、定型文括弧 << >> を境界として認識
                before_ok = (idx == 0) or (text[idx - 1] in ' \t<>')
                after_ok = (end >= len(text)) or (text[end] in ' \t<>')
                # 既にハイライトされていない範囲のみ適用
                if before_ok and after_ok and not self._is_range_highlighted(idx, end):
                    self.setFormat(idx, len(cmd), self.cmd_format)
                    for i in range(idx, end):
                        self.highlighted_ranges.add(i)
                start = idx + len(cmd)

    def _highlight_name_set(self, text, lower_text, en_list, ja_list, fmt):
        if not fmt:
            return
        if en_list:
            self._highlight_english_names(text, lower_text, en_list, fmt)
        if ja_list:
            self._highlight_japanese_names(text, ja_list, fmt)

    def _highlight_english_names(self, text, lower_text, names, fmt):
        for name in names:
            start = 0
            while True:
                idx = lower_text.find(name, start)
                if idx == -1:
                    break
                end = idx + len(name)
                # 既にハイライトされていない、かつ単語境界が正しい場合のみ適用
                if self._is_ascii_word_boundary(text, idx, end) and not self._is_range_highlighted(idx, end):
                    self.setFormat(idx, len(name), fmt)
                    for i in range(idx, end):
                        self.highlighted_ranges.add(i)
                start = idx + len(name)

    def _highlight_japanese_names(self, text, names, fmt):
        # 日本語名は部分一致も許可（例：「空蝉の術」は「空蝉の術:壱」を含む）
        for name in names:
            # 完全一致
            start = 0
            while True:
                idx = text.find(name, start)
                if idx == -1:
                    break
                end = idx + len(name)
                # 単語境界チェック: 前後に日本語・英数字が続いていないかチェック
                before_ok = (idx == 0) or not self._is_word_char(text[idx - 1])
                after_ok = (end >= len(text)) or not self._is_word_char(text[end])
                # 既にハイライトされていない、かつ境界が正しい場合のみ適用
                if before_ok and after_ok and not self._is_range_highlighted(idx, end):
                    self.setFormat(idx, len(name), fmt)
                    for i in range(idx, end):
                        self.highlighted_ranges.add(i)
                start = idx + 1  # 1文字進めて次の候補を探す
            
            # ベース名の部分一致（「:」や「・」の前まで）
            base_name = name.split(':')[0].split('・')[0].strip()
            if len(base_name) >= 3 and base_name != name:  # 3文字以上で元の名前と異なる場合
                start = 0
                while True:
                    idx = text.find(base_name, start)
                    if idx == -1:
                        break
                    end = idx + len(base_name)
                    # 単語境界チェック
                    before_ok = (idx == 0) or not self._is_word_char(text[idx - 1])
                    after_ok = (end >= len(text)) or not self._is_word_char(text[end])
                    # 既にハイライトされていない、かつ境界が正しい場合のみ適用
                    if before_ok and after_ok and not self._is_range_highlighted(idx, end):
                        self.setFormat(idx, len(base_name), fmt)
                        for i in range(idx, end):
                            self.highlighted_ranges.add(i)
                    start = idx + 1

    def _is_range_highlighted(self, start, end):
        """指定された範囲が既にハイライトされているかチェック"""
        for i in range(start, end):
            if i in self.highlighted_ranges:
                return True
        return False

    @staticmethod
    def _is_ascii_word_boundary(text, start, end):
        """英語名の単語境界チェック - 引用符や空白、タグなども境界として認識"""
        if start > 0:
            prev_char = text[start - 1]
            # 引用符、空白、タグ括弧は境界として認識
            if prev_char not in ' \t"\'<>' and MacroSyntaxHighlighter._is_ascii_word_char(prev_char):
                return False
        if end < len(text):
            next_char = text[end]
            # 引用符、空白、タグ括弧は境界として認識
            if next_char not in ' \t"\'<>' and MacroSyntaxHighlighter._is_ascii_word_char(next_char):
                return False
        return True

    @staticmethod
    def _is_ascii_word_char(ch: str) -> bool:
        return ch.isascii() and (ch.isalnum() or ch == "_")
    
    @staticmethod
    def _is_word_char(ch: str) -> bool:
        """日本語・英数字を含む単語文字かチェック"""
        # 英数字、アンダースコア、またはUnicodeの文字・数字カテゴリ
        return ch.isalnum() or ch == "_" or ch.isalpha()


class MacroEditor(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighter = MacroSyntaxHighlighter(self.document())
        
        # 入力補完の設定
        self.completer = QCompleter(COMMANDS + TARGETS, self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.activated.connect(self.insert_completion)
        
        # 全角スペース自動変換用のフラグ
        self._converting_space = False
        self.textChanged.connect(self._convert_fullwidth_spaces)
        self.textChanged.connect(self._check_line_errors)
        
        # 初回チェック
        self._check_line_errors()

    def insert_completion(self, completion):
        tc = self.textCursor()
        extra = len(completion) - len(self.completer.completionPrefix())
        tc.movePosition(QTextCursor.MoveOperation.Left)
        tc.movePosition(QTextCursor.MoveOperation.EndOfWord)
        tc.insertText(completion[-extra:])
        self.setTextCursor(tc)

    def textUnderCursor(self):
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        return tc.selectedText()

    def _check_line_errors(self):
        """各行の長さをチェックし、エラーがあればExtraSelectionで警告を表示"""
        selections = []
        doc = self.document()
        
        # エラー警告用のフォーマット
        error_format = QTextCharFormat()
        error_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
        error_format.setUnderlineColor(QColor("red"))
        # 背景色や文字色は変更しない（シンタックスハイライトを維持するため）
        
        for i in range(doc.blockCount()):
            block = doc.findBlockByNumber(i)
            text = block.text()
            
            has_error = False
            try:
                # FFXIはShift-JIS (cp932)
                encoded = text.encode("cp932")
                if len(encoded) > 60:
                    has_error = True
            except UnicodeEncodeError:
                has_error = True
            
            if has_error:
                selection = QTextEdit.ExtraSelection()
                selection.format = error_format
                # 行全体を選択
                selection.cursor = QTextCursor(doc)
                selection.cursor.setPosition(block.position())
                selection.cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
                # 行全体に設定（空行の場合は幅ゼロになるが、エラー行は文字があるはず）
                selections.append(selection)
        
        self.setExtraSelections(selections)

    def _convert_fullwidth_spaces(self):
        """テキスト変更時に全角スペースを半角に自動変換"""
        if self._converting_space:
            return
        
        text = self.toPlainText()
        if '　' in text:
            self._converting_space = True
            cursor = self.textCursor()
            position = cursor.position()
            
            # 全角スペースを半角に置換
            new_text = text.replace('　', ' ')
            self.setPlainText(new_text)
            
            # カーソル位置を復元
            cursor.setPosition(min(position, len(new_text)))
            self.setTextCursor(cursor)
            
            self._converting_space = False
    
    def insertFromMimeData(self, source):
        """ペースト時に全角スペースを半角スペースに変換"""
        if source.hasText():
            text = source.text()
            # 全角スペースを半角スペースに置き換え
            text = text.replace('　', ' ')
            self.insertPlainText(text)
        else:
            super().insertFromMimeData(source)

    def keyPressEvent(self, event: QKeyEvent):
        
        if self.completer.popup().isVisible():
            if event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Escape, Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
                event.ignore()
                return

        # ショートカットキーの処理 (Ctrl+Space で補完強制表示など)
        is_shortcut = (event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_Space)

        if not self.completer or not is_shortcut:
            super().keyPressEvent(event)

        control_or_alt = event.modifiers() & (
            Qt.KeyboardModifier.ControlModifier
            | Qt.KeyboardModifier.AltModifier
            | Qt.KeyboardModifier.MetaModifier
        )
        if not self.completer or (control_or_alt and not is_shortcut):
            return

        eow = "~!@#$%^&*()_+{}|:\"?,./;'[]\\-="
        has_modifier = (event.modifiers() != Qt.KeyboardModifier.NoModifier) and not is_shortcut
        
        completion_prefix = self.textUnderCursor()

        # "/" や "<" が入力された直後、または文字入力中でプレフィックスがある場合
        text = event.text()
        if not is_shortcut and (has_modifier or not text or len(completion_prefix) < 1):
            # 特定のトリガー文字の場合は補完を開始する
            if text not in ["/", "<"]:
                self.completer.popup().hide()
                return

        if text in ["/", "<"]:
             completion_prefix = text

        if completion_prefix != self.completer.completionPrefix():
            self.completer.setCompletionPrefix(completion_prefix)
            self.completer.popup().setCurrentIndex(self.completer.completionModel().index(0, 0))

        cr = self.cursorRect()
        cr.setWidth(self.completer.popup().sizeHintForColumn(0) + self.completer.popup().verticalScrollBar().sizeHint().width())
        self.completer.complete(cr)
