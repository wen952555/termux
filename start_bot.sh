#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

BOT_FILE="bot.py"
PM2_NAME="termux-bot"
TUNNEL_NAME="cloudflared"

# --- 依赖检查函数 ---

check_termux_api() {
    # 仅在原生 Termux 环境下检查
    if command -v pkg &> /dev/null && [ -d "/data/data/com.termux" ]; then
        if ! command -v termux-battery-status &> /dev/null; then
            echo -e "${YELLOW}>> 正在安装 termux-api...${NC}"
            pkg update -y > /dev/null 2>&1 && pkg install termux-api -y > /dev/null 2>&1
        fi
    fi
}

check_python() {
    if ! command -v python &> /dev/null; then
        echo -e "${YELLOW}>> 正在安装 Python...${NC}"
        if command -v pkg &> /dev/null; then
            pkg install python -y > /dev/null 2>&1
        else
            sudo apt update && sudo apt install python3 python3-pip -y
            # 尝试建立软链接
            [ ! -f /usr/bin/python ] && sudo ln -s /usr/bin/python3 /usr/bin/python
        fi
    fi
    
    if ! python -c "import telegram" &> /dev/null; then
        echo -e "${BLUE}>> 安装 Python 依赖...${NC}"
        pip install -r requirements.txt
    fi
}

check_pm2() {
    if ! command -v pm2 &> /dev/null; then
        echo -e "${YELLOW}>> 正在安装进程守护工具 PM2...${NC}"
        if ! command -v npm &> /dev/null; then
             echo "   安装 Node.js..."
             if command -v pkg &> /dev/null; then
                pkg install nodejs -y > /dev/null 2>&1
             else
                sudo apt install nodejs npm -y
             fi
        fi
        npm install -g pm2
    fi
}

check_cloudflared() {
    if ! command -v cloudflared &> /dev/null; then
        echo -e "${YELLOW}>> 未检测到 cloudflared，正在下载...${NC}"
        
        # 检测架构
        ARCH=$(uname -m)
        case $ARCH in
            aarch64|arm64) CF_ARCH="arm64" ;;
            armv7l|arm)    CF_ARCH="arm" ;;
            x86_64|amd64)  CF_ARCH="amd64" ;;
            *)             echo -e "${RED}不支持的架构: $ARCH${NC}"; return 1 ;;
        esac

        DOWNLOAD_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${CF_ARCH}"
        echo "   下载地址: $DOWNLOAD_URL"
        
        curl -L -o cloudflared "$DOWNLOAD_URL"
        
        if [ ! -f "cloudflared" ]; then
            echo -e "${RED}下载失败，请检查网络连接。${NC}"
            return 1
        fi

        chmod +x cloudflared
        
        # 尝试移动到 PATH，如果失败则留在当前目录
        if [ -w "$PREFIX/bin" ]; then
            mv cloudflared "$PREFIX/bin/"
            echo -e "${GREEN}cloudflared 已安装到 \$PREFIX/bin${NC}"
        else
            echo -e "${YELLOW}无法写入系统路径，将使用当前目录下的 cloudflared${NC}"
            export PATH="$PATH:$(pwd)"
        fi
    fi
}

# --- 操作函数 ---

start_bot() {
    echo -e "${GREEN}=== Termux Telegram Bot 启动程序 ===${NC}"
    check_termux_api
    check_python
    check_pm2

    if pm2 describe $PM2_NAME > /dev/null 2>&1; then
        echo -e "${BLUE}Bot 已经在运行，正在重启...${NC}"
        pm2 restart $PM2_NAME
    else
        echo -e "${GREEN}正在启动 Bot 守护进程...${NC}"
        pm2 start $BOT_FILE --name $PM2_NAME --interpreter python
        pm2 save
    fi
    echo -e "${GREEN}✅ Bot 已在后台运行！${NC}"
    echo "使用 './start_bot.sh log' 查看日志"
}

start_tunnel() {
    echo -e "${GREEN}=== Cloudflare Tunnel 配置 ===${NC}"
    check_cloudflared
    check_pm2

    # 获取 Token
    TOKEN="$1"
    TOKEN_FILE=".tunnel_token"

    if [ -z "$TOKEN" ]; then
        if [ -f "$TOKEN_FILE" ]; then
            TOKEN=$(cat "$TOKEN_FILE")
            echo -e "${BLUE}已从缓存读取 Token。${NC}"
        fi
    fi

    if [ -z "$TOKEN" ]; then
        echo -e "${YELLOW}请输入您的 Cloudflare Tunnel Token:${NC}"
        echo "(在 Cloudflare Dashboard > Zero Trust > Access > Tunnels 中获取)"
        read -r INPUT_TOKEN
        if [ -n "$INPUT_TOKEN" ]; then
            TOKEN="$INPUT_TOKEN"
            echo "$TOKEN" > "$TOKEN_FILE"
        else
            echo -e "${RED}错误: 未提供 Token，无法启动隧道。${NC}"
            return 1
        fi
    fi

    echo -e "${GREEN}正在启动 Cloudflare Tunnel...${NC}"
    
    # 确定 cloudflared 命令路径
    CMD="cloudflared"
    if [ -f "./cloudflared" ] && ! command -v cloudflared &> /dev/null; then
        CMD="./cloudflared"
    fi

    # 清理旧进程
    pm2 delete $TUNNEL_NAME >/dev/null 2>&1

    # 启动新进程
    # 注意：Web 服务默认运行在 localhost:5173
    # Cloudflare 后台需要将 Public Hostname 指向 http://localhost:5173
    pm2 start "$CMD" --name $TUNNEL_NAME -- tunnel run --token "$TOKEN"
    pm2 save

    echo -e "${GREEN}✅ 隧道已启动!${NC}"
    echo -e "请确保您在 Cloudflare 后台将隧道指向: ${YELLOW}http://localhost:5173${NC}"
}

stop_all() {
    pm2 stop $PM2_NAME >/dev/null 2>&1
    pm2 stop $TUNNEL_NAME >/dev/null 2>&1
    echo -e "${YELLOW}所有服务已停止。${NC}"
}

view_log() {
    echo -e "${BLUE}正在连接日志 (Ctrl+C 退出)...${NC}"
    pm2 log
}

force_update() {
    echo -e "${YELLOW}正在强制更新代码...${NC}"
    git fetch --all
    git reset --hard origin/main
    git pull
    chmod +x start_bot.sh
    echo -e "${GREEN}更新完成，正在重启 Bot...${NC}"
    start_bot
}

# --- 主逻辑 ---

ACTION=${1:-start}

case "$ACTION" in
    start)
        start_bot
        ;;
    tunnel)
        start_tunnel "$2"
        ;;
    stop)
        stop_all
        ;;
    restart)
        start_bot
        start_tunnel
        ;;
    log|logs)
        view_log
        ;;
    update)
        force_update
        ;;
    help)
        echo "用法: ./start_bot.sh [命令]"
        echo "命令列表:"
        echo "  start       启动/重启 Telegram Bot"
        echo "  tunnel      启动/配置 Cloudflare 内网穿透"
        echo "  stop        停止所有服务"
        echo "  log         查看实时日志"
        echo "  update      强制更新代码"
        ;;
    *)
        echo -e "${RED}未知命令: $ACTION${NC}"
        echo "请使用 './start_bot.sh help' 查看帮助"
        exit 1
        ;;
esac
