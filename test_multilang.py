"""多言語機能のテスト"""
from config import Config
from ffxi_autotrans import (
    load_autotrans_tree,
    encode_macro_text,
    AutoTranslateDecoder,
    reload_dictionaries
)

print("=" * 60)
print("多言語機能テスト")
print("=" * 60)

def test_japanese_mode():
    print("\n=== 日本語モードテスト ===")
    Config.set_language("ja")
    reload_dictionaries()
    
    tree = load_autotrans_tree()
    print(f"カテゴリ数: {len(tree)}")
    print(f"最初のカテゴリ: {tree[0]['name']}")
    print(f"最初のエントリ: {tree[0]['entries'][0]}")
    
    decoder = AutoTranslateDecoder()
    items = decoder._ensure_items()
    print(f"アイテム[1]: {items[1]}")
    
    # 検証
    assert tree[0]['name'] == "アイサツ", f"カテゴリ名が不正: {tree[0]['name']}"
    assert items[1] == "チョコボの寝ワラ", f"アイテム名が不正: {items[1]}"
    print("✓ 日本語モード正常")
    return tree, items


def test_english_mode():
    print("\n=== 英語モードテスト ===")
    Config.set_language("en")
    reload_dictionaries()
    
    tree = load_autotrans_tree()
    print(f"Categories: {len(tree)}")
    print(f"First category: {tree[0]['name']}")
    print(f"First entry: {tree[0]['entries'][0]}")
    
    decoder = AutoTranslateDecoder()
    items = decoder._ensure_items()
    print(f"Item[1]: {items[1]}")
    
    # 検証
    assert tree[0]['name'] == "Greetings", f"Category name error: {tree[0]['name']}"
    assert items[1] == "Chocobo Bedding", f"Item name error: {items[1]}"
    print("✓ English mode OK")
    return tree, items


def test_roundtrip_japanese():
    print("\n=== 往復変換テスト（日本語） ===")
    Config.set_language("ja")
    reload_dictionaries()
    
    decoder = AutoTranslateDecoder()
    test_cases = [
        "装備 <<チョコボの寝ワラ>> を使う",
        "こんにちは <<初めまして。>> よろしく",
        "/wave motion <<サポートジョブ>>",
    ]
    
    for test_text in test_cases:
        encoded = encode_macro_text(test_text)
        decoded = decoder.decode_bytes(encoded)
        print(f"  '{test_text[:30]}...' -> {len(encoded)} bytes -> OK" if test_text == decoded else f"  ✗ FAIL")
        assert test_text == decoded, f"往復変換失敗: {test_text} != {decoded}"
    
    print("✓ 日本語往復変換成功")


def test_roundtrip_english():
    print("\n=== 往復変換テスト（英語） ===")
    Config.set_language("en")
    reload_dictionaries()
    
    decoder = AutoTranslateDecoder()
    test_cases = [
        "Use <<Chocobo Bedding>> item",
        "Hello <<Nice to meet you.>> Thanks",
        "/wave motion <<Support Job>>",
    ]
    
    for test_text in test_cases:
        encoded = encode_macro_text(test_text)
        decoded = decoder.decode_bytes(encoded)
        print(f"  '{test_text[:30]}...' -> {len(encoded)} bytes -> OK" if test_text == decoded else f"  ✗ FAIL")
        assert test_text == decoded, f"Roundtrip failed: {test_text} != {decoded}"
    
    print("✓ English roundtrip OK")


def test_language_switching():
    print("\n=== 言語切り替えテスト ===")
    
    # 日本語→英語→日本語
    Config.set_language("ja")
    reload_dictionaries()
    tree_ja1 = load_autotrans_tree()
    
    Config.set_language("en")
    reload_dictionaries()
    tree_en = load_autotrans_tree()
    
    Config.set_language("ja")
    reload_dictionaries()
    tree_ja2 = load_autotrans_tree()
    
    print(f"  日本語(1): {tree_ja1[0]['name']}")
    print(f"  英語    : {tree_en[0]['name']}")
    print(f"  日本語(2): {tree_ja2[0]['name']}")
    
    assert tree_ja1[0]['name'] == "アイサツ"
    assert tree_en[0]['name'] == "Greetings"
    assert tree_ja2[0]['name'] == "アイサツ"
    
    print("✓ 言語切り替え正常")


# テスト実行
try:
    test_japanese_mode()
    test_english_mode()
    test_roundtrip_japanese()
    test_roundtrip_english()
    test_language_switching()
    
    print("\n" + "=" * 60)
    print("全テスト成功！多言語機能は正常に動作しています。")
    print("=" * 60)
    
except AssertionError as e:
    print(f"\n✗ テスト失敗: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"\n✗ エラー発生: {e}")
    import traceback
    traceback.print_exc()
