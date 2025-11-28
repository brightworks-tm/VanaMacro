from pathlib import Path
text = Path('ui.py').read_text('utf-8')
for i,line in enumerate(text.splitlines(),1):
    if any(ord(ch) > 127 for ch in line):
        print(i, line.encode('unicode_escape').decode())
