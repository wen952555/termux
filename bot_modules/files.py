import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

async def show_files(update: Update, context: ContextTypes.DEFAULT_TYPE, path="."):
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        await update.message.reply_text("❌ 路径不存在")
        return

    context.user_data['cwd'] = abs_path
    
    try:
        items = sorted(os.listdir(abs_path))
    except Exception as e:
        await update.message.reply_text(f"❌ 无法读取目录: {e}")
        return

    keyboard = []
    if abs_path != "/":
        keyboard.append([InlineKeyboardButton("⬆️ 上一级", callback_data="dir:..")])

    folders = [i for i in items if os.path.isdir(os.path.join(abs_path, i))]
    files = [i for i in items if os.path.isfile(os.path.join(abs_path, i))]
    
    # Limit to top 10 to avoid message length limits
    for f in folders[:10]:
        keyboard.append([InlineKeyboardButton(f"📂 {f}", callback_data=f"dir:{f}")])
    for f in files[:10]:
        keyboard.append([InlineKeyboardButton(f"📄 {f}", callback_data=f"file:{f}")])
    
    text = f"📂 **文件浏览器**\n路径: `{abs_path}`\n(列表已折叠，仅显示前20项)"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_file_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    current_cwd = context.user_data.get('cwd', os.getcwd())
    
    if data.startswith("dir:"):
        target = data.split(":", 1)[1]
        new_path = os.path.join(current_cwd, target)
        await show_files(update, context, new_path)
        
    elif data.startswith("file:"):
        filename = data.split(":", 1)[1]
        filepath = os.path.join(current_cwd, filename)
        
        await query.message.reply_text(f"📤 正在发送文件 `{filename}`...", parse_mode='Markdown')
        try:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=open(filepath, 'rb')
            )
        except Exception as e:
            await query.message.reply_text(f"❌ 发送失败: {e}")
