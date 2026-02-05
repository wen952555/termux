import subprocess
import socket
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .utils import check_admin

# --- FLASHLIGHT ---

async def show_torch_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔦 开启", callback_data="torch:on"), 
         InlineKeyboardButton("🌑 关闭", callback_data="torch:off")]
    ]
    await update.message.reply_text("💡 **手电筒控制**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_torch_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action = query.data.split(":")[1]
    
    cmd = f"termux-torch {action}"
    alt = f"/data/data/com.termux/files/usr/bin/termux-torch {action}"
    
    try:
        subprocess.run(f"{cmd} || {alt}", shell=True)
        state_text = "已开启" if action == "on" else "已关闭"
        await query.answer(f"手电筒{state_text}")
    except Exception as e:
        await query.answer(f"执行失败: {e}", show_alert=True)

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
