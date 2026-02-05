import logging
import os
import subprocess
import sys
import platform
import psutil
import json
import time
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
    [KeyboardButton("📊 系统状态"), KeyboardButton("🔋 电池信息")],
    [KeyboardButton("📸 拍摄照片"), KeyboardButton("🐚 终端命令")],
    [KeyboardButton("🔄 重启机器人"), KeyboardButton("❓ 帮助")]
]

def check_admin(user_id):
    is_admin = str(user_id) == str(ADMIN_ID)
    if not is_admin:
        logger.warning(f"非管理员尝试访问: {user_id}")
    return is_admin

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not check_admin(user_id):
        await update.message.reply_text(f"⛔ 拒绝访问。你的 ID: {user_id}")
        return

    await update.message.reply_text(
        "🤖 **Termux 控制终端已就绪**\n"
        "请使用下方菜单或输入命令操作。",
        reply_markup=ReplyKeyboardMarkup(MENU_KEYBOARD, resize_keyboard=True),
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not check_admin(user_id): return

    text = update.message.text
    
    if text == "📊 系统状态":
        await system_status(update, context)
    elif text == "🔋 电池信息":
        await get_battery(update, context)
    elif text == "📸 拍摄照片":
        await take_photo(update, context)
    elif text == "🐚 终端命令":
        await update.message.reply_text(
            "💻 **执行命令模式**\n\n"
            "由于安全原因，请手动输入命令，格式如下：\n"
            "`/exec ls -la`\n"
            "`/exec pm2 list`",
            parse_mode='Markdown'
        )
    elif text == "🔄 重启机器人":
        await restart_bot(update, context)
    elif text == "❓ 帮助":
        await start(update, context)
    else:
        # 如果不是菜单命令，且不是以/开头（已由CommandHandler处理），则忽略或提示
        pass

async def system_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_freq = psutil.cpu_freq()
        freq_info = f"{cpu_freq.current:.0f}MHz" if cpu_freq else "N/A"

        # 内存
        vm = psutil.virtual_memory()
        ram_used = f"{vm.used / 1024 / 1024 / 1024:.2f} GB"
        ram_total = f"{vm.total / 1024 / 1024 / 1024:.2f} GB"
        ram_percent = vm.percent

        # 磁盘
        disk = psutil.disk_usage('/')
        disk_used = f"{disk.used / 1024 / 1024 / 1024:.2f} GB"
        disk_total = f"{disk.total / 1024 / 1024 / 1024:.2f} GB"
        disk_percent = disk.percent

        # 网络
        net = psutil.net_io_counters()
        sent = f"{net.bytes_sent / 1024 / 1024:.1f} MB"
        recv = f"{net.bytes_recv / 1024 / 1024:.1f} MB"

        # 运行时间
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        uptime_hours = uptime_seconds // 3600
        uptime_days = uptime_hours // 24
        uptime_str = f"{int(uptime_days)}天 {int(uptime_hours % 24)}小时" if uptime_days > 0 else f"{int(uptime_hours)}小时"

        msg = (
            f"📊 **系统状态报告**\n\n"
            f"**系统**: `{platform.system()} {platform.release()}`\n"
            f"**在线**: {uptime_str}\n"
            f"**CPU**: `{cpu_percent}%` ({freq_info})\n"
            f"**内存**: `{ram_used} / {ram_total}` ({ram_percent}%)\n"
            f"**磁盘**: `{disk_used} / {disk_total}` ({disk_percent}%)\n"
            f"**网络**: ⬆️ `{sent}` | ⬇️ `{recv}`"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ 获取状态失败: {str(e)}")

async def get_battery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 尝试不同的 termux-battery-status 调用方式
    commands = [
        "termux-battery-status", 
        "/data/data/com.termux/files/usr/bin/termux-battery-status"
    ]
    
    output = None
    for cmd in commands:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                output = result.stdout
                break
        except:
            continue

    if output:
        try:
            # 尝试解析 JSON 使得显示更友好
            data = json.loads(output)
            percentage = data.get('percentage', '?')
            status = data.get('status', 'Unknown')
            health = data.get('health', 'Unknown')
            temperature = data.get('temperature', 0)
            plugged = data.get('plugged', 'No')
            
            msg = (
                f"🔋 **电池详情**\n\n"
                f"**电量**: `{percentage}%`\n"
                f"**状态**: `{status}` ({plugged})\n"
                f"**健康**: `{health}`\n"
                f"**温度**: `{temperature}°C`"
            )
            await update.message.reply_text(msg, parse_mode='Markdown')
        except json.JSONDecodeError:
            # 如果不是JSON，直接显示原始内容
            await update.message.reply_text(f"🔋 **电池状态**:\n`{output}`", parse_mode='Markdown')
    else:
        await update.message.reply_text(
            "⚠️ 无法读取电池信息。\n"
            "请确认 Termux:API 已安装，或在原生 Termux 环境下运行。"
        )

async def take_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    photo_path = "cam_photo.jpg"
    
    status_msg = await update.message.reply_text("📸 正在调用摄像头...")
    
    # 尝试调用 termux-camera-photo
    cmd = "termux-camera-photo -c 0 cam_photo.jpg"
    alt_cmd = "/data/data/com.termux/files/usr/bin/termux-camera-photo -c 0 cam_photo.jpg"
    
    success = False
    try:
        # 尝试直接调用
        res = subprocess.run(cmd, shell=True, timeout=10)
        if res.returncode == 0 and os.path.exists(photo_path):
            success = True
        else:
            # 尝试绝对路径
            res = subprocess.run(alt_cmd, shell=True, timeout=10)
            if res.returncode == 0 and os.path.exists(photo_path):
                success = True
    except Exception as e:
        await status_msg.edit_text(f"❌ 调用出错: {e}")
        return

    if success:
        await context.bot.send_photo(chat_id=chat_id, photo=open(photo_path, 'rb'))
        await status_msg.delete()
        os.remove(photo_path)
    else:
        await status_msg.edit_text("❌ 拍照失败。请确保已安装 Termux:API 并授予了相机权限。")

async def exec_shell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return

    if not context.args:
        await update.message.reply_text("请提供要执行的命令。例如: `/exec ls -la`", parse_mode='Markdown')
        return

    command = " ".join(context.args)
    await update.message.reply_text(f"💻 执行: `{command}`", parse_mode='Markdown')

    try:
        # 限制输出长度
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        output = result.stdout
        error = result.stderr
        
        response_msg = ""
        if output:
            response_msg += f"📥 **Output**:\n```\n{output[:3000]}\n```"
            if len(output) > 3000: response_msg += "\n*(输出被截断)*"
        
        if error:
            response_msg += f"\n❌ **Error**:\n```\n{error[:1000]}\n```"

        if not response_msg:
            response_msg = "✅ 命令执行完成，无输出。"
            
        await update.message.reply_text(response_msg, parse_mode='Markdown')

    except subprocess.TimeoutExpired:
        await update.message.reply_text("❌ 命令执行超时 (30s)。")
    except Exception as e:
        await update.message.reply_text(f"❌ 执行错误: {str(e)}")

async def restart_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
    await update.message.reply_text("🔄 正在重启机器人...\n(如果由 PM2 管理，进程将自动拉起)")
    
    # 给予一点时间发送消息
    time.sleep(1)
    
    # 方法1: 如果是 PM2 管理，直接退出，PM2 会重启它
    # 方法2: 尝试使用 os.exec 重新执行当前脚本
    
    # 这里我们使用 os.execv 重新加载，这样即使没有 PM2 也能重启
    os.execl(sys.executable, sys.executable, *sys.argv)

def main():
    print(f"Bot 正在启动... (Admin ID: {ADMIN_ID})")
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # 命令处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("status", system_status))
    application.add_handler(CommandHandler("battery", get_battery))
    application.add_handler(CommandHandler("photo", take_photo))
    application.add_handler(CommandHandler("exec", exec_shell))

    # 文本消息处理器 (用于处理菜单按钮点击)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot 已开始轮询...")
    application.run_polling()

if __name__ == '__main__':
    main()