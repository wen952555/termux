import os
import logging

# --- CONFIGURATION ---
BOT_TOKEN = "8091415322:AAFuS0PJKnu8hi0WHwXoSqHuJTZJNRFzzS4"
ADMIN_ID = 1878794912
MEDIA_DIR = os.path.abspath("captured_media")

# Proxy Configuration
# 自动读取环境变量中的代理设置 (如 export http_proxy=http://127.0.0.1:7890)
PROXY_URL = os.environ.get("http_proxy") or os.environ.get("HTTP_PROXY")

# Create media dir if not exists
if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

# Logging Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)