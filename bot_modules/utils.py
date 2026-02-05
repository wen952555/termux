import subprocess
from telegram import Update
from telegram.ext import ContextTypes
from .config import ADMIN_ID, logger

def check_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

def get_size(bytes, suffix="B"):
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor: return f"{bytes:.1f}{unit}{suffix}"
        bytes /= factor

async def send_toast(msg):
    """Send Android Toast notification via Termux API"""
    try:
        cmd = f"termux-toast '{msg}'"
        full_path = "/data/data/com.termux/files/usr/bin/termux-toast"
        subprocess.run(f"{cmd} || {full_path} '{msg}'", shell=True, timeout=2)
    except: pass

async def clean_device():
    """Aggressively clean up recording processes using pkill"""
    try:
        # Method 1: Standard quit command
        subprocess.run("termux-microphone-record -q", shell=True, timeout=2, stderr=subprocess.DEVNULL)
        subprocess.run("termux-camera-record -q", shell=True, timeout=2, stderr=subprocess.DEVNULL)
        
        # Method 2: Force kill process by name (requires pkill/killall)
        # This fixes 'resource busy' errors when previous recording crashed
        subprocess.run("pkill -f termux-microphone-record", shell=True, stderr=subprocess.DEVNULL)
        subprocess.run("pkill -f termux-camera-record", shell=True, stderr=subprocess.DEVNULL)
        
        # Method 3: Absolute path cleanup for PRoot
        base = "/data/data/com.termux/files/usr/bin"
        subprocess.run(f"{base}/termux-microphone-record -q", shell=True, timeout=2, stderr=subprocess.DEVNULL)
        subprocess.run(f"{base}/termux-camera-record -q", shell=True, timeout=2, stderr=subprocess.DEVNULL)
    except: 
        pass

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(f"❌ 发生内部错误: {context.error}")
    except:
        pass
