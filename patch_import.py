from pathlib import Path
import re
path = Path('ui.py')
text = path.read_text(encoding='utf-8')
pattern = r"        mode_key = self._current_storage_mode\(\)\\r?\\n        folder = storage.character_folder\(mode_key, cid\)\\r?\\n        if not folder.exists\(\):\\r?\\n            QMessageBox.warning\(self, \"FFXI\\u53d6\\u308a\\u8fbc\\u307f\", f\"\\u30d5\\u30a9\\u30eb\\u30c0\\u304c\\u898b\\u3064\\u304b\\u308a\\u307e\\u305b\\u3093: \{folder\}\"\)\\r?\\n            return\\r?\\n\\r?\\n        snapshot = ffxi_mcr.parse_mcr_dir\(folder\)"
replacement = "        folder = storage.ffxi_user_root(\"ffxi_usr\") / cid\\n        if not folder.exists():\\n            fallback = storage.character_folder(self._current_storage_mode(), cid)\\n            if fallback.exists():\\n                folder = fallback\\n            else:\\n                QMessageBox.warning(self, \"FFXI\\u53d6\\u308a\\u8fbc\\u307f\", f\"\\u30d5\\u30a9\\u30eb\\u30c0\\u304c\\u898b\\u3064\\u304b\\u308a\\u307e\\u305b\\u3093: {folder}\")\\n                return\\n\\n        snapshot = ffxi_mcr.parse_mcr_dir(folder)"
new_text, count = re.subn(pattern, replacement, text)
if count != 1:
    raise SystemExit(f"pattern replacements={count}")
path.write_text(new_text, encoding='utf-8')
