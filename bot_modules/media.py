import os
import asyncio
import subprocess
import json
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from .config import MEDIA_DIR, logger
from .utils import clean_device, send_toast, get_executable_path

async def check_camera_available():
    """检查摄像头是否可用"""
    exe = get_executable_path("termux-camera-info")
    if not exe:
        return False, "未找到 termux-camera-info 命令。请运行 `pkg install termux-api`"
        
    try:
        result = subprocess.run(exe, shell=True, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            cameras = json.loads(result.stdout)
            if isinstance(cameras, list) and len(cameras) > 0:
                return True, f"检测到 {len(cameras)} 个摄像头"
            else:
                return False, "摄像头列表为空 (API 返回 [])"
        else:
            return False, f"无法执行 camera-info: {result.stderr}"
    except Exception as e:
        return False, str(e)

async def capture_media(update: Update, context: ContextTypes.DEFAULT_TYPE, media_type):
    chat_id = update.effective_chat.id
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. 强力清理设备占用
    await clean_device()
    await asyncio.sleep(1)
    
    filename = ""
    msg = ""
    cmd_exe = ""
    cmd_args = ""
    
    # 2. 检查命令是否存在
    if media_type == "photo":
        cmd_exe = get_executable_path("termux-camera-photo")
    elif media_type == "video":
        cmd_exe = get_executable_path("termux-camera-record")
    else:
        cmd_exe = get_executable_path("termux-microphone-record")
        
    if not cmd_exe:
        await update.message.reply_text(
            f"❌ **命令未找到**\n"
            f"Termux 缺少必要的软件包。\n\n"
            f"请在 Termux 终端运行以下命令安装：\n"
            f"`pkg install termux-api`",
            parse_mode='Markdown'
        )
        return

    # 3. 准备参数
    if media_type == "photo":
        filename = os.path.join(MEDIA_DIR, f"img_{timestamp}.jpg")
        cmd_args = f"{cmd_exe} {filename}"
        msg = "📸 正在拍照..."
        
    elif media_type == "video":
        filename = os.path.join(MEDIA_DIR, f"vid_{timestamp}.mp4")
        # Android 7 使用 -l 限制时长
        cmd_args = f"{cmd_exe} -l 30 {filename}"
        msg = "📹 正在启动录制 (30秒)..."
        
    else:
        filename = os.path.join(MEDIA_DIR, f"rec_{timestamp}.m4a")
        cmd_args = f"{cmd_exe} -l 30 -f {filename}"
        msg = "🎤 正在启动录音 (30秒)..."

    status_msg = await update.message.reply_text(msg)
    
    try:
        logger.info(f"Running: {cmd_args}")
        
        # 4. 执行命令
        if media_type == "photo":
             result = subprocess.run(cmd_args, shell=True, capture_output=True, text=True, timeout=15)
             if result.returncode != 0:
                 raise Exception(f"命令返回错误: {result.stderr}")
        else:
            # 视频/音频 (限制时长模式)
            process = subprocess.Popen(cmd_args, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # 立即检查是否秒退
            try:
                code = process.wait(timeout=2)
                if code != 0:
                    err = process.stderr.read()
                    raise Exception(f"启动失败 (Exit {code}): {err}")
            except subprocess.TimeoutExpired:
                # 正常运行中，等待录制完成 (30s + 缓冲)
                await asyncio.sleep(32)
                if process.poll() is None:
                    process.terminate()

        # 5. 检查文件生成
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            await status_msg.edit_text("📤 上传中...")
            with open(filename, 'rb') as f:
                if media_type == "photo": await context.bot.send_photo(chat_id, f)
                elif media_type == "video": await context.bot.send_video(chat_id, f)
                else: await context.bot.send_audio(chat_id, f)
            
            await status_msg.delete()
            await send_toast(f"Captured {media_type}")
        else:
            raise Exception("文件未生成")

    except Exception as e:
        await clean_device()
        logger.error(f"Media error: {e}")
        await status_msg.edit_text(f"❌ **操作失败**\n错误: {str(e)}", parse_mode='Markdown')

async def play_received_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not check_admin(update.effective_user.id): return
    msg = await update.message.reply_text("📥 处理音频...")
    
    try:
        player_exe = get_executable_path("termux-media-player") or get_executable_path("play-audio")
        if not player_exe:
            await msg.edit_text("❌ 未找到播放命令 (termux-media-player)")
            return

        file_obj = await (update.message.voice or update.message.audio).get_file()
        ext = ".ogg" if update.message.voice else ".mp3"
        filename = f"play_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        filepath = os.path.join(MEDIA_DIR, filename)
        
        await file_obj.download_to_drive(filepath)
        await msg.edit_text("▶️ 正在播放...")
        
        cmd = f"{player_exe} play '{filepath}'"
        subprocess.run(cmd, shell=True)
        await msg.edit_text(f"✅ 播放完成")

    except Exception as e:
        await msg.edit_text(f"❌ 错误: {e}")

async def cleanup_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # (保持原有清理逻辑)
    msg = await update.message.reply_text("🗑 清理中...")
    try:
        import glob
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
