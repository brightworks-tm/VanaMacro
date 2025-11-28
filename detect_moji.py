from pathlib import Path
text = Path('ui.py').read_text(encoding='utf-8')
for i,line in enumerate(text.splitlines(),1):
    if '\ufffd' in line or '�' in line:
        print(f"{i}: {line}")
