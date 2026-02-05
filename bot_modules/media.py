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
    
    # 1. 极强力清理设备占用
    await clean_device()
    # 等待一秒让硬件释放
    time.sleep(1)
    
    if media_type == "photo":
        filename = os.path.join(MEDIA_DIR, f"img_{timestamp}.jpg")
        # -c 0: Explicitly use Back Camera
        cmd = f"termux-camera-photo -c 0 {filename}"
        alt_cmd = f"{termux_bin}/termux-camera-photo -c 0 {filename}"
        msg = "📸 正在调用后置摄像头拍照..."
        duration_limit = 8
        
    elif media_type == "video":
        filename = os.path.join(MEDIA_DIR, f"vid_{timestamp}.mp4")
        # Video: Limit 30s, Back Camera (-c 0)
        cmd = f"termux-camera-record -c 0 -l 30 {filename}"
        alt_cmd = f"{termux_bin}/termux-camera-record -c 0 -l 30 {filename}"
        msg = "📹 正在启动录制 (30秒)..."
        duration_limit = 35
        
    else:
        filename = os.path.join(MEDIA_DIR, f"rec_{timestamp}.m4a")
        # Audio: Limit 30s
        cmd = f"termux-microphone-record -l 30 -f {filename}"
        alt_cmd = f"{termux_bin}/termux-microphone-record -l 30 -f {filename}"
        msg = "🎤 正在录制音频 (30秒)..."
        duration_limit = 35

    status_msg = await update.message.reply_text(msg)
    
    start_time = time.time()
    try:
        # 执行命令
        result = subprocess.run(f"{cmd} || {alt_cmd}", shell=True, timeout=duration_limit, capture_output=True, text=True)
        
        elapsed = time.time() - start_time
        file_exists = os.path.exists(filename) and os.path.getsize(filename) > 0
        
        # 2. 失败判定逻辑
        if not file_exists:
            logger.error(f"Recording failed. Stderr: {result.stderr}")
            
            # --- 智能错误分析 ---
            err_text = result.stderr.lower()
            
            if "not found" in err_text:
                await status_msg.edit_text(
                    "❌ **缺少 Termux API 组件**\n\n"
                    "系统找不到录制命令。您可能安装了 Termux:API **App**，但未安装 **命令行包**。\n\n"
                    "🛠 **修复方法**:\n"
                    "1. 请打开 Termux 原生终端 (不要在 Ubuntu/Proot 内)\n"
                    "2. 执行命令: `pkg install termux-api`\n"
                    "3. 授予权限: 手机设置 > 应用 > Termux > 权限 > 允许相机/麦克风"
                )
                return

            if "permission" in err_text or "denied" in err_text:
                 await status_msg.edit_text(
                    "❌ **权限不足**\n\n"
                    "请到手机设置中授予 Termux **麦克风** 和 **相机** 权限。\n"
                    "设置 > 应用 > Termux > 权限"
                )
                 return

            if "connection refused" in err_text or "socket" in err_text:
                 await status_msg.edit_text(
                    "❌ **API 连接失败**\n\n"
                    "无法连接到 Termux:API 服务。\n"
                    "1. 确保已安装 Termux:API 安卓应用。\n"
                    "2. 如果在 Ubuntu (PRoot) 中运行，尝试在原生 Termux 中运行 Bot。"
                )
                 return

            # 通用错误
            await status_msg.edit_text(
                f"❌ 录制失败 (耗时 {elapsed:.1f}s)\n"
                f"错误: `{result.stderr[:200]}`"
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
        
    except subprocess.TimeoutExpired:
        await clean_device()
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            await status_msg.edit_text("📤 录制时间到，正在上传...")
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
        patterns = ["*.jpg", "*.mp4", "*.m4a"]
        count = 0
        for pat in patterns:
            files = glob.glob(os.path.join(MEDIA_DIR, pat))
            for f in files:
                try:
                    os.remove(f)
                    count += 1
                except: pass
        
        await msg.edit_text(f"✅ 清理完成！\n共释放 {count} 个文件。\n\n提示: 建议定期清理以节省手机空间。")
        await send_toast(f"Bot: Deleted {count} files")
    except Exception as e:
        await msg.edit_text(f"❌ 清理失败: {e}")
