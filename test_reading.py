import pykakasi

# カスタム辞書
custom_dict = {
    "八之太刀": "はちのたち",
    "明鏡止水": "めいきょうしすい",
    "空蝉": "うつせみ",
    "震天動地": "しんてんどうち",
}

kks = pykakasi.kakasi()

# テストケース
test_cases = [
    "八之太刀・月光",
    "明鏡止水",
    "空蝉の術:壱",
    "震天動地の章"
]

print("=== カスタム辞書なし ===")
for text in test_cases:
    result = kks.convert(text)
    hiragana = ''.join([item['hira'] for item in result])
    print(f"{text} -> {hiragana}")

print("\n=== カスタム辞書あり ===")
for text in test_cases:
    # カスタム辞書で置き換え
    text_replaced = text
    for kanji, hiragana_reading in custom_dict.items():
        text_replaced = text_replaced.replace(kanji, hiragana_reading)
    
    result = kks.convert(text_replaced)
    hiragana = ''.join([item['hira'] for item in result])
    print(f"{text} -> {hiragana}")
