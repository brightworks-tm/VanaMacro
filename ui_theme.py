"""
Manages UI themes.
"""

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

# Slightly ornate brown/gold palette inspired by RPG UIs.
FFXI_QSS = """
QWidget {
    background-color: #18100b;
    color: #e5d6b1;
    selection-background-color: #3a4f73;
    selection-color: #f6f6f6;
}
QMainWindow {
    background-color: #18100b;
}
QGroupBox {
    background-color: #1f150d;
    border: 1px solid #7b6843;
    border-radius: 2px;
    margin-top: 8px;
    padding: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 6px;
    padding: 0 4px;
    color: #d4c79b;
}
QPushButton {
    background-color: #2b2216;
    color: #e5d6b1;
    border: 1px solid #7b6843;
    border-radius: 2px;
    padding: 6px 10px;
}
QPushButton:hover {
    background-color: #33291a;
}
QPushButton:pressed {
    background-color: #3a2e1e;
}
QPushButton:checked, QPushButton:default {
    background-color: #3d3020;
    border-color: #a08850;
    color: #f5ead0;
    font-weight: bold;
}
QPushButton:disabled {
    color: #a79a7a;
    background-color: #241a11;
    border-color: #4d3f29;
}
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #120d08;
    color: #e5d6b1;
    border: 1px solid #6d5836;
    selection-background-color: #334b70;
    selection-color: #eef2f9;
}
QListWidget {
    background-color: #120d08;
    color: #e5d6b1;
    border: 1px solid #6d5836;
}
QListWidget::item:selected {
    background: #334b70;
    color: #eef2f9;
}
QComboBox {
    background-color: #2b2216;
    color: #e5d6b1;
    border: 1px solid #7b6843;
    padding: 4px 8px;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #7b6843;
}
QComboBox QAbstractItemView {
    background-color: #120d08;
    color: #e5d6b1;
    selection-background-color: #334b70;
}
QSplitter::handle {
    background-color: #7b6843;
    width: 2px;
}
QStatusBar {
    background-color: #1c140c;
    color: #cfc29a;
}
QScrollBar:vertical {
    background: #120d08;
    width: 12px;
    margin: 4px 0 4px 0;
    border: 1px solid #6d5836;
}
QScrollBar::handle:vertical {
    background: #2f2518;
    min-height: 24px;
    border: 1px solid #8b7345;
}
QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical {
    background: #2f2518;
    height: 14px;
    border: 1px solid #8b7345;
}
QMenuBar {
    background-color: #18100b;
    color: #e5d6b1;
}
QMenuBar::item:selected {
    background-color: #3a4f73;
    color: #f6f6f6;
}
QMenu {
    background-color: #1f150d;
    color: #e5d6b1;
    border: 1px solid #7b6843;
}
QMenu::item:selected {
    background-color: #3a4f73;
    color: #f6f6f6;
}
"""

# Modern dark theme with cool gray/blue tones
DARK_QSS = """
QWidget {
    background-color: #1e1e1e;
    color: #d4d4d4;
    selection-background-color: #264f78;
    selection-color: #ffffff;
}
QMainWindow {
    background-color: #1e1e1e;
}
QGroupBox {
    background-color: #252526;
    border: 1px solid #3e3e42;
    border-radius: 3px;
    margin-top: 8px;
    padding: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 6px;
    padding: 0 4px;
    color: #cccccc;
}
QPushButton {
    background-color: #2d2d30;
    color: #cccccc;
    border: 1px solid #3e3e42;
    border-radius: 2px;
    padding: 6px 10px;
}
QPushButton:hover {
    background-color: #3e3e42;
    border-color: #007acc;
}
QPushButton:pressed {
    background-color: #007acc;
    color: #ffffff;
}
QPushButton:checked, QPushButton:default {
    background-color: #0e639c;
    border-color: #007acc;
    color: #ffffff;
    font-weight: bold;
}
QPushButton:disabled {
    color: #656565;
    background-color: #2d2d30;
    border-color: #3e3e42;
}
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #1e1e1e;
    color: #d4d4d4;
    border: 1px solid #3e3e42;
    selection-background-color: #264f78;
    selection-color: #ffffff;
}
QListWidget {
    background-color: #252526;
    color: #cccccc;
    border: 1px solid #3e3e42;
}
QListWidget::item:selected {
    background: #094771;
    color: #ffffff;
}
QComboBox {
    background-color: #2d2d30;
    color: #cccccc;
    border: 1px solid #3e3e42;
    padding: 4px 8px;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #3e3e42;
}
QComboBox QAbstractItemView {
    background-color: #252526;
    color: #cccccc;
    selection-background-color: #094771;
    selection-color: #ffffff;
}
QSplitter::handle {
    background-color: #3e3e42;
    width: 2px;
}
QStatusBar {
    background-color: #007acc;
    color: #ffffff;
}
QScrollBar:vertical {
    background: #1e1e1e;
    width: 12px;
    margin: 4px 0 4px 0;
    border: 1px solid #3e3e42;
}
QScrollBar::handle:vertical {
    background: #424242;
    min-height: 24px;
    border: 1px solid #3e3e42;
}
QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical {
    background: #2d2d30;
    height: 14px;
    border: 1px solid #3e3e42;
}
QMenuBar {
    background-color: #1e1e1e;
    color: #d4d4d4;
}
QMenuBar::item:selected {
    background-color: #094771;
    color: #ffffff;
}
QMenu {
    background-color: #252526;
    color: #d4d4d4;
    border: 1px solid #3e3e42;
}
QMenu::item:selected {
    background-color: #094771;
    color: #ffffff;
}
"""

THEMES = {
    "Base": "",
    "Dark": DARK_QSS,
    "Game": FFXI_QSS,
}
DEFAULT_THEME = "Base"


def _store_original_font(app):
    if not hasattr(app, '_original_font'):
        app._original_font = app.font()


def _apply_game_font(app):
    """
    Apply a font that keeps Japanese glyphs intact.
    """
    font_order = [
        "Meiryo UI",
    ]

    families = set(QFontDatabase.families())
    chosen = None
    for family in font_order:
        if family in families:
            chosen = family
            break

    if chosen:
        base = QFont(chosen)
        base.setPointSize(max(app.font().pointSize(), 10))
        app.setFont(base)


def _revert_font(app):
    if hasattr(app, '_original_font'):
        app.setFont(app._original_font)


def apply_theme(app, theme_name):
    """
    Apply the selected theme to the application.
    """
    _store_original_font(app)

    # Remember the active theme on the QApplication so widgets can adjust per-theme accents.
    app.setProperty("vanamacro_theme", theme_name)

    qss = THEMES.get(theme_name, "")
    app.setStyleSheet(qss)

    if theme_name == "Game":
        _apply_game_font(app)
    else:
        _revert_font(app)
