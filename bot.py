from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler

# Import Modules
from bot_modules.config import BOT_TOKEN, logger
from bot_modules.utils import check_admin, error_handler
from bot_modules.system import system_status, show_processes, handle_process_callback, force_update
from bot_modules.media import capture_media, cleanup_media
from bot_modules.tools import show_torch_menu, handle_torch_callback, check_ip, exec_command

# --- MENU LAYOUT ---
# 布局调整：移除文件管理，添加清理和强制更新
MENU_KEYBOARD = [
    [KeyboardButton("📊 系统状态"), KeyboardButton("🗑 清理媒体")],
    [KeyboardButton("📸 拍摄照片"), KeyboardButton("🔦 手电筒")],
    [KeyboardButton("📹 录制视频"), KeyboardButton("🎤 录制音频")],
    [KeyboardButton("🌐 公网 IP"), KeyboardButton("🔄 强制更新")]
]

# --- MAIN DISPATCHER ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
    await update.message.reply_text(
        "🤖 **Termux 智能控制台**\n模块加载完成，请选择操作：",
        reply_markup=ReplyKeyboardMarkup(MENU_KEYBOARD, resize_keyboard=True),
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return
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
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Command Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("exec", exec_command))
    app.add_handler(CommandHandler("update", force_update))
    
    # Message Handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Callback Handlers (Router)
    app.add_handler(CallbackQueryHandler(handle_process_callback, pattern="^(kill:|refresh_ps)"))
    app.add_handler(CallbackQueryHandler(handle_torch_callback, pattern="^torch:"))

    # Error Handler
    app.add_error_handler(error_handler)

    print(f"Bot started. Monitoring...")
    app.run_polling()

if __name__ == '__main__':
    main()
