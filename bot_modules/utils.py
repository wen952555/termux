import subprocess
import shutil
import os
import traceback
import html
import json
from telegram import Update
from telegram.ext import ContextTypes
from .config import ADMIN_ID, logger

def get_executable_path(cmd_name):
    """
    检查命令是否存在。
    如果是原生 Termux，shutil.which 应该能直接找到。
    """
    # 1. 优先检测系统 PATH
    path = shutil.which(cmd_name)
    if path:
        return path
    
    # 2. 备用检测 Termux 默认路径 (防止 PATH 环境变量异常)
    termux_bin = f"/data/data/com.termux/files/usr/bin/{cmd_name}"
    if os.path.exists(termux_bin):
        return termux_bin
        
    # 3. 找不到
    return None

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
        exe = get_executable_path("termux-toast")
        if exe:
            subprocess.run(f"{exe} '{msg}'", shell=True, timeout=2, stderr=subprocess.DEVNULL)
    except: pass

async def clean_device():
    """清理可能卡死的录制进程"""
    try:
        subprocess.run("pkill -9 termux-camera", shell=True, stderr=subprocess.DEVNULL)
        subprocess.run("pkill -9 termux-micro", shell=True, stderr=subprocess.DEVNULL)
    except: 
        pass

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    
    message = (
        f"⚠️ <b>Bot Error Report</b>\n\n"
        f"<pre>{html.escape(tb_string[-3000:])}</pre>"
    )

    try:
        if context.bot:
            await context.bot.send_message(
                chat_id=ADMIN_ID, 
                text=message, 
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")
