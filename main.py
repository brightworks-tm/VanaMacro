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
        print(f"バックアップ準備完了: {backed_ids}")
    else:
        print("注: FFXI USER フォルダが見つからず、バックアップをスキップしました。")

    app = QApplication(sys.argv)

    # Load and apply saved theme
    theme_name = get_theme()
    apply_theme(app, theme_name)

    window = VanaMacroUI()
    window.show()
    sys.exit(app.exec())
