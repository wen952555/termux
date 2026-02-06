import subprocess
import socket
from telegram import Update
from telegram.ext import ContextTypes
from .utils import check_admin

# --- FLASHLIGHT ---

# 全局变量追踪状态 (默认为关)
TORCH_STATE = False

async def toggle_torch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global TORCH_STATE
    
    # 切换状态
    TORCH_STATE = not TORCH_STATE
    action = "on" if TORCH_STATE else "off"
    
    cmd = f"termux-torch {action}"
    alt = f"/data/data/com.termux/files/usr/bin/termux-torch {action}"
    
    try:
        # 执行命令 (不检查返回值，因为 termux-torch 有时无输出)
        subprocess.run(f"{cmd} || {alt}", shell=True)
        
        status_msg = "💡 手电筒已开启" if TORCH_STATE else "🌑 手电筒已关闭"
        await update.message.reply_text(status_msg)
        
    except Exception as e:
        # 失败回滚状态
        TORCH_STATE = not TORCH_STATE
        await update.message.reply_text(f"❌ 执行失败: {e}")

# --- IP CHECK ---

async def check_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🌐 正在查询网络信息...")
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
        # Use a reliable external service
        public_ip = subprocess.check_output("curl -s ifconfig.me", shell=True, timeout=5).decode().strip()
        text = f"🌐 **网络概览**\n\n🏠 **内网 IP**: `{local_ip}`\n🌍 **公网 IP**: `{public_ip}`"
        await msg.edit_text(text, parse_mode='Markdown')
    except Exception as e:
        await msg.edit_text(f"❌ 查询失败: {e}")

# --- SHELL EXEC ---

async def exec_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
    cmd = " ".join(context.args)
    if not cmd: return
    
    await update.message.reply_text(f"💻 执行: `{cmd}`", parse_mode='Markdown')
    
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        out = (res.stdout + res.stderr)[:4000] or "[无输出]"
        await update.message.reply_text(f"```\n{out}\n```", parse_mode='Markdown')
    except subprocess.TimeoutExpired:
        await update.message.reply_text("❌ 命令执行超时 (15s)")