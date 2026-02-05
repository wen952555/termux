import psutil
import subprocess
import json
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .utils import get_size

# --- SYSTEM STATUS ---

def get_battery_info():
    """Helper to fetch battery info via Termux API"""
    try:
        cmd = "termux-battery-status"
        alt_cmd = "/data/data/com.termux/files/usr/bin/termux-battery-status"
        res = subprocess.check_output(f"{cmd} || {alt_cmd}", shell=True, stderr=subprocess.DEVNULL).decode()
        data = json.loads(res)
        return f"{data.get('percentage')}% ({data.get('status')})"
    except:
        return "未知 (需 Termux:API)"

async def system_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    battery = get_battery_info()
    
    text = (
        f"📊 **系统状态报告**\n"
        f"────────────────\n"
        f"🔋 **电池**: `{battery}`\n"
        f"🖥 **CPU**: `{cpu}%`\n"
        f"🧠 **内存**: `{mem.percent}%`\n"
        f"   └ 使用: {get_size(mem.used)} / {get_size(mem.total)}\n"
        f"💾 **磁盘**: `{disk.percent}%`\n"
        f"   └ 剩余: {get_size(disk.free)}"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def force_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pull latest code from git and restart"""
    await update.message.reply_text("🔄 正在从 Git 更新代码并重启...", parse_mode='Markdown')
    
    try:
        # Pull git
        subprocess.run("git pull", shell=True, check=True)
        # Exit so PM2/Loop can restart it
        await update.message.reply_text("✅ 代码更新成功，正在重启 Bot 进程...")
        os.execv(sys.executable, ['python'] + sys.argv)
    except Exception as e:
        await update.message.reply_text(f"❌ 更新失败: {e}")

# --- PROCESS MANAGER ---

async def show_processes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent']):
        try:
            procs.append(p.info)
        except: pass
    
    top_procs = sorted(procs, key=lambda p: p['cpu_percent'] or 0, reverse=True)[:6]
    
    keyboard = []
    for p in top_procs:
        btn_text = f"{p['name'][:10]} ({p['cpu_percent']}%) ❌"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"kill:{p['pid']}")])
    
    keyboard.append([InlineKeyboardButton("🔄 刷新列表", callback_data="refresh_ps")])
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
            await show_processes(update, context)
        except Exception as e:
            await query.answer(f"失败: {e}", show_alert=True)
