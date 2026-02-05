#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}=== Termux Telegram Bot 启动器 ===${NC}"

# 1. 检查 Python
if ! command -v python &> /dev/null; then
    echo -e "${BLUE}未检测到 Python，正在安装...${NC}"
    # 检测是 Termux (pkg) 还是 Ubuntu (apt)
    if command -v pkg &> /dev/null; then
        pkg update && pkg install python -y
    elif command -v apt &> /dev/null; then
        apt update && apt install python3 python3-pip -y
        # 确保 python 命令指向 python3
        if ! command -v python &> /dev/null; then
            ln -s $(which python3) /usr/bin/python
        fi
    else
        echo "无法自动安装 Python，请手动安装。"
        exit 1
    fi
fi

# 2. 安装依赖
echo -e "${BLUE}正在检查依赖库...${NC}"
pip install -r requirements.txt

# 3. 运行 Bot
echo -e "${GREEN}正在启动 Bot...${NC}"
echo "提示：按 Ctrl + C 可以停止运行"
echo "--------------------------------"

python bot.py
