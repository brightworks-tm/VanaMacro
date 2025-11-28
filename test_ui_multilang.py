"""UI多言語化の動作確認"""
print("=" * 70)
print("UI多言語化 動作確認")
print("=" * 70)

# 1. モジュールのインポート
print("\n[1] モジュールのインポート確認")
try:
    from config import Config
    from ui_i18n import get_text
    print("  ✓ インポート成功")
except Exception as e:
    print(f"  ✗ エラー: {e}")
    import sys
    sys.exit(1)

# 2. 日本語モードのテキスト確認
print("\n[2] 日本語モードのテキスト")
Config.set_language("ja")
texts_ja = {
    "autotrans_title": get_text("autotrans_title"),
    "btn_insert": get_text("btn_insert"),
    "btn_close": get_text("btn_close"),
    "btn_macro_save": get_text("btn_macro_save"),
    "btn_copy": get_text("btn_copy"),
    "status_saved": get_text("status_saved"),
}

for key, value in texts_ja.items():
    print(f"  {key}: {value}")

# 3. 英語モードのテキスト確認
print("\n[3] 英語モードのテキスト")
Config.set_language("en")
texts_en = {
    "autotrans_title": get_text("autotrans_title"),
    "btn_insert": get_text("btn_insert"),
    "btn_close": get_text("btn_close"),
    "btn_macro_save": get_text("btn_macro_save"),
    "btn_copy": get_text("btn_copy"),
    "status_saved": get_text("status_saved"),
}

for key, value in texts_en.items():
    print(f"  {key}: {value}")

# 4. 言語切り替えテスト
print("\n[4] 言語切り替えテスト")
Config.set_language("ja")
assert get_text("btn_insert") == "挿入", "日本語エラー"
print(f"  ✓ 日本語: {get_text('btn_insert')}")

Config.set_language("en")
assert get_text("btn_insert") == "Insert", "英語エラー"
print(f"  ✓ English: {get_text('btn_insert')}")

Config.set_language("ja")
assert get_text("btn_insert") == "挿入", "日本語(2)エラー"
print(f"  ✓ 日本語(2): {get_text('btn_insert')}")

print("\n" + "=" * 70)
print("✅ UI多言語化の動作確認: 成功！")
print("=" * 70)
print("\n次のステップ:")
print("  1. python main.py でツールを起動")
print("  2. 「ツール」→「設定」で言語を English に変更")
print("  3. 定型文ダイアログ等のボタンが英語になっているか確認")
print("=" * 70)
