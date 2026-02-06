#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

BOT_FILE="bot.py"
PM2_NAME="termux-bot"
TUNNEL_NAME="cloudflared"

# --- 依赖检查函数 ---

check_termux_api() {
    echo -e "${YELLOW}>> 检查 Termux API 依赖...${NC}"
    if ! command -v termux-camera-record &> /dev/null; then
        echo -e "${YELLOW}未找到 termux-api 包，正在安装...${NC}"
        pkg update -y
        pkg install termux-api -y
        
        if command -v termux-camera-record &> /dev/null; then
             echo -e "${GREEN}✅ termux-api 安装成功！${NC}"
        else
             echo -e "${RED}❌ 安装失败。请尝试手动运行: pkg install termux-api${NC}"
        fi
    else
        echo -e "${GREEN}✅ termux-api 已安装${NC}"
    fi
}

check_python() {
    if ! command -v python &> /dev/null; then
        echo -e "${YELLOW}>> 正在安装 Python...${NC}"
        pkg install python -y
    fi
    
    if ! python -c "import telegram" &> /dev/null; then
        echo -e "${YELLOW}>> 安装 Python 依赖...${NC}"
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

# --- Cloudflare 逻辑省略，保持原有 ---
# (为了保持文件简洁，这里只列出核心修改部分，实际使用时请保留完整的 Tunnel 逻辑)
# 此处假定 Tunnel 逻辑不变，直接跳到 Start Bot 部分

start_bot() {
    echo -e "${GREEN}=== Termux Bot 启动 ===${NC}"
    check_termux_api
    check_python
    check_pm2

    if pm2 describe $PM2_NAME > /dev/null 2>&1; then
        echo -e "${GREEN}Bot 正在运行，执行重启...${NC}"
        pm2 restart $PM2_NAME
    else
        echo -e "${GREEN}启动 Bot...${NC}"
        pm2 start $BOT_FILE --name $PM2_NAME --interpreter python
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
    # 更新后重新运行 start 以确保依赖被安装
    start_bot
}

ACTION=${1:-start}

case "$ACTION" in
    start) start_bot ;;
    stop) pm2 stop $PM2_NAME >/dev/null 2>&1 ;;
    restart) start_bot ;;
    log|logs) pm2 log ;;
    update) force_update ;;
    *) echo "用法: ./start_bot.sh [start|stop|log|update]" ;;
esac
