import os
import asyncio
import subprocess
import json
from datetime import datetime
from telegram import Update, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .config import MEDIA_DIR, logger
from .utils import clean_device, send_toast, get_executable_path, check_admin

async def capture_media(update: Update, context: ContextTypes.DEFAULT_TYPE, media_type):
    chat_id = update.effective_chat.id
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. 强力清理设备占用 (防止摄像头/麦克风被之前的僵尸进程占用)
    await clean_device()
    await asyncio.sleep(0.5)
    
    # 2. 检查基础命令
    cmd_photo = get_executable_path("termux-camera-photo")
    cmd_audio = get_executable_path("termux-microphone-record")
        
    if not cmd_photo or not cmd_audio:
        await update.message.reply_text(
            f"❌ **命令未找到**\n请运行 `pkg install termux-api` 安装必要组件。",
            parse_mode='Markdown'
        )
        return

    # --- 逻辑分支 ---

    # === 连拍模式 (替代视频) ===
    if media_type == "burst":
        msg = await update.message.reply_text("📸 正在启动连拍 (5张)...")
        files_to_send = []
        
        try:
            for i in range(5):
                # 拍摄间隔
                if i > 0: await asyncio.sleep(0.8)
                
                fname = os.path.join(MEDIA_DIR, f"burst_{timestamp}_{i+1}.jpg")
                cmd = f"{cmd_photo} {fname}"
                logger.info(f"Burst shot {i+1}: {cmd}")
                
                # 执行拍照
                subprocess.run(cmd, shell=True, timeout=10)
                
                if os.path.exists(fname) and os.path.getsize(fname) > 0:
                    files_to_send.append(fname)
            
            if not files_to_send:
                raise Exception("连拍失败，未生成照片")

            await msg.edit_text(f"📤 正在上传 {len(files_to_send)} 张照片...")
            
            # 构造媒体组 (Album)
            media_group = [InputMediaPhoto(open(f, 'rb')) for f in files_to_send]
            await context.bot.send_media_group(chat_id=chat_id, media=media_group)
            
            await msg.delete()
            await send_toast(f"Burst capture: {len(files_to_send)} photos")
            
        except Exception as e:
            logger.error(f"Burst error: {e}")
            await msg.edit_text(f"❌ 连拍失败: {e}")
        return

    # === 单张拍照 ===
    if media_type == "photo":
        filename = os.path.join(MEDIA_DIR, f"img_{timestamp}.jpg")
        msg_obj = await update.message.reply_text("📸 正在拍照...")
        
        try:
            cmd = f"{cmd_photo} {filename}"
            # 拍照可能比较慢，给 15s 超时
            subprocess.run(cmd, shell=True, timeout=15, stderr=subprocess.PIPE)
            
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                await msg_obj.edit_text("📤 上传中...")
                with open(filename, 'rb') as f:
                    await context.bot.send_photo(chat_id, f)
                await msg_obj.delete()
                await send_toast("Photo captured")
            else:
                await msg_obj.edit_text("❌ 拍照失败: 文件未生成 (请检查是否有其他应用占用摄像头)")
        except Exception as e:
            await msg_obj.edit_text(f"❌ 错误: {e}")
        return

    # === 录制音频 (修复版) ===
    if media_type == "audio":
        filename = os.path.join(MEDIA_DIR, f"rec_{timestamp}.m4a")
        duration = 30
        msg_obj = await update.message.reply_text(f"🎤 正在录音 {duration} 秒 (请勿发送新指令)...")
        
        try:
            # -l 指定时长(秒), -f 指定文件, -e 指定编码(aac/amr/wb)
            # 注意: termux-microphone-record 默认是阻塞的，直到录制完成
            cmd = f"{cmd_audio} -l {duration} -f {filename}"
            logger.info(f"Recording audio: {cmd}")
            
            # 使用 subprocess.run 等待命令结束。
            # timeout 设为 duration + 5 秒缓冲，防止死锁
            subprocess.run(cmd, shell=True, timeout=duration + 5, stderr=subprocess.PIPE)
            
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                await msg_obj.edit_text("📤 上传录音...")
                with open(filename, 'rb') as f:
                    await context.bot.send_audio(chat_id, f, duration=duration, title=f"Audio {timestamp}")
                await msg_obj.delete()
                await send_toast("Audio captured")
            else:
                await msg_obj.edit_text("❌ 录音失败: 文件为空 (请检查麦克风权限)")
        except subprocess.TimeoutExpired:
            # 如果超时，尝试终止并发送已经录到的部分
            await clean_device()
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                await msg_obj.edit_text("⚠️ 录音超时，尝试发送已保存部分...")
                with open(filename, 'rb') as f:
                    await context.bot.send_audio(chat_id, f)
            else:
                await msg_obj.edit_text("❌ 录音超时且无文件生成")
        except Exception as e:
            await msg_obj.edit_text(f"❌ 错误: {e}")
        return

async def play_received_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Enhanced audio player:
    1. Downloads voice notes or audio files.
    2. Plays them using termux-media-player.
    3. Shows metadata and a Stop button.
    """
    if not update.effective_user or not check_admin(update.effective_user.id): return
    msg = await update.message.reply_text("📥 正在下载音频...")
    
    try:
        player_exe = get_executable_path("termux-media-player")
        if not player_exe:
            await msg.edit_text("❌ 未找到 `termux-media-player`。\n请先安装: `pkg install termux-api`")
            return

        # 1. 提取文件信息
        attachment = update.message.voice or update.message.audio
        
        original_fname = "Unknown"
        ext = ".ogg" # 语音消息默认
        
        if update.message.audio:
            ext = ".mp3" # 默认兜底
            if update.message.audio.file_name:
                original_fname = update.message.audio.file_name
                _, f_ext = os.path.splitext(original_fname)
                if f_ext: ext = f_ext
        else:
            original_fname = f"Voice_{datetime.now().strftime('%H%M%S')}"

        # 2. 下载
        filename = f"play_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        filepath = os.path.join(MEDIA_DIR, filename)
        
        file_obj = await attachment.get_file()
        await file_obj.download_to_drive(filepath)
        
        # 3. 播放
        await msg.edit_text("▶️ 启动播放器...")
        
        # Termux API play
        cmd = f"{player_exe} play '{filepath}'"
        subprocess.run(cmd, shell=True)
        
        # 4. 显示信息与控制
        info_text = f"🎶 **正在播放**\n"
        
        if update.message.audio:
            title = update.message.audio.title or original_fname
            performer = update.message.audio.performer or "未知艺术家"
            info_text += f"🎵 **标题**: {title}\n👤 **歌手**: {performer}\n"
            info_text += f"📄 **文件**: `{original_fname}`"
        else:
            info_text += f"🎤 **语音消息**\n📅 {datetime.now().strftime('%H:%M:%S')}"

        keyboard = [[InlineKeyboardButton("⏹ 停止播放", callback_data="media_stop")]]
        
        await msg.edit_text(info_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        await send_toast(f"Playing audio")

    except Exception as e:
        logger.error(f"Play error: {e}")
        await msg.edit_text(f"❌ 播放失败: {e}")

async def stop_playback_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("正在停止...")
    
    player_exe = get_executable_path("termux-media-player")
    if player_exe:
        subprocess.run(f"{player_exe} stop", shell=True)
        await query.edit_message_text(f"{query.message.text}\n\n✅ 播放已停止")
    else:
        await query.edit_message_text("❌ 无法停止: 命令丢失")

async def cleanup_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🗑 清理中...")
    try:
        import glob
        patterns = ["*.jpg", "*.mp4", "*.m4a", "*.ogg", "*.mp3", "*.wav", "play_*"]
        count = 0
        for pat in patterns:
            files = glob.glob(os.path.join(MEDIA_DIR, pat))
            for f in files:
                try: os.remove(f); count += 1
                except: pass
        await msg.edit_text(f"✅ 已清理 {count} 个文件。")
    except Exception as e:
        await msg.edit_text(f"❌ 失败: {e}")