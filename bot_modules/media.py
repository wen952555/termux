import os
import time
import subprocess
import glob
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from .config import MEDIA_DIR, logger
from .utils import clean_device, send_toast

async def capture_media(update: Update, context: ContextTypes.DEFAULT_TYPE, media_type):
    chat_id = update.effective_chat.id
    termux_bin = "/data/data/com.termux/files/usr/bin"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. 强制清理设备占用
    await clean_device()
    
    if media_type == "photo":
        filename = os.path.join(MEDIA_DIR, f"img_{timestamp}.jpg")
        cmd = f"termux-camera-photo -c 0 {filename}"
        alt_cmd = f"{termux_bin}/termux-camera-photo -c 0 {filename}"
        msg = "📸 正在调用后置摄像头拍照..."
        duration_limit = 5 
        
    elif media_type == "video":
        filename = os.path.join(MEDIA_DIR, f"vid_{timestamp}.mp4")
        # Video: 30s limit
        cmd = f"termux-camera-record -l 30 {filename}"
        alt_cmd = f"{termux_bin}/termux-camera-record -l 30 {filename}"
        msg = "📹 正在录制视频 (30秒)..."
        duration_limit = 30
        
    else:
        filename = os.path.join(MEDIA_DIR, f"rec_{timestamp}.m4a")
        # Audio: 30s limit. Default encoder.
        cmd = f"termux-microphone-record -l 30 -f {filename}"
        alt_cmd = f"{termux_bin}/termux-microphone-record -l 30 -f {filename}"
        msg = "🎤 正在录制环境音 (30秒)..."
        duration_limit = 30

    status_msg = await update.message.reply_text(msg)
    
    start_time = time.time()
    try:
        # Give a small buffer (5s) over the limit
        result = subprocess.run(f"{cmd} || {alt_cmd}", shell=True, timeout=duration_limit + 5, capture_output=True, text=True)
        
        elapsed = time.time() - start_time
        
        # 2. 验证逻辑：如果录音/录像瞬间结束 (<2s)，视为失败
        if media_type in ["video", "audio"] and elapsed < 2:
            logger.error(f"Recording failed instantly. Stderr: {result.stderr}")
            await status_msg.edit_text(
                "❌ 录制失败：进程异常退出。\n"
                "可能原因：\n"
                "1. 未授予 Termux 麦克风/摄像头权限\n"
                "2. 设备正被其他应用占用\n"
                "3. 当前环境不支持 Termux API"
            )
            return

        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            await status_msg.edit_text("📤 捕获成功，正在上传...")
            with open(filename, 'rb') as f:
                if media_type == "photo":
                    await context.bot.send_photo(chat_id, f)
                elif media_type == "video":
                    await context.bot.send_video(chat_id, f)
                else:
                    await context.bot.send_audio(chat_id, f)
            await status_msg.delete()
            await send_toast(f"Bot: Captured {media_type}")
        else:
            await status_msg.edit_text("❌ 文件生成失败 (0KB)。\n请检查 Termux:API 安装情况及权限。")
            
    except subprocess.TimeoutExpired:
        # 如果超时，尝试停止并上传已录制的内容
        await clean_device()
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            await status_msg.edit_text("📤 录制完成，上传中...")
            try:
                with open(filename, 'rb') as f:
                    if media_type == "video": await context.bot.send_video(chat_id, f)
                    else: await context.bot.send_audio(chat_id, f)
            except Exception as e:
                await status_msg.edit_text(f"❌ 上传失败: {e}")
        else:
            await status_msg.edit_text("❌ 录制超时且未生成有效文件。")
            
    except Exception as e:
        await status_msg.edit_text(f"❌ 未知错误: {e}")

async def cleanup_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete all files in the captured_media directory"""
    msg = await update.message.reply_text("🗑 正在清理媒体缓存...")
    try:
        files = glob.glob(os.path.join(MEDIA_DIR, "*"))
        count = 0
        for f in files:
            try:
                os.remove(f)
                count += 1
            except: pass
        
        await msg.edit_text(f"✅ 清理完成！\n共删除 {count} 个文件。")
        await send_toast(f"Bot: Deleted {count} files")
    except Exception as e:
        await msg.edit_text(f"❌ 清理失败: {e}")
