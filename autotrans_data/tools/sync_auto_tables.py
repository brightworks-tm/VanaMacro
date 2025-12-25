import re
import ast
import sqlite3
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parent.parent
RES_DIR = BASE / 'res'
DB_PATH = BASE / 'autotrans.db'
ENC_RES = 'utf-8'

ENTRY_PATTERN = re.compile(r'\[(\d+)\]\s*=\s*{([^}]*)}', re.S)
FIELD_PATTERN = re.compile(r'(\w+)\s*=\s*("(?:[^"\\]|\\.)*")')

def decode_lua_string(value: str) -> str:
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return ""

def parse_lua_entries(path: Path):
    """Luaファイルから全フィールドを辞書として抽出"""
    text = path.read_text(encoding=ENC_RES)
    result = {}
    for mid, body in ENTRY_PATTERN.findall(text):
        fields = dict((k, decode_lua_string(v)) for k, v in FIELD_PATTERN.findall(body))
        result[int(mid)] = fields
    return result

def init_db():
    if DB_PATH.exists():
        DB_PATH.unlink()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE items (
        id INTEGER PRIMARY KEY,
        ja TEXT,
        en TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE categories (
        id INTEGER PRIMARY KEY,
        ja TEXT,
        en TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE auto_translates (
        category_id INTEGER,
        entry_id INTEGER,
        ja TEXT,
        en TEXT,
        PRIMARY KEY (category_id, entry_id)
    )
    """)
    
    conn.commit()
    return conn

def build_items(conn):
    print("Building items...")
    items = parse_lua_entries(RES_DIR / 'items.lua')
    data = []
    for item_id, fields in items.items():
        ja = fields.get('ja', '')
        en = fields.get('en', '')
        if ja or en:
            data.append((item_id, ja, en))
    
    cursor = conn.cursor()
    cursor.executemany("INSERT INTO items (id, ja, en) VALUES (?, ?, ?)", data)
    conn.commit()
    print(f"Inserted {len(data)} items.")

def build_auto_text(conn):
    print("Building auto-translates...")
    entries = parse_lua_entries(RES_DIR / 'auto_translates.lua')
    
    categories = []
    translates = []
    
    for mid, fields in entries.items():
        ja = fields.get('ja', '')
        en = fields.get('en', '')
        
        hi = mid // 256
        lo = mid % 256
        
        if lo == 0:
            categories.append((hi, ja, en))
        else:
            translates.append((hi, lo, ja, en))
            
    cursor = conn.cursor()
    cursor.executemany("INSERT INTO categories (id, ja, en) VALUES (?, ?, ?)", categories)
    cursor.executemany("INSERT INTO auto_translates (category_id, entry_id, ja, en) VALUES (?, ?, ?, ?)", translates)
    conn.commit()
    print(f"Inserted {len(categories)} categories and {len(translates)} entries.")

def main():
    print(f"Generating database at {DB_PATH}...")
    conn = init_db()
    try:
        build_items(conn)
        build_auto_text(conn)
        print("Database generation complete.")
    finally:
        conn.close()

if __name__ == '__main__':
    main()
