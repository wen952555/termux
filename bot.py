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
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# --- 配置区域 ---
BOT_TOKEN = "8091415322:AAFuS0PJKnu8hi0WHwXoSqHuJTZJNRFzzS4"
ADMIN_ID = 1878794912
MEDIA_DIR = "captured_media"  # 媒体文件保存目录
# ----------------

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 键盘菜单布局 (重组后)
MENU_KEYBOARD = [
    [KeyboardButton("📊 系统状态"), KeyboardButton("📈 进程列表")],
    [KeyboardButton("📸 拍摄照片"), KeyboardButton("📹 录制视频")],
    [KeyboardButton("🗑 清理媒体"), KeyboardButton("🛠 服务探测")],
    [KeyboardButton("🔋 电池信息"), KeyboardButton("🔄 检查更新")]
]

# 确保媒体目录存在
if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

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
    
    api_status = "✅ 已就绪" if check_api_availability() else "⚠️ 未检测到 (媒体功能可能不可用)"

    await update.message.reply_text(
        f"🤖 **Termux 监控卫士**\n"
        f"🐧 环境: `{distro}` ({env_type})\n"
        f"📱 API 状态: {api_status}\n"
        f"💾 媒体目录: `{MEDIA_DIR}/`\n\n"
        "请选择操作:",
        reply_markup=ReplyKeyboardMarkup(MENU_KEYBOARD, resize_keyboard=True),
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not check_admin(user_id): return

    text = update.message.text
    
    # 系统类
    if text == "📊 系统状态":
        await system_status(update, context)
    elif text == "📈 进程列表":
        await top_processes(update, context)
    elif text == "🛠 服务探测":
        await check_services(update, context)
    elif text == "🔋 电池信息":
        await get_battery(update, context)
        
    # 媒体类
    elif text == "📸 拍摄照片":
        await capture_media(update, context, "photo")
    elif text == "📹 录制视频":
        await capture_media(update, context, "video")
    elif text == "🗑 清理媒体":
        await clean_media_files(update, context)
        
    # 管理类
    elif text == "🔄 检查更新":
        await update_bot_command(update, context)
    elif text == "❓ 帮助":
        await start(update, context)

# --- 核心功能函数 ---

async def capture_media(update: Update, context: ContextTypes.DEFAULT_TYPE, media_type="photo"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    chat_id = update.effective_chat.id
    
    if media_type == "photo":
        filename = f"{MEDIA_DIR}/photo_{timestamp}.jpg"
        # 尝试两个路径，优先使用 path 变量中的，失败则尝试绝对路径
        cmd = f"termux-camera-photo -c 0 {filename}"
        alt_cmd = f"/data/data/com.termux/files/usr/bin/termux-camera-photo -c 0 {filename}"
        msg_text = "📸 正在拍摄..."
    else:
        filename = f"{MEDIA_DIR}/video_{timestamp}.mp4"
        duration = 5 # 视频时长秒
        cmd = f"termux-camera-record -c 0 -l {duration} {filename}"
        alt_cmd = f"/data/data/com.termux/files/usr/bin/termux-camera-record -c 0 -l {duration} {filename}"
        msg_text = f"📹 正在录制 ({duration}s)..."

    status_msg = await update.message.reply_text(msg_text)
    
    # 执行命令
    try:
        # 使用 timeout 防止卡死，视频录制需要稍微多一点时间
        timeout_val = 15 if media_type == "video" else 10
        subprocess.run(f"{cmd} || {alt_cmd}", shell=True, timeout=timeout_val, capture_output=True)
    except subprocess.TimeoutExpired:
        pass # 有时候录制会超时但文件已生成
    except Exception as e:
        await status_msg.edit_text(f"❌ 命令执行出错: {e}")
        return

    # 检查文件并发送
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        try:
            await status_msg.edit_text(f"📤 正在上传...")
            with open(filename, 'rb') as f:
                if media_type == "photo":
                    await context.bot.send_photo(chat_id, photo=f, caption=f"📅 {timestamp}")
                else:
                    await context.bot.send_video(chat_id, video=f, caption=f"📅 {timestamp}")
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ 发送失败: {e}")
    else:
        await status_msg.edit_text(f"❌ 获取失败 (请检查 Termux:API 权限)\n未能生成文件: {filename}")

async def clean_media_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
    
    files = glob.glob(f"{MEDIA_DIR}/*")
    count = len(files)
    
    if count == 0:
        await update.message.reply_text("🗑 目录为空，无需清理。")
        return

    try:
        for f in files:
            os.remove(f)
        await update.message.reply_text(f"✅ 已删除 {count} 个媒体文件。")
    except Exception as e:
        await update.message.reply_text(f"❌ 清理部分失败: {e}")

async def update_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🔄 正在从 GitHub 强制拉取更新...", parse_mode='Markdown')
    try:
        cmd = "git fetch --all && git reset --hard origin/main && git pull && chmod +x start_bot.sh"
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if proc.returncode == 0:
            log_output = proc.stdout[-200:] if len(proc.stdout) > 200 else proc.stdout
            await msg.edit_text(f"✅ **更新成功**\n\n`{log_output}`\n\n🚀 正在重启 Bot...", parse_mode='Markdown')
            time.sleep(1)
            os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            await msg.edit_text(f"❌ **更新失败**\n\n`{proc.stderr}`", parse_mode='Markdown')
    except Exception as e:
        await msg.edit_text(f"❌ **异常**: `{str(e)}`", parse_mode='Markdown')

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
    await update.message.reply_text("🔍 正在分析进程...")
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                processes.append(proc.info)
            except: pass
        
        top_cpu = sorted(processes, key=lambda p: p['cpu_percent'] or 0, reverse=True)[:5]
        msg = "📈 **Top 5 CPU 进程**:\n```\nPID    %CPU   NAME\n"
        for p in top_cpu:
            msg += f"{p['pid']:<6} {p['cpu_percent']:<6.1f} {p['name'][:15]}\n"
        msg += "```"
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ 失败: {e}")

async def check_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ports = {22: "SSH", 80: "HTTP", 8080: "Web", 3306: "MySQL", 6379: "Redis", 5173: "Vite Dev"}
    results = []
    for port, name in ports.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        res = sock.connect_ex(('127.0.0.1', port))
        if res == 0: results.append(f"🟢 **{name}** ({port})")
        sock.close()

    msg = "🛠 **服务探测**:\n" + ("\n".join(results) if results else "未检测到常用端口。")
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

async def exec_shell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
    if not context.args: return await update.message.reply_text("用法: `/exec ls -la`")
    cmd = " ".join(context.args)
    await update.message.reply_text(f"💻 执行: `{cmd}`", parse_mode='Markdown')
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        out = (res.stdout + res.stderr)[:3000] or "✅ (无输出)"
        await update.message.reply_text(f"```\n{out}\n```", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌: {e}")

def main():
    print(f"Bot 启动... Admin: {ADMIN_ID}")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # 命令处理器
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("exec", exec_shell))
    app.add_handler(CommandHandler("update", update_bot_command))
    
    # 消息处理器 (菜单按钮)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Polling...")
    app.run_polling()

if __name__ == '__main__':
    main()