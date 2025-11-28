"""ui_i18n モジュールのテスト"""
from config import Config
from ui_i18n import get_text, get_all_keys
import ui_i18n

print("=== ui_i18n モジュールテスト ===\n")

# テスト1: 日本語モード
print("テスト1: 日本語モード")
Config.set_language("ja")
assert get_text("menu_file") == "ファイル"
assert get_text("btn_save") == "マクロ保存"
assert get_text("dlg_settings_title") == "設定"
print("✓ 日本語テキスト正常\n")

# テスト2: 英語モード
print("テスト2: 英語モード")
Config.set_language("en")
assert get_text("menu_file") == "File"
assert get_text("btn_save") == "Save Macro"
assert get_text("dlg_settings_title") == "Settings"
print("✓ English text OK\n")

# テスト3: 存在しないキー
print("テスト3: 存在しないキー")
result = get_text("nonexistent_key")
assert result == "nonexistent_key"
print("✓ 存在しないキーは自身を返す\n")

# テスト4: すべてのキーの整合性チェック
print("テスト4: 日英キーの整合性チェック")
ja_keys = set(ui_i18n._TEXTS["ja"].keys())
en_keys = set(ui_i18n._TEXTS["en"].keys())
missing_in_en = ja_keys - en_keys
missing_in_ja = en_keys - ja_keys

if missing_in_en:
    print(f"⚠ 英語版に不足: {missing_in_en}")
if missing_in_ja:
    print(f"⚠ 日本語版に不足: {missing_in_ja}")
if not missing_in_en and not missing_in_ja:
    print("✓ 日英のキーは完全に一致\n")

# テスト5: サンプル表示
print("テスト5: サンプルテキスト表示")
Config.set_language("ja")
print("  日本語:")
print(f"    メニュー: {get_text('menu_file')}, {get_text('menu_edit')}, {get_text('menu_tools')}")
print(f"    ボタン: {get_text('btn_save')}, {get_text('btn_import')}")

Config.set_language("en")
print("  English:")
print(f"    Menu: {get_text('menu_file')}, {get_text('menu_edit')}, {get_text('menu_tools')}")
print(f"    Button: {get_text('btn_save')}, {get_text('btn_import')}")

print("\n" + "=" * 60)
print("ui_i18n テスト完了")
print("=" * 60)
