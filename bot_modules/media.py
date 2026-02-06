import os
import asyncio
import subprocess
import glob
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from .config import MEDIA_DIR, logger
from .utils import clean_device, send_toast, check_admin

async def capture_media(update: Update, context: ContextTypes.DEFAULT_TYPE, media_type):
    chat_id = update.effective_chat.id
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. 强力清理设备占用 (防止上一次录制未退出)
    await clean_device()
    await asyncio.sleep(1) # 使用异步等待
    
    filename = ""
    msg = ""
    
    if media_type == "photo":
        filename = os.path.join(MEDIA_DIR, f"img_{timestamp}.jpg")
        cmd = f"termux-camera-photo -c 0 {filename}"
        msg = "📸 正在拍照..."
        
    elif media_type == "video":
        filename = os.path.join(MEDIA_DIR, f"vid_{timestamp}.mp4")
        # 视频不再使用 -l 限制，改为手动开始和停止
        start_cmd = f"termux-camera-record -c 0 {filename}"
        stop_cmd = "termux-camera-record -q"
        msg = "📹 正在启动录制 (30秒)..."
        
    else:
        filename = os.path.join(MEDIA_DIR, f"rec_{timestamp}.m4a")
        # 音频不再使用 -l 限制，改为手动开始和停止
        start_cmd = f"termux-microphone-record -f {filename}"
        stop_cmd = "termux-microphone-record -q"
        msg = "🎤 正在启动录音 (30秒)..."

    status_msg = await update.message.reply_text(msg)
    
    try:
        if media_type == "photo":
            # 拍照是瞬间动作，直接运行
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise Exception(f"命令执行错误: {result.stderr}")
        else:
            # 录音和录像：采用 "启动 -> 等待 -> 停止" 模式
            # 1. 启动进程 (不等待它结束)
            process = subprocess.Popen(start_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 2. 异步等待 30 秒 (期间 Bot 可以响应其他消息)
            await asyncio.sleep(30)
            
            # 3. 发送停止信号
            subprocess.run(stop_cmd, shell=True, capture_output=True)
            
            # 4. 确保进程结束
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()

        # 检查文件结果
        file_exists = os.path.exists(filename) and os.path.getsize(filename) > 0
        
        if not file_exists:
            # 错误分析
            error_hint = "未知错误"
            if media_type == "video":
                error_hint = "Android 11+ 系统限制严格，后台调用录像极易失败。请尝试保持 Termux 前台亮屏运行，或改用拍照功能。"
            
            await status_msg.edit_text(
                f"❌ **{media_type} 录制失败**\n"
                f"未生成文件。可能原因：\n"
                f"1. 权限被拒绝 (请在手机设置授予 Termux 权限)\n"
                f"2. 设备硬件被占用\n"
                f"3. {error_hint}"
            )
            return

        # 3. 成功上传
        await status_msg.edit_text("📤 录制完成，正在上传...")
        
        with open(filename, 'rb') as f:
            if media_type == "photo":
                await context.bot.send_photo(chat_id, f)
            elif media_type == "video":
                await context.bot.send_video(chat_id, f)
            else:
                await context.bot.send_audio(chat_id, f)
        
        await status_msg.delete()
        await send_toast(f"Bot: Captured {media_type}")
        
    except Exception as e:
        await clean_device()
        logger.error(f"Media capture error: {e}")
        await status_msg.edit_text(f"❌ 执行出错: {str(e)}")

async def play_received_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """下载并播放用户发送的音频"""
    if not check_admin(update.effective_user.id): return

    msg = await update.message.reply_text("📥 正在下载音频...")
    
    try:
        # 1. 获取文件对象
        file_obj = None
        ext = ".ogg" # 默认语音消息格式
        
        if update.message.voice:
            file_obj = await update.message.voice.get_file()
            ext = ".ogg"
        elif update.message.audio:
            file_obj = await update.message.audio.get_file()
            # 尝试获取原始扩展名，如果没有则默认mp3
            if update.message.audio.file_name:
                _, ext = os.path.splitext(update.message.audio.file_name)
            else:
                ext = ".mp3"
        
        if not file_obj:
            await msg.edit_text("❌ 无法获取音频文件")
            return

        # 2. 保存文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"play_{timestamp}{ext}"
        filepath = os.path.join(MEDIA_DIR, filename)
        
        await file_obj.download_to_drive(filepath)
        
        # 3. 调用 Termux 播放
        await msg.edit_text("▶️ 正在 Termux 上播放...")
        
        # 使用 termux-media-player play <file>
        cmd = f"termux-media-player play '{filepath}'"
        
        # 执行命令
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if proc.returncode == 0:
            await msg.edit_text(f"✅ 播放请求已发送\n📄 文件: `{filename}`")
            await send_toast(f"Playing: {filename}")
        else:
            # 尝试备用命令 play-audio
            cmd_alt = f"play-audio '{filepath}'"
            proc_alt = subprocess.run(cmd_alt, shell=True, capture_output=True, text=True)
            if proc_alt.returncode == 0:
                 await msg.edit_text(f"✅ 播放成功 (play-audio)\n📄 文件: `{filename}`")
            else:
                 await msg.edit_text(f"❌ 播放失败。请确保安装了 termux-api。\n错误: {proc.stderr}")

    except Exception as e:
        logger.error(f"Play audio error: {e}")
        await msg.edit_text(f"❌ 错误: {e}")

async def cleanup_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🗑 清理中...")
    try:
        # 增加清理 .ogg 和 .mp3
        patterns = ["*.jpg", "*.mp4", "*.m4a", "*.ogg", "*.mp3", "*.wav"]
        count = 0
        for pat in patterns:
            files = glob.glob(os.path.join(MEDIA_DIR, pat))
            for f in files:
                try: os.remove(f); count += 1
                except: pass
        await msg.edit_text(f"✅ 已清理 {count} 个文件。")
    except Exception as e:
        await msg.edit_text(f"❌ 失败: {e}")
