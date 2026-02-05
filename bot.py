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
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# --- 配置区域 ---
BOT_TOKEN = "8091415322:AAFuS0PJKnu8hi0WHwXoSqHuJTZJNRFzzS4"
ADMIN_ID = 1878794912
# ----------------

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 键盘菜单布局
MENU_KEYBOARD = [
    [KeyboardButton("📊 系统状态"), KeyboardButton("📈 进程列表")],
    [KeyboardButton("📂 文件管理"), KeyboardButton("🛠 服务探测")],
    [KeyboardButton("🔋 电池信息"), KeyboardButton("📸 拍摄照片")],
    [KeyboardButton("🔄 检查更新"), KeyboardButton("🐚 终端命令")]
]

def check_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

def get_distro_name():
    """尝试获取 Linux 发行版名称"""
    try:
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=")[1].strip().strip('"')
    except:
        pass
    return "Unknown Linux"

def get_size(bytes, suffix="B"):
    """人类可读的文件大小"""
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.1f}{unit}{suffix}"
        bytes /= factor

def check_api_availability():
    """检测 Termux API 是否可用"""
    # 检查命令是否存在
    cmd_name = "termux-battery-status"
    termux_path = "/data/data/com.termux/files/usr/bin/" + cmd_name
    
    is_available = shutil.which(cmd_name) is not None or os.path.exists(termux_path)
    return is_available

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not check_admin(user_id):
        await update.message.reply_text(f"⛔ 拒绝访问。你的 ID: {user_id}")
        return

    distro = get_distro_name()
    env_type = "PRoot/Chroot" if "Android" not in platform.uname().release and os.path.exists("/data/data/com.termux") else "Native Termux"
    
    # API 状态检测
    api_status = "✅ 已就绪" if check_api_availability() else "⚠️ 未检测到 (部分功能不可用)"
    if env_type == "PRoot/Chroot" and "未检测到" in api_status:
        api_status += "\n(Ubuntu 环境下请确保已安装 termux-exec 或使用绝对路径)"

    await update.message.reply_text(
        f"🤖 **Termux 全能管家**\n"
        f"🐧 环境: `{distro}` ({env_type})\n"
        f"📱 API 状态: {api_status}\n"
        f"📂 当前路径: `{os.getcwd()}`\n\n"
        "请选择功能:",
        reply_markup=ReplyKeyboardMarkup(MENU_KEYBOARD, resize_keyboard=True),
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not check_admin(user_id): return

    text = update.message.text
    
    if text == "📊 系统状态":
        await system_status(update, context)
    elif text == "📈 进程列表":
        await top_processes(update, context)
    elif text == "📂 文件管理":
        # 默认列出当前目录
        await list_files(update, context, ".")
    elif text == "🛠 服务探测":
        await check_services(update, context)
    elif text == "🔋 电池信息":
        await get_battery(update, context)
    elif text == "📸 拍摄照片":
        await take_photo(update, context)
    elif text == "🐚 终端命令":
        await update.message.reply_text(
            "💻 **执行命令模式**\n\n"
            "输入: `/exec <命令>`\n"
            "例如: `/exec df -h`",
            parse_mode='Markdown'
        )
    elif text == "🔄 检查更新":
        await update_bot_command(update, context)
    elif text == "❓ 帮助":
        await start(update, context)

async def update_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
    
    msg = await update.message.reply_text("🔄 正在从 GitHub 强制拉取更新...", parse_mode='Markdown')
    
    try:
        # 执行 git 命令：强制重置并拉取
        # 注意：这会丢弃本地对代码的直接修改
        cmd = "git fetch --all && git reset --hard origin/main && git pull && chmod +x start_bot.sh"
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if proc.returncode == 0:
            log_output = proc.stdout[-200:] if len(proc.stdout) > 200 else proc.stdout
            await msg.edit_text(f"✅ **更新成功**\n\n`{log_output}`\n\n🚀 正在重启 Bot...", parse_mode='Markdown')
            
            # 给消息一点发送时间
            time.sleep(1)
            
            # 重启当前脚本
            # os.execl 会用新的进程替换当前进程，如果是在 PM2 下，PM2 会注意到 PID 变化或保持监控
            # 如果是 PM2 管理，其实 os.execl 也是有效的，或者可以让进程退出让 PM2 重启
            # 这里使用 os.execl 比较通用
            os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            await msg.edit_text(f"❌ **更新失败**\n\n错误信息:\n`{proc.stderr}`", parse_mode='Markdown')
            
    except Exception as e:
        await msg.edit_text(f"❌ **发生异常**\n\n`{str(e)}`", parse_mode='Markdown')

async def system_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net = psutil.net_io_counters()
        
        boot_time = psutil.boot_time()
        uptime_s = time.time() - boot_time
        uptime_str = f"{int(uptime_s // 3600)}h {int((uptime_s % 3600) // 60)}m"

        msg = (
            f"📊 **系统状态**\n"
            f"💻 **CPU**: `{cpu_percent}%`\n"
            f"🧠 **RAM**: `{vm.percent}%` ({get_size(vm.used)} / {get_size(vm.total)})\n"
            f"💾 **Disk**: `{disk.percent}%` ({get_size(disk.free)} 可用)\n"
            f"🌐 **Net**: ⬆️`{get_size(net.bytes_sent)}` ⬇️`{get_size(net.bytes_recv)}`\n"
            f"⏱ **运行**: `{uptime_str}`"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ 错误: {str(e)}")

async def top_processes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
    await update.message.reply_text("🔍 正在分析进程...")
    
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                processes.append(proc.info)
            except: pass
        
        top_cpu = sorted(processes, key=lambda p: p['cpu_percent'] or 0, reverse=True)[:5]
        
        msg = "📈 **Top 5 CPU 进程**:\n```\n"
        msg += f"{'PID':<6} {'%CPU':<6} {'NAME'}\n"
        for p in top_cpu:
            msg += f"{p['pid']:<6} {p['cpu_percent']:<6.1f} {p['name'][:15]}\n"
        msg += "```"
        
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ 获取进程失败: {e}")

async def list_files_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
    path = " ".join(context.args) if context.args else "."
    await list_files(update, context, path)

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE, path="."):
    try:
        if not os.path.exists(path):
            await update.message.reply_text("❌ 路径不存在")
            return
            
        abs_path = os.path.abspath(path)
        items = os.listdir(abs_path)
        items.sort(key=lambda x: (not os.path.isdir(os.path.join(abs_path, x)), x.lower()))
        
        msg = f"📂 **目录**: `{abs_path}`\n\n"
        
        # 限制显示数量防止消息过长
        count = 0
        for item in items:
            if count > 20: 
                msg += "\n...(更多文件请指定子目录)"
                break
            full_item_path = os.path.join(abs_path, item)
            is_dir = os.path.isdir(full_item_path)
            icon = "📁" if is_dir else "📄"
            size = "" if is_dir else f" ({get_size(os.path.getsize(full_item_path))})"
            
            # 对特殊字符进行简单转义
            display_name = item.replace("_", "\\_").replace("*", "\\*")
            msg += f"{icon} `{display_name}`{size}\n"
            count += 1
            
        msg += "\n💾 **下载文件**: `/get <文件名>`\n"
        msg += "📂 **进入目录**: `/ls <路径>`"
        
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ 无法列出目录: {e}")

async def download_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
    
    if not context.args:
        await update.message.reply_text("用法: `/get <文件路径>`", parse_mode='Markdown')
        return
        
    path = " ".join(context.args)
    if os.path.exists(path) and os.path.isfile(path):
        status_msg = await update.message.reply_text(f"📤 正在上传 `{path}`...", parse_mode='Markdown')
        try:
            await context.bot.send_document(chat_id=update.effective_chat.id, document=open(path, 'rb'))
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ 发送失败: {e}")
    else:
        await update.message.reply_text("❌ 文件不存在或无法读取。")

async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
    
    doc = update.message.document
    file_name = doc.file_name
    
    # 创建下载目录
    download_dir = "Downloads"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
        
    save_path = os.path.join(download_dir, file_name)
    
    status_msg = await update.message.reply_text(f"⬇️ 正在下载 `{file_name}`...", parse_mode='Markdown')
    
    try:
        new_file = await doc.get_file()
        await new_file.download_to_drive(save_path)
        await status_msg.edit_text(f"✅ 文件已保存至:\n`{os.path.abspath(save_path)}`", parse_mode='Markdown')
    except Exception as e:
        await status_msg.edit_text(f"❌ 下载失败: {e}")

async def check_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
    
    ports = {22: "SSH", 80: "HTTP", 8080: "Web", 3306: "MySQL", 6379: "Redis"}
    results = []
    
    for port, name in ports.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        res = sock.connect_ex(('127.0.0.1', port))
        if res == 0: results.append(f"🟢 **{name}** ({port})")
        sock.close()

    if not results: msg = "🛠 未检测到常用端口开放。"
    else: msg = "🛠 **服务探测**:\n" + "\n".join(results)
    await update.message.reply_text(msg, parse_mode='Markdown')

async def get_battery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    paths = ["termux-battery-status", "/data/data/com.termux/files/usr/bin/termux-battery-status"]
    output = None
    for cmd in paths:
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3)
            if res.returncode == 0 and res.stdout.strip():
                output = res.stdout; break
        except: continue

    if output:
        try:
            data = json.loads(output)
            msg = f"🔋 **电量**: `{data.get('percentage')}%` | 🌡 `{data.get('temperature')}°C` | `{data.get('status')}`"
            await update.message.reply_text(msg, parse_mode='Markdown')
        except:
            await update.message.reply_text(f"🔋: {output}")
    else:
        await update.message.reply_text("⚠️ 无法获取电池信息 (需 Termux:API)")

async def take_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    photo_path = "cam_photo.jpg"
    await update.message.reply_text("📸 正在拍照...")
    
    cmd = "termux-camera-photo -c 0 cam_photo.jpg"
    alt_cmd = "/data/data/com.termux/files/usr/bin/termux-camera-photo -c 0 cam_photo.jpg"
    
    subprocess.run(f"{cmd} || {alt_cmd}", shell=True, timeout=10)
    
    if os.path.exists(photo_path):
        await context.bot.send_photo(chat_id, photo=open(photo_path, 'rb'))
        os.remove(photo_path)
    else:
        await update.message.reply_text("❌ 拍照失败。")

async def exec_shell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
    if not context.args: return await update.message.reply_text("用法: `/exec ls`")

    cmd = " ".join(context.args)
    await update.message.reply_text(f"💻 执行: `{cmd}`", parse_mode='Markdown')
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        out = (res.stdout + res.stderr)[:3000] or "✅ (无输出)"
        await update.message.reply_text(f"```\n{out}\n```", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌: {e}")

async def restart_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
    await update.message.reply_text("🔄 重启中...")
    time.sleep(1)
    os.execl(sys.executable, sys.executable, *sys.argv)

def main():
    print(f"Bot 启动... Admin: {ADMIN_ID}")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("exec", exec_shell))
    app.add_handler(CommandHandler("ls", list_files_command))
    app.add_handler(CommandHandler("get", download_file))
    app.add_handler(CommandHandler("update", update_bot_command))
    
    # 处理文件上传
    app.add_handler(MessageHandler(filters.Document.ALL, receive_file))
    # 处理菜单按钮
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Polling...")
    app.run_polling()

if __name__ == '__main__':
    main()