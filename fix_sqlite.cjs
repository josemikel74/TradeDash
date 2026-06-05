const fs = require('fs');

let content = fs.readFileSync('trade_utils.py', 'utf-8');
content = content.replace(/sqlite3\.connect\(DB_PATH\)/g, "sqlite3.connect(DB_PATH, timeout=20, check_same_thread=False)");
content = content.replace(/sqlite3\.connect\(temp_path\)/g, "sqlite3.connect(temp_path, timeout=20, check_same_thread=False)");
fs.writeFileSync('trade_utils.py', content);
