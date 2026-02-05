import logging
import os
import subprocess
import sys
import platform
import psutil
from telegram import Update
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

def check_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not check_admin(user_id):
        await update.message.reply_text(f"⛔ 拒绝访问。你的 ID: {user_id}")
        return

    await update.message.reply_text(
        "🤖 **Termux 控制终端已就绪**\n\n"
        "可用命令:\n"
        "📊 /status - 查看系统状态 (CPU/内存/磁盘)\n"
        "🔋 /battery - 查看电池状态 (Termux API)\n"
        "📸 /photo - 调用后置摄像头拍照\n"
        "💻 /exec <命令> - 执行 Shell 命令\n"
        "⚠️ 请谨慎执行系统命令。",
        parse_mode='Markdown'
    )

async def system_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return

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

        # 运行时间
        boot_time = psutil.boot_time()
        import time
        uptime_seconds = time.time() - boot_time
        uptime_hours = uptime_seconds // 3600

        msg = (
            f"📊 **系统状态报告**\n\n"
            f"**CPU**: {cpu_percent}% ({freq_info})\n"
            f"**内存**: {ram_used} / {ram_total} ({ram_percent}%)\n"
            f"**磁盘**: {disk_used} / {disk_total} ({disk_percent}%)\n"
            f"**运行时间**: {int(uptime_hours)} 小时\n"
            f"**系统**: {platform.system()} {platform.release()}"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ 获取状态失败: {str(e)}")

async def get_battery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
    
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
        await update.message.reply_text(f"🔋 **电池状态**:\n`{output}`", parse_mode='Markdown')
    else:
        await update.message.reply_text(
            "⚠️ 无法读取电池信息。\n"
            "如果你在 Ubuntu/PRoot 环境中运行，请确保 Termux 原生环境已安装 Termux:API，"
            "并且你有权限访问该命令。"
        )

async def take_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
    
    chat_id = update.effective_chat.id
    photo_path = "cam_photo.jpg"
    
    await update.message.reply_text("📸 正在调用摄像头...")
    
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
        await update.message.reply_text(f"❌ 调用出错: {e}")
        return

    if success:
        await context.bot.send_photo(chat_id=chat_id, photo=open(photo_path, 'rb'))
        os.remove(photo_path)
    else:
        await update.message.reply_text("❌ 拍照失败。请确保已安装 Termux:API 并授予了相机权限。")

async def exec_shell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return

    if not context.args:
        await update.message.reply_text("请提供要执行的命令。例如: `/exec ls -la`", parse_mode='Markdown')
        return

    command = " ".join(context.args)
    await update.message.reply_text(f"💻 执行: `{command}`", parse_mode='Markdown')

    try:
        # 限制输出长度，防止消息过长发送失败
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

def main():
    print(f"Bot 正在启动... (Admin ID: {ADMIN_ID})")
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("status", system_status))
    application.add_handler(CommandHandler("battery", get_battery))
    application.add_handler(CommandHandler("photo", take_photo))
    application.add_handler(CommandHandler("exec", exec_shell))

    print("Bot 已开始轮询...")
    application.run_polling()

if __name__ == '__main__':
    main()
