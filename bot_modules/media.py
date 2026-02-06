import os
import asyncio
import subprocess
import json
import glob
from datetime import datetime
from telegram import Update, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .config import MEDIA_DIR, logger
from .utils import clean_device, send_toast, get_executable_path, check_admin

# 全局变量控制播放任务
CURRENT_PLAYBACK_TASK = None
STOP_FLAG = False

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

# === 播放逻辑 ===

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
        
        # 3. 触发播放（默认只播一次）
        await start_playback_task(msg, filepath, loop_count=1, title=original_fname)

    except Exception as e:
        logger.error(f"Play error: {e}")
        await msg.edit_text(f"❌ 播放失败: {e}")

# === 音频列表与循环功能 ===

async def list_audio_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin(update.effective_user.id): return

    audio_files = []
    # 扫描支持的音频格式
    extensions = ['*.mp3', '*.m4a', '*.wav', '*.ogg', '*.flac']
    for ext in extensions:
        audio_files.extend(glob.glob(os.path.join(MEDIA_DIR, ext)))
    
    # 按修改时间排序，最新的在前
    audio_files.sort(key=os.path.getmtime, reverse=True)
    
    if not audio_files:
        await update.message.reply_text("📂 媒体库中没有找到音频文件。")
        return

    keyboard = []
    # 限制显示前 20 个，防止消息过长
    for f in audio_files[:20]:
        filename = os.path.basename(f)
        # 按钮回调: select_audio:filename
        keyboard.append([InlineKeyboardButton(f"🎵 {filename}", callback_data=f"sel_audio:{filename}")])
    
    await update.message.reply_text(
        f"📂 **音频列表** (共 {len(audio_files)} 个)\n请选择要播放的音频：",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_audio_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """当用户选择一个文件后，询问循环次数"""
    query = update.callback_query
    await query.answer()
    
    filename = query.data.split(":", 1)[1]
    
    # 构建循环次数选择菜单
    # 回调格式: play_loop:<count>:<filename>
    keyboard = [
        [
            InlineKeyboardButton("1 次", callback_data=f"play_loop:1:{filename}"),
            InlineKeyboardButton("2 次", callback_data=f"play_loop:2:{filename}"),
            InlineKeyboardButton("3 次", callback_data=f"play_loop:3:{filename}"),
        ],
        [
            InlineKeyboardButton("5 次", callback_data=f"play_loop:5:{filename}"),
            InlineKeyboardButton("10 次", callback_data=f"play_loop:10:{filename}"),
            InlineKeyboardButton("♾ 无限循环", callback_data=f"play_loop:9999:{filename}"),
        ],
        [InlineKeyboardButton("🔙 返回列表", callback_data="back_to_audio_list")] # 这里需要自行实现或者只是简单取消
    ]
    
    await query.edit_message_text(
        f"💿 **已选择**: `{filename}`\n\n请选择播放模式：",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def start_playback_task(msg_obj, filepath, loop_count, title="Unknown"):
    """启动异步任务来管理循环播放"""
    global CURRENT_PLAYBACK_TASK, STOP_FLAG
    
    # 停止之前的任务
    STOP_FLAG = True
    if CURRENT_PLAYBACK_TASK and not CURRENT_PLAYBACK_TASK.done():
        CURRENT_PLAYBACK_TASK.cancel()
        try: await CURRENT_PLAYBACK_TASK
        except asyncio.CancelledError: pass
    
    STOP_FLAG = False
    
    # 定义后台播放函数
    async def playback_loop():
        player_exe = get_executable_path("termux-media-player")
        if not player_exe: return

        count_str = "♾ 无限" if loop_count > 1000 else str(loop_count)
        
        # 更新 UI
        keyboard = [[InlineKeyboardButton("⏹ 停止播放", callback_data="media_stop")]]
        await msg_obj.edit_text(
            f"🎶 **正在播放**: {title}\n🔄 **模式**: 循环 {count_str} 次\n▶️ 状态: 启动中...",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

        current_iter = 1
        while current_iter <= loop_count and not STOP_FLAG:
            if loop_count > 1:
                # 只有循环时才频繁更新 UI，避免 api 限制
                 try:
                    await msg_obj.edit_text(
                        f"🎶 **正在播放**: {title}\n🔄 **进度**: 第 {current_iter} / {count_str} 次",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )
                 except: pass

            # 1. 开始播放
            logger.info(f"Starting playback iteration {current_iter}")
            subprocess.run(f"{player_exe} play '{filepath}'", shell=True)
            await send_toast(f"Playing: {title} ({current_iter})")
            
            # 2. 轮询状态直到播放结束
            # termux-media-player info 返回 JSON: { "status": "playing" ... }
            while not STOP_FLAG:
                await asyncio.sleep(2) # 每2秒检查一次
                try:
                    res = subprocess.check_output(f"{player_exe} info", shell=True).decode()
                    status = json.loads(res).get("status", "stopped")
                    if status != "playing":
                        break # 当前歌曲结束
                except Exception as e:
                    logger.error(f"Status check failed: {e}")
                    break # 出错则跳过
            
            current_iter += 1
            if not STOP_FLAG and current_iter <= loop_count:
                await asyncio.sleep(1) # 间隔缓冲

        if not STOP_FLAG:
            await msg_obj.edit_text(f"✅ 播放结束 (已完成 {count_str} 次循环)")

    # 启动任务
    CURRENT_PLAYBACK_TASK = asyncio.create_task(playback_loop())

async def handle_loop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(":")
    count = int(data[1])
    filename = data[2]
    filepath = os.path.join(MEDIA_DIR, filename)
    
    if not os.path.exists(filepath):
        await query.edit_message_text("❌ 文件不存在 (可能已被删除)")
        return
        
    await start_playback_task(query.message, filepath, count, title=filename)

async def stop_playback_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global STOP_FLAG
    query = update.callback_query
    await query.answer("正在停止...")
    
    # 1. 设置标志位，让 Loop 退出
    STOP_FLAG = True
    
    # 2. 强制停止当前播放
    player_exe = get_executable_path("termux-media-player")
    if player_exe:
        subprocess.run(f"{player_exe} stop", shell=True)
    
    # 3. 取消任务
    if CURRENT_PLAYBACK_TASK and not CURRENT_PLAYBACK_TASK.done():
        CURRENT_PLAYBACK_TASK.cancel()
        
    await query.edit_message_text(f"{query.message.text}\n\n✅ 播放已手动停止")

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