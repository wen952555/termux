#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

BOT_FILE="bot.py"
PM2_NAME="termux-bot"
TUNNEL_NAME="cloudflared"

echo -e "${GREEN}=== Termux 环境自动修复与启动 ===${NC}"

# --- 1. 基础依赖修复 ---

check_packages() {
    echo -e "${YELLOW}[1/4] 检查系统组件...${NC}"
    
    # 自动更新源 (修复找不到包的问题)
    if ! command -v pkg &> /dev/null; then
        echo -e "${RED}严重错误: pkg 命令丢失，您的 Termux 环境可能已损坏。${NC}"
        exit 1
    fi

    # 检查 termux-api
    if ! command -v termux-camera-record &> /dev/null; then
        echo -e "${YELLOW}>> 检测到 termux-api 丢失，正在重装...${NC}"
        pkg update -y
        pkg install termux-api -y
    fi

    # 检查 Python
    if ! command -v python &> /dev/null; then
        echo -e "${YELLOW}>> 正在安装 Python...${NC}"
        pkg install python -y
    fi
    
    # 检查 Python 库
    if ! python -c "import telegram" &> /dev/null; then
        echo -e "${YELLOW}>> 恢复 Python 依赖库...${NC}"
        pip install -r requirements.txt
    fi

    # 检查 Node.js / PM2
    if ! command -v pm2 &> /dev/null; then
        echo -e "${YELLOW}>> 正在安装进程管理器 (PM2)...${NC}"
        if ! command -v npm &> /dev/null; then
             pkg install nodejs -y
        fi
        npm install -g pm2
    fi
}

# --- 2. Cloudflare 隧道修复 ---

check_cloudflared() {
    echo -e "${YELLOW}[2/4] 检查 Cloudflare 隧道...${NC}"
    
    if [ ! -f "./cloudflared" ]; then
        echo -e "${YELLOW}>> 未找到 cloudflared，正在下载...${NC}"
        ARCH=$(uname -m)
        case $ARCH in
            aarch64) CF_ARCH="arm64" ;;
            arm*) CF_ARCH="arm" ;;
            x86_64) CF_ARCH="amd64" ;;
            *) echo -e "${RED}不支持的架构: $ARCH${NC}"; return ;;
        esac
        
        echo "下载架构: $CF_ARCH"
        curl -L --output cloudflared "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-android-$CF_ARCH"
        chmod +x cloudflared
        echo -e "${GREEN}cloudflared 下载完成${NC}"
    else
        echo -e "${GREEN}cloudflared 已存在${NC}"
    fi
}

# --- 3. 启动逻辑 ---

start_tunnel() {
    local TOKEN=$1
    if [ -z "$TOKEN" ]; then
        echo -e "${YELLOW}提示: 未提供 Tunnel Token，跳过隧道启动。${NC}"
        echo "用法: ./start_bot.sh tunnel <你的Token>"
        return
    fi

    echo -e "${YELLOW}[3/4] 启动 Cloudflare 隧道...${NC}"
    # 先停止旧的
    pkill -f cloudflared > /dev/null 2>&1
    
    # 后台启动
    nohup ./cloudflared tunnel run --token $TOKEN > cloudflared.log 2>&1 &
    echo -e "${GREEN}✅ 隧道已在后台启动 (日志: cloudflared.log)${NC}"
}

start_bot() {
    echo -e "${YELLOW}[4/4] 启动 Bot 进程...${NC}"

    # 停止旧进程防止冲突
    pm2 delete $PM2_NAME > /dev/null 2>&1

    # 启动新进程
    pm2 start $BOT_FILE --name $PM2_NAME --interpreter python --no-autorestart
    pm2 save
    
    echo -e "${GREEN}==============================${NC}"
    echo -e "${GREEN}✅ 所有服务已恢复！${NC}"
    echo -e "${GREEN}==============================${NC}"
    echo -e "📊 查看 Bot 日志: ./start_bot.sh log"
    echo -e "🐛 调试: 如果依然报错，请运行 pkg update 刷新源"
}

# --- 主菜单 ---

ACTION=${1:-start}
TOKEN=$2

case "$ACTION" in
    start)
        check_packages
        check_cloudflared
        start_bot
        ;;
    tunnel)
        check_packages
        check_cloudflared
        start_tunnel $TOKEN
        start_bot
        ;;
    log|logs)
        pm2 log $PM2_NAME
        ;;
    stop)
        pm2 stop $PM2_NAME
        pkill -f cloudflared
        echo "已停止所有服务"
        ;;
    *)
        echo "用法:"
        echo "  ./start_bot.sh start             # 仅启动 Bot (修复环境)"
        echo "  ./start_bot.sh tunnel <TOKEN>    # 启动 Bot + Cloudflare隧道"
        echo "  ./start_bot.sh log               # 查看日志"
        ;;
esac
