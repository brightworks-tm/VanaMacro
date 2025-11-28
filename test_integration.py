"""統合テスト - 英語版実装の最終確認"""
import sys

print("=" * 70)
print("英語版実装 統合テスト")
print("=" * 70)

# テスト1: モジュールのインポート
print("\n[1/5] モジュールのインポート確認")
try:
    from config import Config
    from ffxi_autotrans import load_autotrans_tree, encode_macro_text, reload_dictionaries, AutoTranslateDecoder
    from ui_i18n import get_text
    from ui_settings import SettingsDialog
    print("  ✓ すべてのモジュールをインポート成功")
except Exception as e:
    print(f"  ✗ インポートエラー: {e}")
    sys.exit(1)

# テスト2: 日本語モードの動作確認
print("\n[2/5] 日本語モードの動作確認")
try:
    Config.set_language("ja")
    reload_dictionaries()
    
    tree = load_autotrans_tree()
    decoder = AutoTranslateDecoder()
    items = decoder._ensure_items()
    
    assert len(tree) == 42, f"カテゴリ数が不正: {len(tree)}"
    assert tree[0]['name'] == "アイサツ", f"カテゴリ名が不正: {tree[0]['name']}"
    assert items[1] == "チョコボの寝ワラ", f"アイテム名が不正: {items[1]}"
    assert get_text("menu_file") == "ファイル", "UIテキストが不正"
    
    print(f"  ✓ カテゴリ: {len(tree)}件")
    print(f"  ✓ 最初のカテゴリ: {tree[0]['name']}")
    print(f"  ✓ アイテム[1]: {items[1]}")
    print(f"  ✓ UIテキスト: {get_text('menu_file')}")
except AssertionError as e:
    print(f"  ✗ アサーションエラー: {e}")
    sys.exit(1)
except Exception as e:
    print(f"  ✗ エラー: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# テスト3: 英語モードの動作確認
print("\n[3/5] 英語モードの動作確認")
try:
    Config.set_language("en")
    reload_dictionaries()
    
    tree = load_autotrans_tree()
    decoder = AutoTranslateDecoder()
    items = decoder._ensure_items()
    
    assert len(tree) == 42, f"Category count error: {len(tree)}"
    assert tree[0]['name'] == "Greetings", f"Category name error: {tree[0]['name']}"
    assert items[1] == "Chocobo Bedding", f"Item name error: {items[1]}"
    assert get_text("menu_file") == "File", "UI text error"
    
    print(f"  ✓ Categories: {len(tree)}")
    print(f"  ✓ First category: {tree[0]['name']}")
    print(f"  ✓ Item[1]: {items[1]}")
    print(f"  ✓ UI Text: {get_text('menu_file')}")
except AssertionError as e:
    print(f"  ✗ Assertion error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# テスト4: 往復変換テスト
print("\n[4/5] 往復変換テスト")
try:
    # 日本語
    Config.set_language("ja")
    reload_dictionaries()
    decoder = AutoTranslateDecoder()
    
    ja_tests = [
        "装備 <<チョコボの寝ワラ>> を使う",
        "こんにちは <<初めまして。>>",
    ]
    
    for test_text in ja_tests:
        encoded = encode_macro_text(test_text)
        decoded = decoder.decode_bytes(encoded)
        assert test_text == decoded, f"日本語往復失敗: {test_text} != {decoded}"
    
    print(f"  ✓ 日本語往復変換: {len(ja_tests)}件成功")
    
    # 英語
    Config.set_language("en")
    reload_dictionaries()
    decoder = AutoTranslateDecoder()
    
    en_tests = [
        "Use <<Chocobo Bedding>> item",
        "Hello <<Nice to meet you.>>",
    ]
    
    for test_text in en_tests:
        encoded = encode_macro_text(test_text)
        decoded = decoder.decode_bytes(encoded)
        assert test_text == decoded, f"English roundtrip failed: {test_text} != {decoded}"
    
    print(f"  ✓ English roundtrip: {len(en_tests)} tests passed")
    
except AssertionError as e:
    print(f"  ✗ アサーションエラー: {e}")
    sys.exit(1)
except Exception as e:
    print(f"  ✗ エラー: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# テスト5: 言語切り替えテスト
print("\n[5/5] 言語切り替えテスト")
try:
    # 日本語→英語→日本語
    Config.set_language("ja")
    reload_dictionaries()
    ja_cat = load_autotrans_tree()[0]['name']
    
    Config.set_language("en")
    reload_dictionaries()
    en_cat = load_autotrans_tree()[0]['name']
    
    Config.set_language("ja")
    reload_dictionaries()
    ja_cat2 = load_autotrans_tree()[0]['name']
    
    assert ja_cat == "アイサツ", f"日本語(1)エラー: {ja_cat}"
    assert en_cat == "Greetings", f"英語エラー: {en_cat}"
    assert ja_cat2 == "アイサツ", f"日本語(2)エラー: {ja_cat2}"
    
    print(f"  ✓ 日本語(1): {ja_cat}")
    print(f"  ✓ 英語    : {en_cat}")
    print(f"  ✓ 日本語(2): {ja_cat2}")
    print("  ✓ 言語切り替え正常")
    
except AssertionError as e:
    print(f"  ✗ アサーションエラー: {e}")
    sys.exit(1)
except Exception as e:
    print(f"  ✗ エラー: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 成功
print("\n" + "=" * 70)
print("🎉 統合テスト: すべて成功！")
print("=" * 70)
print("\n英語版実装は完璧に動作しています。")
print("以下の機能が利用可能です:")
print("  - 日本語/英語の辞書切り替え")
print("  - トークンのエンコード/デコード（日英対応）")
print("  - UIテキストの多言語管理")
print("  - 設定ダイアログによる言語変更")
print("\nツールを起動して「ツール」→「設定」から言語を変更できます。")
print("=" * 70)
