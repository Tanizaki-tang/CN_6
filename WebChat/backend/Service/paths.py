'''
统一的后端路径：全部基于本文件推导，不跟"启动时的工作目录"跑
'''
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]        # WebChat/backend
DB_PATH = BASE_DIR / "chat.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
LOG_PATH = BASE_DIR / "app.log"
