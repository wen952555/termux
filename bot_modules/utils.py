import subprocess
import shutil
import os
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
