import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import ffxi_autotrans
import sqlite3

def test_db_loading():
    print("Testing load_autotrans_tree()...")
    tree = ffxi_autotrans.load_autotrans_tree()
    if not tree:
        print("FAIL: Tree is empty")
        return
    
    print(f"Tree loaded with {len(tree)} categories.")
    print(f"First category: {tree[0]['name']}")
    print(f"First few entries: {tree[0]['entries'][:3]}")
    
    # Find a valid entry to test encode/decode
    test_word = tree[0]['entries'][0]
    print(f"Testing with word: {test_word}")
    
    encoded = ffxi_autotrans.encode_macro_text(f"<<{test_word}>>")
    print(f"Encoded: {encoded.hex()}")
    
    decoded = ffxi_autotrans.decode_macro_bytes(encoded)
    print(f"Decoded: {decoded}")
    
    if f"<<{test_word}>>" in decoded:
        print("PASS: Encode/Decode successful")
    else:
        print(f"FAIL: Decoded string '{decoded}' does not contain '<<{test_word}>>'")

if __name__ == "__main__":
    test_db_loading()
