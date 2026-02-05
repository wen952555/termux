import logging
import os
import subprocess
import sys
import platform
import psutil
import json
import time
import socket
import shutil
import glob
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler

# --- CONFIGURATION ---
BOT_TOKEN = "8091415322:AAFuS0PJKnu8hi0WHwXoSqHuJTZJNRFzzS4"
ADMIN_ID = 1878794912
MEDIA_DIR = os.path.abspath("captured_media")
# ---------------------

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Main Menu Layout
MENU_KEYBOARD = [
    [KeyboardButton("📊 系统状态"), KeyboardButton("📂 文件管理")],
    [KeyboardButton("📸 拍摄照片"), KeyboardButton("🎤 录制音频")],
    [KeyboardButton("🔦 开启手电"), KeyboardButton("🌑 关闭手电")],
    [KeyboardButton("🔋 电池信息"), KeyboardButton("💀 进程管理")],
    [KeyboardButton("🌐 公网 IP"), KeyboardButton("💻 终端命令")],
]

if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

def check_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

# --- UTILITIES ---

def get_distro_name():
    try:
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=")[1].strip().strip('"')
    except: pass
    return "Linux"

def get_size(bytes, suffix="B"):
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor: return f"{bytes:.1f}{unit}{suffix}"
        bytes /= factor

async def send_toast(msg):
    """Send Android Toast notification via Termux API"""
    try:
        cmd = f"termux-toast '{msg}'"
        # Try direct or full path
        full_path = "/data/data/com.termux/files/usr/bin/termux-toast"
        subprocess.run(f"{cmd} || {full_path} '{msg}'", shell=True, timeout=2)
    except: pass

# --- HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
    await update.message.reply_text(
        "🤖 **Termux 控制台已就绪**\n选择下方功能进行操作:",
        reply_markup=ReplyKeyboardMarkup(MENU_KEYBOARD, resize_keyboard=True),
        parse_mode='Markdown'
    )

# --- FILE BROWSER LOGIC ---

async def show_files(update: Update, context: ContextTypes.DEFAULT_TYPE, path="."):
    abs_path = os.path.abspath(path)
    
    # Security: Don't allow going above root (though root is fine in Termux)
    if not os.path.exists(abs_path):
        await update.message.reply_text("❌ 路径不存在")
        return

    # Store current path in user_data
    context.user_data['cwd'] = abs_path
    
    # List items
    try:
        items = sorted(os.listdir(abs_path))
    except Exception as e:
        await update.message.reply_text(f"❌ 无法读取目录: {e}")
        return

    keyboard = []
    # Add "Up" button if not root
    if abs_path != "/":
        keyboard.append([InlineKeyboardButton("⬆️ 上一级", callback_data="dir:..")])

    # Add folders first, then files (limit to 20 items for UI stability)
    folders = [i for i in items if os.path.isdir(os.path.join(abs_path, i))]
    files = [i for i in items if os.path.isfile(os.path.join(abs_path, i))]
    
    # Pagination or Truncation could be added here. For now, we take top 10 folders and top 10 files.
    for f in folders[:10]:
        keyboard.append([InlineKeyboardButton(f"📂 {f}", callback_data=f"dir:{f}")])
    for f in files[:10]:
        keyboard.append([InlineKeyboardButton(f"📄 {f}", callback_data=f"file:{f}")])
    
    text = f"📂 **当前路径**: `{abs_path}`\n(只显示前20项)"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_file_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    current_cwd = context.user_data.get('cwd', os.getcwd())
    
    if data.startswith("dir:"):
        target = data.split(":", 1)[1]
        new_path = os.path.join(current_cwd, target)
        await show_files(update, context, new_path)
        
    elif data.startswith("file:"):
        filename = data.split(":", 1)[1]
        filepath = os.path.join(current_cwd, filename)
        
        await query.message.reply_text(f"📤 正在发送 `{filename}`...", parse_mode='Markdown')
        try:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=open(filepath, 'rb')
            )
        except Exception as e:
            await query.message.reply_text(f"❌ 发送失败: {e}")

# --- PROCESS MANAGER LOGIC ---

async def show_processes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent']):
        try:
            procs.append(p.info)
        except: pass
    
    # Sort by CPU usage
    top_procs = sorted(procs, key=lambda p: p['cpu_percent'] or 0, reverse=True)[:6]
    
    keyboard = []
    for p in top_procs:
        btn_text = f"{p['name'][:10]} ({p['cpu_percent']}%) ❌"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"kill:{p['pid']}")])
    
    keyboard.append([InlineKeyboardButton("🔄 刷新", callback_data="refresh_ps")])
    
    text = "💀 **进程管理**\n点击按钮强制结束进程 (Kill -9)"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_process_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "refresh_ps":
        await query.answer("刷新中...")
        await show_processes(update, context)
        return

    if data.startswith("kill:"):
        pid = int(data.split(":")[1])
        try:
            os.kill(pid, 9)
            await query.answer(f"已结束进程 PID {pid}")
            await show_processes(update, context) # Refresh list
        except Exception as e:
            await query.answer(f"失败: {e}", show_alert=True)

# --- SYSTEM & UTILS ---

async def check_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🌐 查询中...")
    try:
        # Get local IP
        local_ip = socket.gethostbyname(socket.gethostname())
        # Get public IP via curl
        public_ip = subprocess.check_output("curl -s ifconfig.me", shell=True, timeout=5).decode().strip()
        
        text = f"🌐 **网络信息**\n\n🏠 **内网 IP**: `{local_ip}`\n🌍 **公网 IP**: `{public_ip}`"
        await msg.edit_text(text, parse_mode='Markdown')
    except Exception as e:
        await msg.edit_text(f"❌ 查询失败: {e}")

async def system_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    text = (
        f"📊 **系统状态**\n"
        f"🖥 CPU: `{cpu}%`\n"
        f"🧠 内存: `{mem.percent}%` ({get_size(mem.used)}/{get_size(mem.total)})\n"
        f"💾 磁盘: `{disk.percent}%` ({get_size(disk.free)} 可用)"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def capture_media(update: Update, context: ContextTypes.DEFAULT_TYPE, media_type):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    chat_id = update.effective_chat.id
    
    # Path configuration
    termux_bin = "/data/data/com.termux/files/usr/bin"
    
    if media_type == "photo":
        filename = os.path.join(MEDIA_DIR, f"img_{timestamp}.jpg")
        cmd = f"termux-camera-photo -c 0 {filename}"
        alt_cmd = f"{termux_bin}/termux-camera-photo -c 0 {filename}"
        msg = "📸 拍照中..."
    else:
        filename = os.path.join(MEDIA_DIR, f"rec_{timestamp}.m4a")
        cmd = f"termux-microphone-record -l 10 -e aac -f {filename}"
        alt_cmd = f"{termux_bin}/termux-microphone-record -l 10 -e aac -f {filename}"
        msg = "🎤 录音中 (10s)..."

    status_msg = await update.message.reply_text(msg)
    
    try:
        subprocess.run(f"{cmd} || {alt_cmd}", shell=True, timeout=15, capture_output=True)
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            await status_msg.edit_text("📤 上传中...")
            with open(filename, 'rb') as f:
                if media_type == "photo":
                    await context.bot.send_photo(chat_id, f)
                else:
                    await context.bot.send_audio(chat_id, f)
            await status_msg.delete()
            # Try to show toast on phone
            await send_toast(f"Bot: Captured {media_type}")
        else:
            await status_msg.edit_text("❌ 获取媒体失败。请确保 Termux:API 已安装并授权。")
    except Exception as e:
        await status_msg.edit_text(f"❌ 错误: {e}")

async def toggle_torch(update: Update, state: bool):
    arg = "on" if state else "off"
    cmd = f"termux-torch {arg}"
    alt = f"/data/data/com.termux/files/usr/bin/termux-torch {arg}"
    subprocess.run(f"{cmd} || {alt}", shell=True)
    await update.message.reply_text(f"🔦 手电筒已{'开启' if state else '关闭'}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
    text = update.message.text
    
    if text == "📊 系统状态": await system_status(update, context)
    elif text == "📂 文件管理": await show_files(update, context, ".")
    elif text == "💀 进程管理": await show_processes(update, context)
    elif text == "📸 拍摄照片": await capture_media(update, context, "photo")
    elif text == "🎤 录制音频": await capture_media(update, context, "audio")
    elif text == "🔦 开启手电": await toggle_torch(update, True)
    elif text == "🌑 关闭手电": await toggle_torch(update, False)
    elif text == "🌐 公网 IP": await check_ip(update, context)
    elif text == "🔋 电池信息": 
        # Attempt to get battery status
        try:
            res = subprocess.check_output("termux-battery-status || /data/data/com.termux/files/usr/bin/termux-battery-status", shell=True).decode()
            data = json.loads(res)
            await update.message.reply_text(f"🔋 电量: {data.get('percentage')}% ({data.get('status')})")
        except:
            await update.message.reply_text("⚠️ 无法获取电池信息")
    elif text == "💻 终端命令":
        await update.message.reply_text("使用 `/exec <command>` 执行命令。\n例如: `/exec ls -lh`")

async def exec_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
    cmd = " ".join(context.args)
    if not cmd: return
    
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    out = (res.stdout + res.stderr)[:4000] or "No output"
    await update.message.reply_text(f"```\n{out}\n```", parse_mode='Markdown')

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("exec", exec_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Callback Handlers
    app.add_handler(CallbackQueryHandler(handle_file_callback, pattern="^(dir|file):"))
    app.add_handler(CallbackQueryHandler(handle_process_callback, pattern="^(kill:|refresh_ps)"))

    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
