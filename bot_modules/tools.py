import subprocess
import socket
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .utils import check_admin

# --- FLASHLIGHT ---

# 全局变量追踪状态 (默认为关)
TORCH_STATE = False

async def toggle_torch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global TORCH_STATE
    
    # 切换状态
    TORCH_STATE = not TORCH_STATE
    action = "on" if TORCH_STATE else "off"
    
    cmd = f"termux-torch {action}"
    alt = f"/data/data/com.termux/files/usr/bin/termux-torch {action}"
    
    try:
        # 执行命令 (不检查返回值，因为 termux-torch 有时无输出)
        subprocess.run(f"{cmd} || {alt}", shell=True)
        
        status_msg = "💡 手电筒已开启" if TORCH_STATE else "🌑 手电筒已关闭"
        await update.message.reply_text(status_msg)
        
    except Exception as e:
        # 失败回滚状态
        TORCH_STATE = not TORCH_STATE
        await update.message.reply_text(f"❌ 执行失败: {e}")

# --- IP CHECK ---

def get_real_local_ip():
    """
    使用 UDP 连接技巧获取真实路由 IP (不会实际发送数据)。
    这比 socket.gethostname() 在 Termux 上准确得多。
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 连接 Google DNS (不需要实际可达)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

async def check_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🌐 正在查询网络信息...")
    try:
        # 1. 获取内网 IP (优化版)
        local_ip = get_real_local_ip()
        
        # 2. 获取公网 IP (使用 curl，带超时)
        # 尝试 ipinfo.io/ip 或 ifconfig.me
        cmd = "curl -s --max-time 5 ifconfig.me"
        try:
            public_ip = subprocess.check_output(cmd, shell=True).decode().strip()
        except subprocess.CalledProcessError:
            public_ip = "查询超时"

        text = (
            f"🌐 **网络概览**\n"
            f"────────────────\n"
            f"🏠 **内网 IP**: `{local_ip}`\n"
            f"   └用于: 局域网 SSH 连接\n\n"
            f"🌍 **公网 IP**: `{public_ip}`\n"
            f"   └用于: 检查 VPN/代理状态"
        )
        await msg.edit_text(text, parse_mode='Markdown')
    except Exception as e:
        await msg.edit_text(f"❌ 查询失败: {e}")

# --- ENHANCED TERMINAL & EXEC ---

async def terminal_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示终端快捷菜单"""
    cwd = context.user_data.get('cwd', os.getcwd())
    
    keyboard = [
        [InlineKeyboardButton("📂 ls -lh", callback_data="cmd:ls -lh"), InlineKeyboardButton("💾 df -h", callback_data="cmd:df -h")],
        [InlineKeyboardButton("🧠 free -m", callback_data="cmd:free -m"), InlineKeyboardButton("⏱ uptime", callback_data="cmd:uptime")],
        [InlineKeyboardButton("🆔 whoami", callback_data="cmd:whoami"), InlineKeyboardButton("🌐 ifconfig", callback_data="cmd:ifconfig")]
    ]
    
    text = (
        f"💻 **终端控制台**\n"
        f"当前目录: `{cwd}`\n\n"
        "👇 **快捷指令** (点击执行):"
    )
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_tool_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理终端快捷菜单点击"""
    query = update.callback_query
    
    if query.data.startswith("cmd:"):
        cmd = query.data.split(":", 1)[1]
        await query.answer(f"执行: {cmd}")
        
        # 使用 exec_command 相同的逻辑执行，保持一致性
        # 这里模拟一个 execute 过程
        cwd = context.user_data.get('cwd', os.getcwd())
        full_cmd = f"cd \"{cwd}\" && {cmd}"
        
        try:
            res = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=10)
            out = (res.stdout + res.stderr)[:4000] or "[无输出]"
            
            # 显示结果并保留键盘，方便再次操作
            await query.edit_message_text(
                f"💻 `{cmd}`\n📂 `{cwd}`\n```\n{out}\n```", 
                parse_mode='Markdown',
                reply_markup=query.message.reply_markup
            )
        except Exception as e:
            await query.edit_message_text(f"❌ 错误: {e}")

async def exec_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    执行 Shell 命令，支持 `cd` 目录切换记忆。
    """
    if not check_admin(update.effective_user.id): return
    
    cmd = " ".join(context.args)
    if not cmd:
        # 如果没有参数，显示帮助或菜单
        await terminal_menu(update, context)
        return
    
    # 1. 处理 cd 命令 (状态保持)
    if cmd.startswith("cd "):
        try:
            target_dir = cmd[3:].strip()
            current_cwd = context.user_data.get('cwd', os.getcwd())
            
            # 处理相对路径
            new_path = os.path.abspath(os.path.join(current_cwd, target_dir))
            
            if os.path.isdir(new_path):
                context.user_data['cwd'] = new_path
                await update.message.reply_text(f"📂 目录已切换至:\n`{new_path}`", parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❌ 目录不存在: `{new_path}`", parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ 错误: {e}")
        return

    # 2. 执行普通命令 (使用当前 cwd)
    cwd = context.user_data.get('cwd', os.getcwd())
    await update.message.reply_text(f"💻 执行: `{cmd}`\n📂 CWD: `{cwd}`", parse_mode='Markdown')
    
    try:
        # 组合 cd 和用户命令，确保在正确目录执行
        full_cmd = f"cd \"{cwd}\" && {cmd}"
        
        res = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=15)
        out = (res.stdout + res.stderr)[:4000] or "[无输出]"
        await update.message.reply_text(f"```\n{out}\n```", parse_mode='Markdown')
    except subprocess.TimeoutExpired:
        await update.message.reply_text("❌ 命令执行超时 (15s)")