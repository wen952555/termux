import os
import logging

# --- CONFIGURATION ---
BOT_TOKEN = "8091415322:AAFuS0PJKnu8hi0WHwXoSqHuJTZJNRFzzS4"
ADMIN_ID = 1878794912
MEDIA_DIR = os.path.abspath("captured_media")

# Create media dir if not exists
if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

# Logging Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
