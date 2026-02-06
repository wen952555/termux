from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram.request import HTTPXRequest

# Import Modules
from bot_modules.config import BOT_TOKEN, logger, PROXY_URL, ADMIN_ID
from bot_modules.utils import check_admin, error_handler
from bot_modules.system import system_status, show_processes, handle_process_callback, force_update
from bot_modules.media import capture_media, cleanup_media, play_received_audio
from bot_modules.tools import show_torch_menu, handle_torch_callback, check_ip, exec_command

# --- MENU LAYOUT ---
MENU_KEYBOARD = [
    [KeyboardButton("📊 系统状态"), KeyboardButton("🗑 清理媒体")],
    [KeyboardButton("📸 拍摄照片"), KeyboardButton("🔦 手电筒")],
    [KeyboardButton("📹 录制视频"), KeyboardButton("🎤 录制音频")],
    [KeyboardButton("🌐 公网 IP"), KeyboardButton("🔄 强制更新")]
]

# --- MAIN DISPATCHER ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not check_admin(user_id):
        logger.warning(f"Unauthorized start attempt from {user_id}")
        await update.message.reply_text(
            f"⛔️ **未授权访问**\n\n"
            f"您的 Telegram ID: `{user_id}`\n"
            f"配置的 Admin ID: `{ADMIN_ID}`\n\n"
            f"请修改 `bot_modules/config.py` 文件中的 ADMIN_ID，或检查您的账号。",
            parse_mode='Markdown'
        )
        return

    await update.message.reply_text(
        "🤖 **Termux 智能控制台**\n模块加载完成。\n\n**提示:** 🗣 直接发送语音消息或音频文件，Bot 将在手机上播放！",
        reply_markup=ReplyKeyboardMarkup(MENU_KEYBOARD, resize_keyboard=True),
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not check_admin(user_id):
        await update.message.reply_text(f"⛔️ 未授权 (您的 ID: {user_id})")
        return

    text = update.message.text
    
    # Routing
    if text == "📊 系统状态": await system_status(update, context)
    elif text == "🗑 清理媒体": await cleanup_media(update, context)
    elif text == "🔄 强制更新": await force_update(update, context)
    elif text == "📸 拍摄照片": await capture_media(update, context, "photo")
    elif text == "📹 录制视频": await capture_media(update, context, "video")
    elif text == "🎤 录制音频": await capture_media(update, context, "audio")
    elif text == "🔦 手电筒": await show_torch_menu(update, context)
    elif text == "🌐 公网 IP": await check_ip(update, context)
    elif text == "💻 终端命令":
        await update.message.reply_text("使用 `/exec <命令>` 执行任意 Shell 指令。\n例如: `/exec ls -lh`")
    elif text == "💀 进程管理": await show_processes(update, context) # Hidden command

def main():
    # 1. 配置网络请求 (代理支持)
    request = None
    if PROXY_URL:
        print(f"🌐 检测到代理配置: {PROXY_URL}")
        request = HTTPXRequest(proxy_url=PROXY_URL)
    else:
        print("ℹ️ 未检测到代理环境变量 (http_proxy)。如果连接失败，请配置代理。")

    # 2. 构建应用
    builder = ApplicationBuilder().token(BOT_TOKEN)
    if request:
        builder.request(request)
    
    app = builder.build()
    
    # Command Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("exec", exec_command))
    app.add_handler(CommandHandler("update", force_update))
    
    # Message Handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, play_received_audio))
    
    # Callback Handlers
    app.add_handler(CallbackQueryHandler(handle_process_callback, pattern="^(kill:|refresh_ps)"))
    app.add_handler(CallbackQueryHandler(handle_torch_callback, pattern="^torch:"))

    # Error Handler
    app.add_error_handler(error_handler)

    print(f"✅ Bot 启动成功！正在等待消息...")
    if PROXY_URL:
        print(f"📡 代理模式运行中 -> {PROXY_URL}")
        
    app.run_polling()

if __name__ == '__main__':
    main()