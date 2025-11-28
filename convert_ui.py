from pathlib import Path
path = Path('ui.py')
data = path.read_bytes()
if data.startswith(b'\xef\xbb\xbf'):
    data = data[3:]
text = data.decode('cp932')
path.write_text(text, encoding='utf-8')
