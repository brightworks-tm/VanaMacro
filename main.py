import os
import sys

from PyQt6.QtWidgets import QApplication

from config import Config
from storage import backup_and_prepare_edit, get_theme
from ui import VanaMacroUI
from ui_theme import apply_theme


if __name__ == "__main__":
    # 設定を読み込み
    Config.load()
    
    backed_ids = backup_and_prepare_edit()
    if backed_ids:
        print(f"\u30d0\u30c3\u30af\u30a2\u30c3\u30d7\u6e96\u5099\u5b8c\u4e86: {backed_ids}")
    else:
        print("\u6ce8: FFXI USER \u30d5\u30a9\u30eb\u30c0\u304c\u898b\u3064\u304b\u3089\u305a\u3001\u30d0\u30c3\u30af\u30a2\u30c3\u30d7\u3092\u30b9\u30ad\u30c3\u30d7\u3057\u307e\u3057\u305f\u3002")

    app = QApplication(sys.argv)

    # Load and apply saved theme
    theme_name = get_theme()
    apply_theme(app, theme_name)

    window = VanaMacroUI()
    window.show()
    sys.exit(app.exec())
