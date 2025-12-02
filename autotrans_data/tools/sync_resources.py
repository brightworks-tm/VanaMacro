import re
import ast
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RES_DIR = BASE / 'res'
DB_PATH = BASE / 'resources.db'
ENC_RES = 'utf-8'

FIELD_PATTERN = re.compile(r'(\w+)\s*=\s*("(?:[^"\\]|\\.)*")')

def decode_lua_string(value: str) -> str:
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return ""

def parse_lua_entries(path: Path):
    """Luaファイルから全フィールドを辞書として抽出（ネストされたテーブル対応）"""
    text = path.read_text(encoding=ENC_RES)
    
    # エントリの開始パターン: [数字] = {
    entry_start_pattern = re.compile(r'\[(\d+)\]\s*=\s*{')
    
    result = {}
    
    for match in entry_start_pattern.finditer(text):
        mid = int(match.group(1))
        start = match.end()
        
        # 波括弧の深さを追跡してエントリの終わりを見つける
        depth = 1
        idx = start
        length = len(text)
        
        while idx < length and depth > 0:
            char = text[idx]
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
            idx += 1
            
        if depth == 0:
            body = text[start : idx - 1]
            # フィールド抽出（数値キーやネストされたテーブルは無視し、文字列値を持つキーのみ抽出）
            fields = {}
            for field_match in FIELD_PATTERN.finditer(body):
                k, v = field_match.groups()
                fields[k] = decode_lua_string(v)
            result[mid] = fields
            
    return result

def init_db():
    if DB_PATH.exists():
        DB_PATH.unlink()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # コマンドテーブル（テキストコマンド）
    cursor.execute("""
    CREATE TABLE commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        command TEXT UNIQUE NOT NULL
    )
    """)
    
    # リソース名テーブル（ジョブアビリティ、魔法、ウェポンスキルなど）
    cursor.execute("""
    CREATE TABLE resource_names (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        locale TEXT NOT NULL
    )
    """)
    
    cursor.execute("""
    CREATE INDEX idx_resource_names_type_locale ON resource_names(type, locale)
    """)
    
    conn.commit()
    return conn

def build_commands(conn):
    """auto_translates.luaからテキストコマンドを抽出"""
    print("Building commands...")
    path = RES_DIR / 'auto_translates.lua'
    if not path.exists():
        print(f"Warning: {path} not found, skipping commands.")
        return
    
    entries = parse_lua_entries(path)
    commands = set()
    # ID 3329-3583 の範囲（3328は「テキストコマンド」カテゴリ名自体なので除外）
    command_ids = set(range(3329, 3584))
    
    for entry_id, fields in entries.items():
        if entry_id in command_ids:
            en_value = fields.get('en', '').strip()
            ja_value = fields.get('ja', '').strip()
            # コマンドは "/"で始まる
            if en_value.startswith("/"):
                commands.add(en_value)
            if ja_value.startswith("/"):
                commands.add(ja_value)
    
    cursor = conn.cursor()
    data = [(cmd,) for cmd in sorted(commands)]
    cursor.executemany("INSERT INTO commands (command) VALUES (?)", data)
    conn.commit()
    print(f"Inserted {len(data)} commands.")

def build_resource_names(conn):
    """各種Luaファイルからリソース名を抽出"""
    print("Building resource names...")
    cursor = conn.cursor()
    total_count = 0
    
    # job_abilities.lua
    path = RES_DIR / 'job_abilities.lua'
    if path.exists():
        entries = parse_lua_entries(path)
        data = []
        type_mapping = {
            'JobAbility': 'JobAbility',
            'Scholar': 'ConditionalJA',
            'CorsairRoll': 'ConditionalJA',
            'CorsairShot': 'ConditionalJA',
            'Samba': 'ConditionalJA',
            'Waltz': 'ConditionalJA',
            'Jig': 'ConditionalJA',
            'Step': 'ConditionalJA',
            'Flourish1': 'ConditionalJA',
            'Flourish2': 'ConditionalJA',
            'Flourish3': 'ConditionalJA',
            'Rune': 'ConditionalJA',
            'Ward': 'ConditionalJA',
            'Effusion': 'ConditionalJA',
            'PetCommand': 'PetCommand',
            'BloodPactRage': 'PetCommand',
            'BloodPactWard': 'PetCommand',
        }
        
        for entry_id, fields in entries.items():
            entry_type = fields.get('type', '')
            if entry_type in type_mapping:
                db_type = type_mapping[entry_type]
                en_value = fields.get('en', '').strip()
                ja_value = fields.get('ja', '').strip()
                if en_value:
                    data.append((en_value, db_type, 'en'))
                if ja_value:
                    data.append((ja_value, db_type, 'ja'))
        
        cursor.executemany(
            "INSERT INTO resource_names (name, type, locale) VALUES (?, ?, ?)",
            data
        )
        total_count += len(data)
        print(f"Inserted {len(data)} job ability entries.")
    else:
        print(f"Warning: {path} not found, skipping job abilities.")
    
    # weapon_skills.lua
    path = RES_DIR / 'weapon_skills.lua'
    if path.exists():
        entries = parse_lua_entries(path)
        data = []
        for entry_id, fields in entries.items():
            en_value = fields.get('en', '').strip()
            ja_value = fields.get('ja', '').strip()
            if en_value:
                data.append((en_value, 'WeaponSkill', 'en'))
            if ja_value:
                data.append((ja_value, 'WeaponSkill', 'ja'))
        
        cursor.executemany(
            "INSERT INTO resource_names (name, type, locale) VALUES (?, ?, ?)",
            data
        )
        total_count += len(data)
        print(f"Inserted {len(data)} weapon skill entries.")
    else:
        print(f"Warning: {path} not found, skipping weapon skills.")
    
    # spells.lua
    path = RES_DIR / 'spells.lua'
    if path.exists():
        entries = parse_lua_entries(path)
        data = []
        magic_types = {'WhiteMagic', 'BlackMagic', 'BardSong', 'Ninjutsu', 'SummonerPact', 'BlueMagic', 'Geomancy'}
        
        for entry_id, fields in entries.items():
            entry_type = fields.get('type', '')
            if entry_type in magic_types:
                en_value = fields.get('en', '').strip()
                ja_value = fields.get('ja', '').strip()
                if en_value:
                    data.append((en_value, 'Magic', 'en'))
                if ja_value:
                    data.append((ja_value, 'Magic', 'ja'))
        
        cursor.executemany(
            "INSERT INTO resource_names (name, type, locale) VALUES (?, ?, ?)",
            data
        )
        total_count += len(data)
        print(f"Inserted {len(data)} spell entries.")
    else:
        print(f"Warning: {path} not found, skipping spells.")
    
    # auto_translates.luaから歌を抽出（定型文「ウタ」カテゴリ: ID 7169-7198）
    path = RES_DIR / 'auto_translates.lua'
    if path.exists():
        entries = parse_lua_entries(path)
        song_ids = set(range(7169, 7199))
        data = []
        
        for entry_id, fields in entries.items():
            if entry_id in song_ids:
                en_value = fields.get('en', '').strip()
                ja_value = fields.get('ja', '').strip()
                # "(Song)" などの注釈を除去
                clean_en = re.sub(r'\s*\([^)]*\)', '', en_value).strip()
                clean_ja = re.sub(r'\s*\([^)]*\)', '', ja_value).strip()
                if clean_en:
                    data.append((clean_en, 'Magic', 'en'))
                if clean_ja:
                    data.append((clean_ja, 'Magic', 'ja'))
        
        if data:
            cursor.executemany(
                "INSERT INTO resource_names (name, type, locale) VALUES (?, ?, ?)",
                data
            )
            total_count += len(data)
            print(f"Inserted {len(data)} song entries from auto_translates.")
    else:
        print(f"Warning: {path} not found, skipping songs.")
    
    conn.commit()
    print(f"Total resource names inserted: {total_count}")

def main():
    print(f"Generating resources database at {DB_PATH}...")
    conn = init_db()
    try:
        build_commands(conn)
        build_resource_names(conn)
        print("Resources database generation complete.")
    finally:
        conn.close()

if __name__ == '__main__':
    main()

