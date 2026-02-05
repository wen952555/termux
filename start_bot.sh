#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

BOT_FILE="bot.py"
PM2_NAME="termux-bot"

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
    
    # 简单检查是否安装了 telegram 库，如果没有则安装
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

# --- 操作函数 ---

start_bot() {
    echo -e "${GREEN}=== Termux Telegram Bot 启动程序 ===${NC}"
    check_termux_api
    check_python
    check_pm2

    # 检查 PM2 状态
    if pm2 describe $PM2_NAME > /dev/null 2>&1; then
        echo -e "${BLUE}Bot 已经在运行，执行重启以应用更改...${NC}"
        pm2 restart $PM2_NAME
    else
        echo -e "${GREEN}正在启动 Bot 守护进程...${NC}"
        pm2 start $BOT_FILE --name $PM2_NAME --interpreter python
        pm2 save
    fi
    echo -e "${GREEN}✅ Bot 已在后台运行！${NC}"
    echo "使用 './start_bot.sh log' 查看实时日志"
}

stop_bot() {
    pm2 stop $PM2_NAME
    echo -e "${YELLOW}Bot 已停止。${NC}"
}

view_log() {
    echo -e "${BLUE}正在连接日志 (Ctrl+C 退出)...${NC}"
    pm2 log $PM2_NAME
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

# 读取第一个参数，默认为 start
ACTION=${1:-start}

case "$ACTION" in
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    restart)
        start_bot
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
        echo "  start   (默认) 检查环境并启动/重启 Bot"
        echo "  stop    停止 Bot"
        echo "  log     查看日志"
        echo "  update  强制拉取最新代码并重启"
        ;;
    *)
        # 如果参数不匹配，尝试直接传递给 pm2 或者报错，这里直接报错比较安全
        echo -e "${RED}未知命令: $ACTION${NC}"
        echo "请使用 './start_bot.sh help' 查看帮助"
        exit 1
        ;;
esac