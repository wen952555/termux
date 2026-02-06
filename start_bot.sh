#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# =================配置区域=================
# 您已将 Token 硬编码在此，无需再手动输入命令
FIXED_TOKEN="eyJhIjoiOWFiNmE4YjQ0NGQ3MDA2OWNlMGIyM2RlMzVmNzE2ZDEiLCJ0IjoiNjA3YmM5NTctODdmYi00MTllLWIyZjYtZDIwZjU5ZTZjZjkxIiwicyI6IlpEVmpOVGd6WVRRdE4yRmhaUzAwTURVMExUaGxNR0l0WXpBME9UYzJaR0k0TTJZdyJ9"
# ==========================================

BOT_FILE="bot.py"
PM2_NAME="termux-bot"
TOKEN_FILE=".tunnel_token"
BOOT_DIR="$HOME/.termux/boot"
PREFIX_DIR="/data/data/com.termux/files/usr"

echo -e "${GREEN}=== Termux 自动修复与启动脚本 ===${NC}"

# --- 1. 基础依赖修复 ---

check_packages() {
    echo -e "${YELLOW}[1/5] 检查系统环境...${NC}"
    
    # 确保 pkg 可用
    if ! command -v pkg &> /dev/null; then
        echo -e "${RED}❌ 错误: pkg 命令丢失，环境可能已损坏。${NC}"
        exit 1
    fi

    # 自动修复 termux-api (防止被系统误删)
    if ! command -v termux-camera-record &> /dev/null; then
        echo -e "${YELLOW}>> 正在恢复 termux-api...${NC}"
        pkg update -y -o Dpkg::Options::="--force-confnew"
        pkg install termux-api -y
    fi

    # 检查 Python 环境
    if ! command -v python &> /dev/null; then
        echo -e "${YELLOW}>> 正在安装 Python...${NC}"
        pkg install python -y
    fi
    
    # 检查 Python 依赖
    if ! python -c "import telegram" &> /dev/null; then
        echo -e "${YELLOW}>> 正在安装 Python 库...${NC}"
        pip install -r requirements.txt
    fi

    # 检查 PM2
    if ! command -v pm2 &> /dev/null; then
        echo -e "${YELLOW}>> 正在安装 PM2...${NC}"
        if ! command -v npm &> /dev/null; then
             pkg install nodejs -y
        fi
        npm install -g pm2
    fi
}

# --- 2. Cloudflare 隧道修复 ---

check_cloudflared() {
    echo -e "${YELLOW}[2/5] 检查 Cloudflare 组件...${NC}"
    
    # 检测是否为伪造的/错误的二进制文件 (比如下载了404页面)
    if [ -f "./cloudflared" ]; then
        if head -n 1 ./cloudflared | grep -q "DOCTYPE"; then
            echo -e "${RED}⚠️ 检测到 cloudflared 文件损坏 (可能是下载失败)，正在删除重试...${NC}"
            rm ./cloudflared
        fi
    fi
    
    if [ ! -f "./cloudflared" ]; then
        echo -e "${YELLOW}>> 下载 cloudflared...${NC}"
        ARCH=$(uname -m)
        case $ARCH in
            aarch64) CF_ARCH="arm64" ;;
            armv7*) CF_ARCH="arm" ;;
            arm*) CF_ARCH="arm" ;;
            x86_64) CF_ARCH="amd64" ;;
            *) echo -e "${RED}不支持的架构: $ARCH${NC}"; return ;;
        esac
        
        # 修正：使用标准 Linux 构建 (Termux 兼容)，移除 -android 后缀
        URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-$CF_ARCH"
        echo -e "下载地址: $URL"
        curl -L --output cloudflared "$URL"
        chmod +x cloudflared
    fi
}

# --- 2.5 DNS 强力修复 (关键步骤) ---

fix_dns() {
    echo -e "${YELLOW}[2.5] 修复 DNS 配置...${NC}"
    RESOLV_CONF="$PREFIX_DIR/etc/resolv.conf"
    
    # 备份原 DNS 配置
    if [ ! -f "${RESOLV_CONF}.bak" ]; then
        cp "$RESOLV_CONF" "${RESOLV_CONF}.bak" 2>/dev/null
    fi

    # 强制写入 Google 和 Cloudflare 的 IPv4 DNS
    # 解决 [::1]:53 connection refused 问题
    echo "nameserver 8.8.8.8" > "$RESOLV_CONF"
    echo "nameserver 1.1.1.1" >> "$RESOLV_CONF"
    echo -e "${GREEN}✅ DNS 已重置为 8.8.8.8 (解决 IPv6 连接报错)${NC}"
}

# --- 3. 启动隧道 ---

start_tunnel() {
    # 智能提取: 允许用户粘贴包含 "sudo cloudflared..." 的整段命令，这里只提取 Token
    local RAW_ARGS="$*"
    # 正则提取 eyJ 开头的长字符串 (Cloudflare Token 特征)
    local EXTRACTED_TOKEN=$(echo "$RAW_ARGS" | grep -oE 'ey[A-Za-z0-9\-_=]{50,}' | head -n 1)

    # 1. 确定 Token 优先级: 提取的 > 参数 > 文件 > 硬编码
    TOKEN=""
    
    if [ -n "$EXTRACTED_TOKEN" ]; then
        TOKEN="$EXTRACTED_TOKEN"
        echo "$TOKEN" > "$TOKEN_FILE" # 更新本地缓存
        echo -e "${GREEN}✅ 已识别并更新 Tunnel Token${NC}"
    elif [ -f "$TOKEN_FILE" ]; then
        TOKEN=$(cat "$TOKEN_FILE")
    fi

    # 如果上述都没找到，使用硬编码的
    if [ -z "$TOKEN" ] && [ -n "$FIXED_TOKEN" ]; then
        TOKEN="$FIXED_TOKEN"
        echo -e "${GREEN}✅ 使用脚本内置 Token${NC}"
    fi

    # 3. 检查 Token 是否存在
    if [ -z "$TOKEN" ]; then
        echo -e "${RED}❌ 错误: 未找到 Tunnel Token。${NC}"
        echo -e "请运行: ./start_bot.sh tunnel <你的Token>"
        return
    fi

    echo -e "${YELLOW}[3/5] 启动 Cloudflare 隧道...${NC}"
    
    # 先修复 DNS
    fix_dns

    # 停止旧的进程
    pkill -f cloudflared > /dev/null 2>&1
    
    # 后台启动
    # --no-autoupdate: 禁止自动更新
    # --edge-ip-version 4: 强制使用 IPv4 (解决部分 Android DNS 解析到 ::1 的问题)
    # --protocol http2: 使用 HTTP2 协议 (比 QUIC 更稳定)
    nohup ./cloudflared tunnel --no-autoupdate --edge-ip-version 4 --protocol http2 run --token $TOKEN > cloudflared.log 2>&1 &
    
    sleep 5
    if pgrep -f cloudflared > /dev/null; then
        echo -e "${GREEN}✅ 隧道运行中 (Cloudflare Tunnel)${NC}"
    else
        echo -e "${RED}⚠️ 隧道启动失败，请检查 Token 是否正确${NC}"
        echo -e "⬇️ 错误日志 (最后 10 行):"
        tail -n 10 cloudflared.log
        echo -e "⬆️ 提示: DNS 已重置，如果依然失败，请检查 Token 是否已失效 (重新生成)。"
    fi
}

# --- 4. 配置开机自启 (无人值守模式) ---

setup_autostart() {
    echo -e "${YELLOW}[配置开机自启]...${NC}"
    
    # 1. 检查是否安装了 Termux:Boot 应用
    if [ ! -d "$BOOT_DIR" ]; then
        echo -e "${RED}❌ 未检测到 Termux:Boot 目录 ($BOOT_DIR)${NC}"
        echo -e "请务必先安装 'Termux:Boot' APP (可在 F-Droid 或 Google Play 下载)"
        echo -e "安装后，请运行一次 Termux:Boot 应用以初始化。"
        mkdir -p "$BOOT_DIR"
    fi

    # 2. 获取当前脚本绝对路径
    PROJECT_DIR=$(pwd)
    BOOT_SCRIPT="$BOOT_DIR/start_bot_service"

    echo -e "正在生成启动脚本: $BOOT_SCRIPT"

    # 3. 写入启动脚本
    cat > "$BOOT_SCRIPT" <<EOF
#!/data/data/com.termux/files/usr/bin/sh
# Termux Boot Script generated by BotGen AI

# 1. 申请唤醒锁，防止手机休眠断网
termux-wake-lock

# 2. 等待网络连接 (给 wifi 连接一点时间)
sleep 10

# 3. 进入项目目录并启动
cd "$PROJECT_DIR"
./start_bot.sh start >> boot.log 2>&1
EOF

    chmod +x "$BOOT_SCRIPT"
    
    echo -e "${GREEN}✅ 开机启动脚本已配置！${NC}"
    echo -e "⚠️ 重要提示："
    echo -e "1. 请确保手机已安装 **Termux:Boot** 应用。"
    echo -e "2. 请在手机设置中，将 Termux 和 Termux:Boot 的**电池优化**设置为'无限制'。"
    echo -e "3. 建议在该脚本最后也配置 SSH 启动，以防 Bot 挂掉。"
}

# --- 5. 启动 Bot ---

start_bot() {
    echo -e "${YELLOW}[4/5] 启动 Bot...${NC}"
    
    # 尝试申请唤醒锁
    if command -v termux-wake-lock &> /dev/null; then
        termux-wake-lock
        echo -e "已申请 Wake Lock (防止休眠)"
    fi

    pm2 delete $PM2_NAME > /dev/null 2>&1
    pm2 start $BOT_FILE --name $PM2_NAME --interpreter python --no-autorestart
    pm2 save
    
    echo -e "\n${GREEN}🎉 系统运行中！${NC}"
    echo -e "-----------------------------------"
    echo -e "📡 远程 SSH 建议: 配合 Cloudflare Tunnel 配置 SSH 访问"
    echo -e "⚙️ 开机自启: ./start_bot.sh autostart"
}

# --- 菜单逻辑 ---

# 提取第一个参数作为动作，如果没有则默认为 start
ACTION=${1:-start}

# 将第一个参数移出，$@ 现在包含剩余的所有参数 (可能是 Token)
shift 2>/dev/null || true

case "$ACTION" in
    start)
        check_packages
        check_cloudflared
        # 只要本地有缓存 OR 脚本里有硬编码 Token，就自动启动隧道
        if [ -f "$TOKEN_FILE" ] || [ -n "$FIXED_TOKEN" ]; then
            start_tunnel
        else
            echo -e "${YELLOW}提示: 未配置隧道。如需外网访问请使用 ./start_bot.sh tunnel <TOKEN>${NC}"
        fi
        start_bot
        ;;
    tunnel)
        check_packages
        check_cloudflared
        # 将剩余所有参数传给 start_tunnel 以支持智能提取
        start_tunnel "$@"
        start_bot
        ;;
    autostart)
        setup_autostart
        ;;
    log|logs)
        pm2 log $PM2_NAME
        ;;
    stop)
        pm2 stop $PM2_NAME
        pkill -f cloudflared
        # 释放唤醒锁
        if command -v termux-wake-unlock &> /dev/null; then
            termux-wake-unlock
        fi
        echo "已停止所有服务"
        ;;
    *)
        echo "使用方法:"
        echo "  ./start_bot.sh                  # 一键启动 (自动读取内置Token)"
        echo "  ./start_bot.sh tunnel <TOKEN>   # 手动更新 Token"
        echo "  ./start_bot.sh autostart        # 配置开机自启"
        echo "  ./start_bot.sh log              # 查看日志"
        ;;
esac
