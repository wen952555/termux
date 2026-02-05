#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

BOT_FILE="bot.py"
PM2_NAME="termux-bot"

echo -e "${GREEN}=== Termux Telegram Bot 管理面板 ===${NC}"

# 函数: 检查并安装 Python
check_python() {
    if ! command -v python &> /dev/null; then
        echo -e "${YELLOW}未检测到 Python，正在安装...${NC}"
        if command -v pkg &> /dev/null; then
            pkg update && pkg install python -y
        elif command -v apt &> /dev/null; then
            sudo apt update && sudo apt install python3 python3-pip -y
            if ! command -v python &> /dev/null; then
                sudo ln -s $(which python3) /usr/bin/python
            fi
        fi
    fi
    echo -e "${BLUE}正在检查 Python 依赖...${NC}"
    pip install -r requirements.txt
}

# 函数: 检查并安装 Node.js 和 PM2
check_pm2() {
    if ! command -v pm2 &> /dev/null; then
        echo -e "${YELLOW}未检测到 PM2，准备安装...${NC}"
        
        # 检查 Node.js
        if ! command -v npm &> /dev/null; then
            echo -e "${YELLOW}未检测到 Node.js，正在安装...${NC}"
            if command -v pkg &> /dev/null; then
                pkg install nodejs -y
            elif command -v apt &> /dev/null; then
                sudo apt update && sudo apt install nodejs npm -y
            else
                echo -e "${RED}无法自动安装 Node.js，请手动安装后重试。${NC}"
                return 1
            fi
        fi
        
        echo -e "${BLUE}正在通过 npm 安装 pm2...${NC}"
        npm install -g pm2
    fi
}

# 函数: 使用 PM2 启动
start_pm2() {
    check_python
    check_pm2
    
    echo -e "${GREEN}正在使用 PM2 启动 Bot...${NC}"
    
    # 检查是否已经运行
    pm2 describe $PM2_NAME > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "Bot 已经在运行，正在重启..."
        pm2 restart $PM2_NAME
    else
        # 启动新的进程
        # 使用 python 解释器启动 bot.py
        pm2 start $BOT_FILE --name $PM2_NAME --interpreter python
    fi
    
    pm2 save
    echo -e "${GREEN}Bot 已在后台启动！${NC}"
    echo "使用 'pm2 log $PM2_NAME' 查看日志。"
}

# 函数: 停止 PM2
stop_pm2() {
    pm2 stop $PM2_NAME
    echo -e "${YELLOW}Bot 已停止。${NC}"
}

# 函数: 查看日志
view_logs() {
    echo -e "${BLUE}正在打开日志 (按 Ctrl+C 退出)...${NC}"
    pm2 log $PM2_NAME
}

# 主菜单
echo "请选择操作:"
echo "1) 🚀 使用 PM2 启动/重启 (后台运行，推荐)"
echo "2) 📝 查看 PM2 日志"
echo "3) 🛑 停止 PM2 服务"
echo "4) 🐛 前台直接运行 (调试用)"
echo "5) 🚪 退出"

read -p "请输入选项 [1-5]: " choice

case $choice in
    1)
        start_pm2
        ;;
    2)
        view_logs
        ;;
    3)
        stop_pm2
        ;;
    4)
        check_python
        echo -e "${GREEN}正在前台启动 Bot (按 Ctrl+C 停止)...${NC}"
        python $BOT_FILE
        ;;
    5)
        exit 0
        ;;
    *)
        echo "无效选项"
        ;;
esac
