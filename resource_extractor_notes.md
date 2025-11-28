# Notes: Windower ResourceExtractor と FFXI res Lua 生成

このプロジェクトでは、Windower 公式の **ResourceExtractor** が行っている処理を参考にしつつ、  
FFXI クライアントの DAT ファイルから各種リソース情報を抜き出し、自前ツール用の `res/*.lua` を生成することを目的としている。

VS Code の Codex には、このファイルを「前提知識」として読んでもらい、  
FFXI 向けツールのコード生成・改修のときに参照してほしい。

---

## 1. 目的と前提

- 対象ゲーム: **FINAL FANTASY XI (FFXI)**
- 公式ツール: **Windower ResourceExtractor (C#)**  
  - GitHub: `Windower/ResourceExtractor`
- 公式の `Resources` リポジトリにある `res/*.lua` と同等の情報を、
  - 自前ツールで
  - Windower 本体に依存せず
  - オフライン生成して配置したい。

このために、ResourceExtractor の解析ロジックを理解し、  
必要であればコードを流用／簡略化／再実装して使いたい。

---

## 2. ResourceExtractor の概要

ResourceExtractor は C# 製のコンソールツールで、主な役割は次のとおり。

1. FFXI の **DAT ファイル**から内部リソース情報を抽出
2. 中間モデル（`model` という動的オブジェクト構造）に詰める
3. そのモデルを **Lua / XML / JSON** などの形で出力
4. 一部のデータは `fixes.xml` で手動修正・追加（例: 新ジョブや例外的な名称）

プログラムの入口は `Program.cs` の `Main`。ざっくりとした流れは：

```csharp
Initialize(args);          // 引数処理・FFXIディレクトリ・出力ディレクトリ等の設定
model = new ModelObject(); // リソース全体を保持する動的モデル

ResourceParser.Initialize(model);

LoadItemData();            // Items・Monstrosity 関連
LoadMainData();            // Abilities・Spells 関連

ParseStringTables();       // 各種文字列テーブルの読込（jobs, buffs, zones など）

PostProcess();             // ID・カテゴリ分け・補助情報の整形・派生フィールドの追加
ApplyFixes();              // fixes.xml による上書き・追加

WriteData();               // Lua / XML / JSON / maps の書き出し

---

## 3. カテゴリと DAT 読み込みの仕組み

Program.cs には以下のようなカテゴリ配列がある（抜粋）:
private static readonly string[] categories = [
    "action_messages",
    "actions",
    "ability_recasts",
    "items",
    "job_abilities",
    "job_traits",
    "jobs",
    "monster_skills",
    "monstrosity",
    "spells",
    "weapon_skills",
];
さらに DatLut という辞書で、
各カテゴリごとに
どの DAT ID を
どの言語スロット（en / ja / icon_id など）として読むか
が定義されている。イメージ：
["spells"] = new() {
    [0xD996] = new() { [0] = "en" }, // 英語
    [0xD91E] = new() { [0] = "ja" }, // 日本語
},
ParseStringTables() → ParseFields(name) という流れで、

DatLut[name] に登録された複数の DAT を順に読み、

DatParser.Parse(stream, filepair.Value) で dynamic[] に変換

既存の model[name] にマージ、もしくは新規オブジェクトとして追加

という動作をしている。

---

## 4. アイテム・アビリティなどの読み込み
4.1 アイテム

LoadItemData() では、複数の DAT ID をペア（EN/JA や Armor/Weapon）で開き、ResourceParser.ParseItems() に渡している。
int[][] fileids = [
    // Armor / Weapons 用の DAT ID 群（EN/JA）
    [0x0049, 0x004A, 0x004D, 0x004C, 0x004B, 0x005B, 0xD973, 0xD974, 0xD977, 0xD975],
    [0x0004, 0x0005, 0x0008, 0x0007, 0x0006, 0x0009, 0xD8FB, 0xD8FC, 0xD8FF, 0xD8FD],
];

for (var i = 0; i < fileids[0].Length; ++i) {
    using var stream   = File.Open(GetPath(fileids[0][i]), ...); // EN
    using var streamja = File.Open(GetPath(fileids[1][i]), ...); // JA
    ResourceParser.ParseItems(stream, streamja);
}
これにより、model.items に全アイテムが集約される。

4.2 メインデータ（アビリティ/魔法など）

LoadMainData() は、特定の DAT ID (0x0051) を ResourceParser.ParseMainStream() で処理し、アクション・ジョブアビ・魔法などの基礎データを読み込む。

---

## 5. PostProcess と ApplyFixes

PostProcess() では、次のような整形処理を行う：

Buff / Key Item / Item などの構造を整理

actions を ID 範囲に応じて、

weapon_skills

job_abilities

job_traits

monster_skills
に振り分ける

auto_translates に紐づく名前を他テーブルから解決

弾種・射撃武器種などを ammo_type / range_type に分類

items_grammar や item_descriptions のようなサブテーブルを新設

ApplyFixes() では、fixes.xml からの差分を適用する。
これにより、クライアント DAT の素の情報では足りない/間違っている部分が補正される。

---

## 6. Lua へのシリアライズ方法

Lua ファイルへの書き出しは Serializers/LuaFile.cs に実装されている。

LuaFile.Write(outDir, name, entries) の動作イメージ：

using var file = new StreamWriter(Path.Combine(outDir, $"{name}.lua")) {
    NewLine = "\n",
};

// 先頭コメント（自動生成ファイルのヘッダ）
file.WriteLine("-- Automatically generated file: {0}", "Items" など);
file.WriteLine();
file.WriteLine("return {");

var keys = new HashSet<string>();
foreach (var entry in entries.Select(e => new LuaEntry(e)).OrderBy(e => e.ID)) {
    file.WriteLine($"    [{entry.ID}] = {entry},");
    keys.UnionWith(entry.Keys);
}

// テーブル終端 ＋ 使用されているキー一覧
file.WriteLine($"}}, {{ {\"id\", \"en\", \"ja\", ...} }}");

file.WriteLine();
file.WriteLine("--[[");
// ここにライセンス文言が入る
file.WriteLine("]]");


LuaEntry は dynamic オブジェクトから

固定キー: id, en, ja, enl, jal

その他のキー: アルファベット順

を Lua の { key = value, ... } 形式に整形するクラス。

重要ポイント:

各ファイルは return { [ID] = {...}, ... }, { "id", "en", ... } という
二つのテーブルを返す構造になっている（データ本体 + キー名一覧）。

ライセンス文言も自動で埋め込まれるが、自前ツールではここを独自表記に変えても良い（要ライセンス確認）。