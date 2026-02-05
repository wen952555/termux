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
MEDIA_DIR = os.path.abspath("captured_media")  # 使用绝对路径更安全
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
    [KeyboardButton("🎤 录制音频"), KeyboardButton("🗑 清理媒体")],
    [KeyboardButton("🔦 开启手电"), KeyboardButton("🌑 关闭手电")],
    [KeyboardButton("🔋 电池信息"), KeyboardButton("🛠 服务探测")],
    [KeyboardButton("💻 终端命令"), KeyboardButton("🔄 检查更新")]
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

# --- Bot 启动后钩子 ---
async def post_init(application: ApplicationBuilder):
    """Bot 启动完成后执行"""
    try:
        # 启动时通知管理员
        distro = get_distro_name()
        await application.bot.send_message(
            chat_id=ADMIN_ID, 
            text=f"🤖 **Bot 已成功上线**\n🌍 环境: {distro}\n📂 目录: {MEDIA_DIR}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Failed to send startup message: {e}")

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
    elif text == "🎤 录制音频":
        await capture_media(update, context, "audio")
    elif text == "🔦 开启手电":
        await toggle_torch(update, context, True)
    elif text == "🌑 关闭手电":
        await toggle_torch(update, context, False)
    elif text == "🗑 清理媒体":
        await clean_media_files(update, context)
        
    # 管理类
    elif text == "💻 终端命令":
        msg = (
            "💻 **终端命令执行指南**\n\n"
            "请使用 `/exec` 命令来运行 Shell 指令。\n\n"
            "**常用示例:**\n"
            "• `/exec ls -lh` (查看当前目录文件)\n"
            "• `/exec ip a` (查看 IP 地址)\n"
            "• `/exec pm2 list` (查看后台任务)\n"
            "• `/exec whoami` (查看当前用户)"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')
    elif text == "🔄 检查更新":
        await update_bot_command(update, context)
    elif text == "❓ 帮助":
        await start(update, context)

# --- 核心功能函数 ---

async def toggle_torch(update: Update, context: ContextTypes.DEFAULT_TYPE, state: bool):
    """控制手电筒开关"""
    cmd_base = "termux-torch"
    full_path = "/data/data/com.termux/files/usr/bin/termux-torch"
    arg = "on" if state else "off"
    
    msg = await update.message.reply_text(f"⚡ 正在{'开启' if state else '关闭'}手电筒...")
    
    try:
        # 同时尝试直接命令和绝对路径
        cmd = f"{cmd_base} {arg} || {full_path} {arg}"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        
        if res.returncode == 0:
            await msg.edit_text(f"✅ 手电筒已{'开启' if state else '关闭'}")
        else:
            err_info = res.stderr.strip() or "未知错误"
            await msg.edit_text(f"❌ 操作失败: {err_info}\n请确认已安装 Termux:API 并授予相机权限。")
    except Exception as e:
        await msg.edit_text(f"❌ 执行错误: {e}")

async def capture_media(update: Update, context: ContextTypes.DEFAULT_TYPE, media_type="photo"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    chat_id = update.effective_chat.id
    
    # 确保目录存在
    if not os.path.exists(MEDIA_DIR):
        os.makedirs(MEDIA_DIR)
    
    # 根据类型配置命令
    if media_type == "photo":
        filename = os.path.join(MEDIA_DIR, f"photo_{timestamp}.jpg")
        cmd_base = "termux-camera-photo -c 0"
        path_base = "/data/data/com.termux/files/usr/bin/termux-camera-photo -c 0"
        cmd = f"{cmd_base} {filename}"
        alt_cmd = f"{path_base} {filename}"
        msg_text = "📸 正在拍摄..."
        timeout_val = 10
        
    elif media_type == "video":
        filename = os.path.join(MEDIA_DIR, f"video_{timestamp}.mp4")
        duration = 5
        cmd_base = f"termux-camera-record -c 0 -l {duration}"
        path_base = f"/data/data/com.termux/files/usr/bin/termux-camera-record -c 0 -l {duration}"
        cmd = f"{cmd_base} {filename}"
        alt_cmd = f"{path_base} {filename}"
        msg_text = f"📹 正在录制 ({duration}s)..."
        timeout_val = 15

    elif media_type == "audio":
        filename = os.path.join(MEDIA_DIR, f"audio_{timestamp}.m4a")
        duration = 10
        # termux-microphone-record -l <seconds> -f <file>
        cmd_base = f"termux-microphone-record -l {duration} -e aac"
        path_base = f"/data/data/com.termux/files/usr/bin/termux-microphone-record -l {duration} -e aac"
        cmd = f"{cmd_base} -f {filename}"
        alt_cmd = f"{path_base} -f {filename}"
        msg_text = f"🎤 正在录音 ({duration}s)..."
        timeout_val = 20
        
    status_msg = await update.message.reply_text(msg_text)
    
    # 执行命令
    try:
        result = subprocess.run(f"{cmd} || {alt_cmd}", shell=True, timeout=timeout_val, capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        # 视频/音频录制有时会超时但实际上已经开始或完成（尤其是后台运行时）
        pass 
    except Exception as e:
        await status_msg.edit_text(f"❌ 命令执行异常: {e}")
        return

    # 检查文件并发送
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        try:
            await status_msg.edit_text(f"📤 正在上传...")
            with open(filename, 'rb') as f:
                if media_type == "photo":
                    await context.bot.send_photo(chat_id, photo=f, caption=f"📅 {timestamp}")
                elif media_type == "video":
                    await context.bot.send_video(chat_id, video=f, caption=f"📅 {timestamp}")
                elif media_type == "audio":
                    await context.bot.send_audio(chat_id, audio=f, caption=f"📅 {timestamp}", title=f"Audio {timestamp}")
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ 发送失败: {e}")
    else:
        # 详细的错误诊断
        error_detail = ""
        if 'result' in locals() and result.stderr:
            error_detail = f"\n错误信息: `{result.stderr.strip()}`"
        
        perm_hint = "麦克风" if media_type == "audio" else "相机"
        hint = f"\n\n💡 提示: \n1. 确保 Termux:API 已安装\n2. 确保已授予 Termux '{perm_hint}' 权限\n3. 如果录音失败，尝试在 Termux 中手动运行 `termux-microphone-record -h` 检查是否支持"
        
        await status_msg.edit_text(f"❌ 未能生成文件{error_detail}{hint}")

async def clean_media_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
    
    files = glob.glob(os.path.join(MEDIA_DIR, "*"))
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
    # 常用服务端口定义
    ports = {
        22: "SSH (远程连接)", 
        80: "HTTP (网页服务)", 
        8080: "Web Proxy", 
        3306: "MySQL (数据库)", 
        6379: "Redis (缓存)", 
        5173: "Monitor Web (监控台)"
    }
    
    results = []
    for port, name in ports.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        # connect_ex 返回 0 表示连接成功（端口开放）
        res = sock.connect_ex(('127.0.0.1', port))
        if res == 0: 
            results.append(f"🟢 **{name}** `:{port}` 运行中")
        else:
            # 也可以选择显示未运行的服务，这里为了简洁只显示运行中的
            pass
        sock.close()

    if results:
        msg = "🛠 **本地服务探测结果**:\n(检测常用端口是否开启)\n\n" + "\n".join(results)
    else:
        msg = "🛠 **本地服务探测结果**:\n\n⚠️ 未检测到常见服务 (SSH, MySQL, Web等)。\n这表示这些服务的端口没有在本地开启。"
        
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
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

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