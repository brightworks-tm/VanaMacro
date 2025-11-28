"""
.ttl ファイルの完全なバイナリ構造を解析して表示
"""
from pathlib import Path
import sys

TITLE_HEADER_SIZE = 16
TITLE_ENTRY_SIZE = 16
NAME_OFFSET_IN_ENTRY = 8
NAME_BYTES = 8

def analyze_ttl(ttl_path: Path):
    """ttl ファイルの構造を詳細に解析"""
    if not ttl_path.exists():
        print(f"ファイルが見つかりません: {ttl_path}")
        return
    
    data = ttl_path.read_bytes()
    print(f"\n{'='*70}")
    print(f"ファイル: {ttl_path.name}")
    print(f"サイズ: {len(data)} bytes")
    print(f"{'='*70}")
    
    # ヘッダー (16 bytes)
    print("\n[ヘッダー部分 0-15]")
    header = data[0:TITLE_HEADER_SIZE]
    hex_dump = ' '.join(f'{b:02X}' for b in header)
    print(f"  HEX: {hex_dump}")
    
    # 各エントリ (20 entries x 16 bytes)
    print(f"\n[Book エントリ部分 16-{TITLE_HEADER_SIZE + 20*TITLE_ENTRY_SIZE - 1}]")
    for idx in range(20):
        entry_offset = TITLE_HEADER_SIZE + (idx * TITLE_ENTRY_SIZE)
        entry = data[entry_offset:entry_offset + TITLE_ENTRY_SIZE]
        
        # エントリ全体
        hex_dump = ' '.join(f'{b:02X}' for b in entry)
        
        # Book 名部分 (offset +8, 8 bytes)
        name_offset = entry_offset + NAME_OFFSET_IN_ENTRY
        name_bytes = data[name_offset:name_offset + NAME_BYTES]
        null_pos = name_bytes.find(b'\x00')
        if null_pos != -1:
            name_bytes = name_bytes[:null_pos]
        try:
            name = name_bytes.decode('cp932', errors='ignore')
        except:
            name = "(decode error)"
        
        # その他のフィールド (offset +0~7, +8~15)
        before_name = entry[0:NAME_OFFSET_IN_ENTRY]
        after_name = entry[NAME_OFFSET_IN_ENTRY + NAME_BYTES:] if len(entry) > NAME_OFFSET_IN_ENTRY + NAME_BYTES else b''
        
        before_hex = ' '.join(f'{b:02X}' for b in before_name)
        after_hex = ' '.join(f'{b:02X}' for b in after_name) if after_name else ''
        
        print(f"\n  Entry {idx} (Book {idx+1}): '{name}'")
        print(f"    [0-7]   : {before_hex}")
        print(f"    [8-15]  : {hex_dump[24:47]} (Book名)")
        if after_hex:
            print(f"    [16+]   : {after_hex}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python analyze_ttl.py <file1.ttl> [file2.ttl]")
        print("\n2つのファイルを指定すると比較します")
        sys.exit(1)
    
    file1 = Path(sys.argv[1])
    analyze_ttl(file1)
    
    if len(sys.argv) > 2:
        file2 = Path(sys.argv[2])
        analyze_ttl(file2)
        
        # 差分を表示
        print(f"\n{'='*70}")
        print("差分比較")
        print(f"{'='*70}")
        
        data1 = file1.read_bytes()
        data2 = file2.read_bytes()
        
        min_len = min(len(data1), len(data2))
        differences = []
        
        for i in range(min_len):
            if data1[i] != data2[i]:
                differences.append(i)
        
        if differences:
            print(f"\n{len(differences)} bytes が異なります:")
            for offset in differences[:50]:  # 最初の50個のみ表示
                print(f"  Offset {offset:04d}: {data1[offset]:02X} vs {data2[offset]:02X}")
            if len(differences) > 50:
                print(f"  ... 他 {len(differences) - 50} bytes")
        else:
            print("\nファイルは完全に一致しています")
