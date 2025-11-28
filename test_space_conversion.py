from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from ui_editor import MacroEditor
import sys

app = QApplication(sys.argv)

window = QMainWindow()
window.setWindowTitle("全角スペース変換テスト")
window.resize(600, 400)

central = QWidget()
layout = QVBoxLayout(central)

label = QLabel("全角入力モードでスペースキーを押してください。半角スペースに変換されるはずです。")
layout.addWidget(label)

editor = MacroEditor()
layout.addWidget(editor)

window.setCentralWidget(central)
window.show()

print("テストウィンドウを表示しました。")
print("1. 全角入力モードに切り替えてください")
print("2. エディタで「あ[スペース]い[スペース]う」と入力してください")
print("3. スペースが半角になっているか確認してください")

sys.exit(app.exec())
