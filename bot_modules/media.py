import os
import asyncio
import subprocess
import json
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from .config import MEDIA_DIR, logger
from .utils import clean_device, send_toast

async def check_camera_available():
    """检查摄像头是否可用"""
    try:
        # 尝试直接命令
        cmd = "termux-camera-info"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        
        # 兼容 PRoot 环境，尝试绝对路径
        if result.returncode != 0 or not result.stdout.strip():
            cmd = "/data/data/com.termux/files/usr/bin/termux-camera-info"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)

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
    cmd = ""
    
    # 2. 诊断摄像头 (仅视频/照片)
    if media_type in ["photo", "video"]:
        available, info = await check_camera_available()
        if not available:
            await update.message.reply_text(
                f"❌ **无法调用摄像头**\n"
                f"诊断信息: {info}\n\n"
                f"**解决方案:**\n"
                f"1. 确保安装了 `Termux:API` App 并在系统中授予其相机权限。\n"
                f"2. 确保 `Termux` App 也拥有相机权限。\n"
                f"3. 尝试重启手机。"
            , parse_mode='Markdown')
            return
    
    if media_type == "photo":
        filename = os.path.join(MEDIA_DIR, f"img_{timestamp}.jpg")
        # 自动选择摄像头
        cmd = f"termux-camera-photo {filename}"
        msg = "📸 正在拍照..."
        
    elif media_type == "video":
        filename = os.path.join(MEDIA_DIR, f"vid_{timestamp}.mp4")
        # Android 7.1.1 建议使用 -l 限制时长，比手动停止更稳定
        # -c 0 使用后置摄像头 (通常 ID 0 是后置)
        cmd = f"termux-camera-record -l 30 {filename}"
        msg = "📹 正在启动录制 (30秒)..."
        
    else:
        filename = os.path.join(MEDIA_DIR, f"rec_{timestamp}.m4a")
        # 音频使用 -l 限制
        cmd = f"termux-microphone-record -l 30 -f {filename}"
        msg = "🎤 正在启动录音 (30秒)..."

    status_msg = await update.message.reply_text(msg)
    
    try:
        # 执行命令
        # 注意: termux-camera-record -l 在旧版 API 中可能是阻塞的，也可能是非阻塞的。
        # 为保险起见，我们使用 subprocess.Popen 并在 Python 端等待。
        
        logger.info(f"Running: {cmd}")
        
        if media_type == "photo":
             result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
             if result.returncode != 0:
                 raise Exception(f"命令返回错误: {result.stderr}")
        else:
            # 对于视频/音频，给予 35 秒超时 (录制 30秒 + 缓冲)
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # 轮询检查进程是否过早退出 (3秒内退出通常意味着失败)
            try:
                code = process.wait(timeout=3)
                # 如果能在 3秒内返回，说明要么瞬间完成(不可能)，要么瞬间失败
                err = process.stderr.read()
                if code != 0:
                    raise Exception(f"启动失败 (Exit {code}): {err}")
            except subprocess.TimeoutExpired:
                # 进程正在运行，这很好。
                # 我们等待剩余时间 (例如 28秒)
                await asyncio.sleep(28)
                
                # 再次检查是否结束
                if process.poll() is None:
                    # 如果还没结束（可能 -l 参数无效），手动停止
                    await clean_device()
                    process.terminate()

        # 检查文件
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            await status_msg.edit_text("📤 上传中...")
            with open(filename, 'rb') as f:
                if media_type == "photo": await context.bot.send_photo(chat_id, f)
                elif media_type == "video": await context.bot.send_video(chat_id, f)
                else: await context.bot.send_audio(chat_id, f)
            
            await status_msg.delete()
            await send_toast(f"Captured {media_type}")
        else:
            raise Exception("文件未生成或大小为0")

    except Exception as e:
        await clean_device()
        logger.error(f"Media error: {e}")
        
        # 针对 Android 7.1.1 的特定提示
        tip = ""
        if "启动失败" in str(e) or "文件未生成" in str(e):
            tip = "\n\n💡 **Termux (Android 7) 提示:**\n1. 请检查 Termux:API APP 是否已安装且授予权限。\n2. 尝试在 Termux 终端手动运行 `termux-camera-record test.mp4` 看看是否报错。"
            
        await status_msg.edit_text(f"❌ **录制失败**\n错误信息: {str(e)}{tip}", parse_mode='Markdown')

async def play_received_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """下载并播放用户发送的音频"""
    if not update.effective_user or not check_admin(update.effective_user.id): return

    msg = await update.message.reply_text("📥 正在下载音频...")
    
    try:
        # 1. 获取文件对象
        file_obj = None
        ext = ".ogg" 
        
        if update.message.voice:
            file_obj = await update.message.voice.get_file()
            ext = ".ogg"
        elif update.message.audio:
            file_obj = await update.message.audio.get_file()
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
        await msg.edit_text("▶️ 正在播放...")
        
        # 尝试多种播放命令
        cmds = [
            f"termux-media-player play '{filepath}'",
            f"play-audio '{filepath}'",
            f"/data/data/com.termux/files/usr/bin/termux-media-player play '{filepath}'"
        ]
        
        success = False
        last_err = ""
        
        for cmd in cmds:
            p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if p.returncode == 0:
                success = True
                break
            last_err = p.stderr

        if success:
            await msg.edit_text(f"✅ 播放成功\n📄 `{filename}`", parse_mode='Markdown')
            await send_toast(f"Playing {filename}")
        else:
             await msg.edit_text(f"❌ 播放失败 (尝试了多种方法)\n错误: {last_err}")

    except Exception as e:
        logger.error(f"Play audio error: {e}")
        await msg.edit_text(f"❌ 错误: {e}")

async def cleanup_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🗑 清理中...")
    try:
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
