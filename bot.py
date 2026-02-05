import logging
import os
import subprocess
import sys
import platform
import psutil
import json
import time
import socket
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
    [KeyboardButton("🔋 电池信息"), KeyboardButton("🛠 服务探测")],
    [KeyboardButton("📸 拍摄照片"), KeyboardButton("🐚 终端命令")],
    [KeyboardButton("🔄 重启机器人"), KeyboardButton("❓ 帮助")]
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not check_admin(user_id):
        await update.message.reply_text(f"⛔ 拒绝访问。你的 ID: {user_id}")
        return

    distro = get_distro_name()
    env_type = "PRoot/Chroot" if "Android" not in platform.uname().release and os.path.exists("/data/data/com.termux") else "Native Termux"

    await update.message.reply_text(
        f"🤖 **Termux 监控终端**\n"
        f"环境: `{distro}` ({env_type})\n"
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
    elif text == "🔋 电池信息":
        await get_battery(update, context)
    elif text == "🛠 服务探测":
        await check_services(update, context)
    elif text == "📸 拍摄照片":
        await take_photo(update, context)
    elif text == "🐚 终端命令":
        await update.message.reply_text(
            "💻 **执行命令模式**\n\n"
            "输入: `/exec <命令>`\n"
            "例如: `/exec df -h`",
            parse_mode='Markdown'
        )
    elif text == "🔄 重启机器人":
        await restart_bot(update, context)
    elif text == "❓ 帮助":
        await start(update, context)

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
            f"🧠 **RAM**: `{vm.percent}%` ({vm.used >> 20}MB / {vm.total >> 20}MB)\n"
            f"💾 **Disk**: `{disk.percent}%` ({disk.free >> 30}GB 可用)\n"
            f"🌐 **Net**: ⬆️`{net.bytes_sent >> 20}MB` ⬇️`{net.bytes_recv >> 20}MB`\n"
            f"⏱ **运行**: `{uptime_str}`"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ 错误: {str(e)}")

async def top_processes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示资源占用前5的进程"""
    if not check_admin(update.effective_user.id): return
    await update.message.reply_text("🔍 正在分析进程...")
    
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # 按 CPU 排序
        top_cpu = sorted(processes, key=lambda p: p['cpu_percent'] or 0, reverse=True)[:5]
        
        msg = "📈 **Top 5 CPU 进程**:\n```\n"
        msg += f"{'PID':<6} {'%CPU':<6} {'NAME'}\n"
        for p in top_cpu:
            msg += f"{p['pid']:<6} {p['cpu_percent']:<6.1f} {p['name'][:15]}\n"
        msg += "```"
        
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ 获取进程失败: {e}")

async def check_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """检测常见端口和服务"""
    if not check_admin(update.effective_user.id): return
    
    # 常用端口定义
    ports = {
        22: "SSH",
        80: "HTTP",
        443: "HTTPS",
        8080: "Web Alt",
        3306: "MySQL",
        5432: "PostgreSQL",
        6379: "Redis",
        27017: "MongoDB"
    }
    
    results = []
    
    # 检查端口
    for port, name in ports.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex(('127.0.0.1', port))
        status = "🟢 运行中" if result == 0 else "🔴 未运行"
        if result == 0: # 只显示运行中的服务以减少刷屏
            results.append(f"**{name}** ({port}): {status}")
        sock.close()

    # 检查特定进程 (针对 Termux/PRoot 环境)
    target_procs = ['sshd', 'nginx', 'apache2', 'httpd', 'mysqld', 'tor']
    running_procs = set()
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] in target_procs:
                running_procs.add(proc.info['name'])
        except: pass
    
    for p in running_procs:
        results.append(f"⚙️ **进程**: `{p}` 正在运行")

    if not results:
        msg = "🛠 **服务探测**: 未检测到常用端口或服务运行。"
    else:
        msg = "🛠 **服务探测结果**:\n" + "\n".join(results)
        
    await update.message.reply_text(msg, parse_mode='Markdown')

async def get_battery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Termux API 路径尝试列表
    paths = [
        "termux-battery-status",
        "/data/data/com.termux/files/usr/bin/termux-battery-status"
    ]
    
    output = None
    for cmd in paths:
        try:
            # PRoot 可能会屏蔽 /data 的直接访问，或者 path 没设置好
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3)
            if res.returncode == 0 and res.stdout.strip():
                output = res.stdout
                break
        except: continue

    if output:
        try:
            data = json.loads(output)
            msg = (
                f"🔋 **电池状态**\n"
                f"⚡ **电量**: `{data.get('percentage', '?')}%`\n"
                f"🌡 **温度**: `{data.get('temperature', '?')}°C`\n"
                f"🩺 **健康**: `{data.get('health', 'Unknown')}`\n"
                f"🔌 **状态**: `{data.get('status', 'Unknown')}`"
            )
            await update.message.reply_text(msg, parse_mode='Markdown')
        except:
            await update.message.reply_text(f"🔋 原始数据: `{output}`", parse_mode='Markdown')
    else:
        await update.message.reply_text(
            "⚠️ **无法获取电池信息**\n"
            "1. 确保 Termux 中已安装 `termux-api` 包。\n"
            "2. 确保已安装 Termux:API 安卓应用。\n"
            "3. 如果在 Ubuntu 中运行，尝试安装 `termux-exec` 或直接调用绝对路径。"
        )

async def take_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    photo_path = "cam_photo.jpg"
    await update.message.reply_text("📸 正在拍照 (后置)...")
    
    cmd = "/data/data/com.termux/files/usr/bin/termux-camera-photo -c 0 cam_photo.jpg"
    try:
        subprocess.run(f"{cmd} || termux-camera-photo -c 0 {photo_path}", shell=True, timeout=10)
        if os.path.exists(photo_path):
            await context.bot.send_photo(chat_id, photo=open(photo_path, 'rb'))
            os.remove(photo_path)
        else:
            await update.message.reply_text("❌ 拍照失败，文件未生成。请检查相机权限。")
    except Exception as e:
        await update.message.reply_text(f"❌ 错误: {e}")

async def exec_shell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("用法: `/exec ls -la`", parse_mode='Markdown')
        return

    cmd = " ".join(context.args)
    await update.message.reply_text(f"💻 执行: `{cmd}`", parse_mode='Markdown')
    
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        out = (res.stdout + res.stderr)[:3000]
        if not out: out = "✅ (无输出)"
        await update.message.reply_text(f"```\n{out}\n```", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ 异常: {e}")

async def restart_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
    await update.message.reply_text("🔄 重启中...")
    time.sleep(1)
    os.execl(sys.executable, sys.executable, *sys.argv)

def main():
    print(f"Bot 启动中... Admin: {ADMIN_ID}")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("exec", exec_shell))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Polling...")
    app.run_polling()

if __name__ == '__main__':
    main()