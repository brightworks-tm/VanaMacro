"""Config モジュールの基本テスト"""
from config import Config

print("=== Config モジュールテスト ===\n")

# テスト1: デフォルト言語
print("テスト1: デフォルト言語")
assert Config.get_language() == "ja"
assert Config.is_japanese() == True
assert Config.is_english() == False
print("✓ デフォルトは日本語\n")

# テスト2: 英語への切り替え
print("テスト2: 英語への切り替え")
Config.set_language("en")
assert Config.get_language() == "en"
assert Config.is_japanese() == False
assert Config.is_english() == True
print("✓ 英語に切り替え成功\n")

# テスト3: 日本語に戻す
print("テスト3: 日本語に戻す")
Config.set_language("ja")
assert Config.get_language() == "ja"
assert Config.is_japanese() == True
print("✓ 日本語に戻せた\n")

# テスト4: 不正な言語コード
print("テスト4: 不正な言語コードの検証")
try:
    Config.set_language("fr")
    print("✗ エラーが発生しなかった（問題）")
except ValueError as e:
    print(f"✓ 期待通りエラー: {e}\n")

print("=" * 60)
print("Config モジュール: 全テスト成功！")
print("=" * 60)
