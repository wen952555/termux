import os
import logging

# --- CONFIGURATION ---
BOT_TOKEN = "8091415322:AAFuS0PJKnu8hi0WHwXoSqHuJTZJNRFzzS4"
ADMIN_ID = 1878794912
MEDIA_DIR = os.path.abspath("captured_media")

# Proxy Configuration
# 优先顺序: HTTPS_PROXY > HTTP_PROXY > ALL_PROXY
PROXY_URL = (
    os.environ.get("https_proxy") or 
    os.environ.get("HTTPS_PROXY") or 
    os.environ.get("http_proxy") or 
    os.environ.get("HTTP_PROXY") or
    os.environ.get("all_proxy") or
    os.environ.get("ALL_PROXY")
)

# Create media dir if not exists
if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

# Logging Setup
# 开启详细调试日志，以便排查 "无反应" 问题
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# 抑制 httpx 的繁琐日志，除非是警告以上
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)