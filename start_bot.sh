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
    # 直接检查命令是否存在
    if ! command -v termux-camera-record &> /dev/null; then
        echo -e "${YELLOW}>> 未找到 termux-api，正在安装...${NC}"
        # 移除 > /dev/null 以便看到报错信息
        pkg update -y && pkg install termux-api -y
        
        if [ $? -eq 0 ]; then
             echo -e "${GREEN}✅ termux-api 安装成功！${NC}"
        else
             echo -e "${RED}❌ 安装失败。请手动运行: pkg install termux-api${NC}"
        fi
    fi
}

check_python() {
    if ! command -v python &> /dev/null; then
        echo -e "${YELLOW}>> 正在安装 Python...${NC}"
        pkg install python -y
    fi
    
    if ! python -c "import telegram" &> /dev/null; then
        echo -e "${BLUE}>> 安装 Python 依赖...${NC}"
        pip install -r requirements.txt
    fi
}

check_pm2() {
    if ! command -v pm2 &> /dev/null; then
        echo -e "${YELLOW}>> 正在安装 PM2...${NC}"
        if ! command -v npm &> /dev/null; then
             pkg install nodejs -y
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
        
        if [ -w "$PREFIX/bin" ]; then
            mv cloudflared "$PREFIX/bin/"
        else
            export PATH="$PATH:$(pwd)"
        fi
    fi
}

# --- 操作函数 ---

run_tunnel_logic() {
    INPUT_TOKEN="$1"
    MODE="$2"
    TOKEN_FILE=".tunnel_token"
    
    check_cloudflared
    check_pm2

    TOKEN=""
    if [ -n "$INPUT_TOKEN" ] && [ "$INPUT_TOKEN" != "auto" ]; then
        TOKEN="$INPUT_TOKEN"
        echo "$TOKEN" > "$TOKEN_FILE"
    fi

    if [ -z "$TOKEN" ] && [ -f "$TOKEN_FILE" ]; then
        TOKEN=$(cat "$TOKEN_FILE")
    fi

    if [ -z "$TOKEN" ]; then
        if [ "$MODE" == "auto" ]; then return 0; fi
        echo -e "${YELLOW}请输入您的 Cloudflare Tunnel Token:${NC}"
        read -r USER_TOKEN
        if [ -n "$USER_TOKEN" ]; then
            TOKEN="$USER_TOKEN"
            echo "$TOKEN" > "$TOKEN_FILE"
        else
            echo -e "${RED}错误: 未提供 Token。${NC}"
            return 1
        fi
    fi

    CMD="cloudflared"
    if [ -f "./cloudflared" ] && ! command -v cloudflared &> /dev/null; then
        CMD="./cloudflared"
    fi

    if pm2 describe $TUNNEL_NAME > /dev/null 2>&1; then
        pm2 restart $TUNNEL_NAME
    else
        pm2 start "$CMD" --name $TUNNEL_NAME -- tunnel run --token "$TOKEN"
    fi
    
    if [ "$MODE" != "auto" ]; then
        echo -e "${GREEN}✅ Cloudflare Tunnel 已启动!${NC}"
    fi
}


start_bot() {
    echo -e "${GREEN}=== Termux Bot 启动 ===${NC}"
    check_termux_api
    check_python
    check_pm2

    if pm2 describe $PM2_NAME > /dev/null 2>&1; then
        echo -e "${BLUE}Bot 正在重启...${NC}"
        pm2 restart $PM2_NAME
    else
        echo -e "${GREEN}启动 Bot...${NC}"
        pm2 start $BOT_FILE --name $PM2_NAME --interpreter python
    fi

    if [ -f ".tunnel_token" ]; then
        run_tunnel_logic "" "auto"
    fi

    pm2 save
    echo -e "${GREEN}✅ 运行中! 使用 './start_bot.sh log' 查看日志${NC}"
}

force_update() {
    echo -e "${YELLOW}更新代码...${NC}"
    git fetch --all
    git reset --hard origin/main
    git pull
    chmod +x start_bot.sh
    start_bot
}

ACTION=${1:-start}

case "$ACTION" in
    start) start_bot ;;
    tunnel) run_tunnel_logic "$2" "manual"; pm2 save ;;
    stop) pm2 stop $PM2_NAME >/dev/null 2>&1; pm2 stop $TUNNEL_NAME >/dev/null 2>&1 ;;
    restart) start_bot ;;
    log|logs) pm2 log ;;
    update) force_update ;;
    *) echo "用法: ./start_bot.sh [start|stop|tunnel|log|update]" ;;
esac
