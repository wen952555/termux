import asyncio
import sys
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram.request import HTTPXRequest
from telegram.error import NetworkError, InvalidToken

# Import Modules
from bot_modules.config import BOT_TOKEN, logger, PROXY_URL, ADMIN_ID
from bot_modules.utils import check_admin, error_handler
from bot_modules.system import system_status, show_processes, handle_process_callback, force_update
from bot_modules.media import (
    capture_media, cleanup_media, play_received_audio, stop_playback_callback,
    list_audio_files, handle_audio_selection, handle_loop_callback
)
from bot_modules.tools import toggle_torch, check_ip, exec_command

# --- MENU LAYOUT ---
MENU_KEYBOARD = [
    [KeyboardButton("📊 系统状态"), KeyboardButton("🎵 播放列表")],
    [KeyboardButton("📸 拍摄照片"), KeyboardButton("🔦 手电筒")],
    [KeyboardButton("💥 连拍模式"), KeyboardButton("🎤 录制音频")],
    [KeyboardButton("🌐 公网 IP"), KeyboardButton("🗑 清理媒体")]
]

# --- MAIN DISPATCHER ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"收到 /start 指令，来自用户: {user_id}")
    
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
        return

    text = update.message.text
    logger.info(f"收到指令: {text}")
    
    # Routing
    if text == "📊 系统状态": await system_status(update, context)
    elif text == "🗑 清理媒体": await cleanup_media(update, context)
    elif text == "🔄 强制更新": await force_update(update, context)
    elif text == "📸 拍摄照片": await capture_media(update, context, "photo")
    elif text == "🎵 播放列表": await list_audio_files(update, context)
    
    # 兼容旧菜单的 "录制视频" 按钮，将其导向连拍模式
    elif text == "💥 连拍模式" or text == "📹 录制视频": 
        if text == "📹 录制视频":
            await update.message.reply_text(
                "⚠️ **菜单已过期**\n视频功能已升级为连拍模式。\n正在为您执行连拍...",
                reply_markup=ReplyKeyboardMarkup(MENU_KEYBOARD, resize_keyboard=True) # 顺便刷新用户的键盘
            )
        await capture_media(update, context, "burst")
        
    elif text == "🎤 录制音频": await capture_media(update, context, "audio")
    elif text == "🔦 手电筒": await toggle_torch(update, context)
    elif text == "🌐 公网 IP": await check_ip(update, context)
    elif text == "💻 终端命令":
        await update.message.reply_text("使用 `/exec <命令>` 执行任意 Shell 指令。\n例如: `/exec ls -lh`")
    elif text == "💀 进程管理": await show_processes(update, context) # Hidden command

async def check_connectivity(app):
    """启动前自检网络"""
    print("⏳ 正在测试 Telegram API 连接...")
    try:
        me = await app.bot.get_me()
        print(f"✅ 连接成功! Bot 信息: @{me.username} (ID: {me.id})")
        print(f"✅ 管理员 ID: {ADMIN_ID}")
    except InvalidToken:
        print("❌ 错误: Bot Token 无效！请检查 bot_modules/config.py")
        sys.exit(1)
    except NetworkError as e:
        print(f"❌ 网络错误: 无法连接到 Telegram 服务器。")
        print(f"🔍 调试信息: {e}")
        print(f"🌐 当前代理配置: {PROXY_URL or '无 (直连)'}")
        print("💡 提示: 请检查 VPN/代理 是否开启，或者尝试配置 http_proxy 环境变量。")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        sys.exit(1)

def main():
    print("🚀 正在初始化 Bot...")

    # 1. 配置网络请求 (代理支持)
    request_kwargs = {
        'connect_timeout': 10.0,
        'read_timeout': 10.0,
    }
    
    if PROXY_URL:
        print(f"🌐 使用代理: {PROXY_URL}")
        request_kwargs['proxy_url'] = PROXY_URL
    else:
        print("ℹ️ 未检测到代理 (http_proxy)。尝试直连...")

    request = HTTPXRequest(**request_kwargs)

    # 2. 构建应用
    try:
        builder = ApplicationBuilder().token(BOT_TOKEN)
        builder.request(request)
        app = builder.build()
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return

    # 3. 运行连接自检 (在主事件循环之前)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(check_connectivity(app))

    # Command Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("exec", exec_command))
    app.add_handler(CommandHandler("update", force_update))
    
    # Message Handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, play_received_audio))
    
    # Callback Handlers
    app.add_handler(CallbackQueryHandler(handle_process_callback, pattern="^(kill:|refresh_ps)"))
    app.add_handler(CallbackQueryHandler(stop_playback_callback, pattern="^media_stop"))
    app.add_handler(CallbackQueryHandler(handle_audio_selection, pattern="^sel_audio:"))
    app.add_handler(CallbackQueryHandler(handle_loop_callback, pattern="^play_loop:"))

    # Error Handler
    app.add_error_handler(error_handler)

    print(f"🎉 Bot 主程序已启动，正在轮询消息...")
    app.run_polling()

if __name__ == '__main__':
    main()