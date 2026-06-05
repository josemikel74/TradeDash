import re

with open('trade_utils.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("sqlite3.connect(DB_PATH)", "sqlite3.connect(DB_PATH, timeout=20, check_same_thread=False)")
content = content.replace("sqlite3.connect(temp_path)", "sqlite3.connect(temp_path, timeout=20, check_same_thread=False)")

with open('trade_utils.py', 'w', encoding='utf-8') as f:
    f.write(content)
