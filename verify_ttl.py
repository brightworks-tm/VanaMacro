"""
mcr.ttl / mcr_2.ttl ファイルから Book 名を読み取って表示するスクリプト
"""
from pathlib import Path
import sys

TITLE_HEADER_SIZE = 16
TITLE_ENTRY_SIZE = 16
NAME_OFFSET_IN_ENTRY = 8
NAME_BYTES = 8

def read_book_names(ttl_path: Path, start_book: int = 0):
    """ttl ファイルから Book 名を読み取る"""
    if not ttl_path.exists():
        print(f"ファイルが見つかりません: {ttl_path}")
        return
    
    data = ttl_path.read_bytes()
    print(f"\nファイル: {ttl_path}")
    print(f"サイズ: {len(data)} bytes")
    print(f"\nBook 名:")
    print("-" * 60)
    
    for idx in range(20):
        book_num = start_book + idx + 1
        offset = TITLE_HEADER_SIZE + (idx * TITLE_ENTRY_SIZE) + NAME_OFFSET_IN_ENTRY
        
        if offset + NAME_BYTES > len(data):
            print(f"Book {book_num:2d}: データ範囲外")
            continue
        
        name_bytes = data[offset:offset + NAME_BYTES]
        # NULL 終端までを取得
        null_pos = name_bytes.find(b'\x00')
        if null_pos != -1:
            name_bytes = name_bytes[:null_pos]
        
        try:
            name = name_bytes.decode('cp932', errors='ignore')
        except:
            name = "(decode error)"
        
        # バイナリダンプも表示
        hex_dump = ' '.join(f'{b:02X}' for b in data[offset:offset + NAME_BYTES])
        print(f"Book {book_num:2d}: '{name}' (hex: {hex_dump})")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        ttl1 = Path(sys.argv[1])
        ttl2 = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    else:
        # デフォルト: 最新のエクスポートフォルダを探す
        print("使い方: python verify_ttl.py <mcr.ttl のパス> [mcr_2.ttl のパス]")
        print("\nまたは、引数なしで実行すると最新のエクスポートフォルダから読み込みます。")
        
        # data/export から最新を探す
        export_root = Path("data/export")
        if not export_root.exists():
            print(f"\n{export_root} が見つかりません。")
            sys.exit(1)
        
        # キャラIDフォルダを探す
        char_folders = [d for d in export_root.iterdir() if d.is_dir()]
        if not char_folders:
            print(f"\n{export_root} 内にキャラフォルダが見つかりません。")
            sys.exit(1)
        
        # 最新のキャラフォルダ
        char_folder = sorted(char_folders)[-1]
        
        # タイムスタンプフォルダを探す
        timestamp_folders = [d for d in char_folder.iterdir() if d.is_dir()]
        if not timestamp_folders:
            print(f"\n{char_folder} 内にエクスポートフォルダが見つかりません。")
            sys.exit(1)
        
        # 最新のエクスポートフォルダ
        latest = sorted(timestamp_folders)[-1]
        
        ttl1 = latest / "mcr.ttl"
        ttl2 = latest / "mcr_2.ttl"
        
        print(f"\n最新のエクスポートフォルダ: {latest}")
    
    # mcr.ttl (Book 1-20)
    read_book_names(ttl1, start_book=0)
    
    # mcr_2.ttl (Book 21-40)
    if ttl2 and ttl2.exists():
        read_book_names(ttl2, start_book=20)
