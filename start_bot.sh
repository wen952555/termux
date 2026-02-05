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
TERMUX_BIN_PATH="/data/data/com.termux/files/usr/bin"

# --- 依赖检查函数 ---

check_termux_api() {
    echo -e "${BLUE}>> 检查 Termux API 组件...${NC}"
    
    # 检查核心二进制文件是否存在 (绝对路径检查，适用于原生和 Ubuntu 环境)
    if [ ! -f "$TERMUX_BIN_PATH/termux-camera-record" ]; then
        echo -e "${YELLOW}⚠️  警告: 未找到 termux-api 命令行工具。${NC}"
        echo -e "${YELLOW}   这会导致拍照、录像功能不可用。${NC}"
        
        # 尝试自动安装
        INSTALLED=0
        
        # 1. 尝试原生 pkg
        if command -v pkg &> /dev/null; then
            echo -e "   正在使用 pkg 安装..."
            pkg update -y >/dev/null 2>&1 && pkg install termux-api -y >/dev/null 2>&1
            if [ $? -eq 0 ]; then INSTALLED=1; fi
        
        # 2. 尝试调用宿主机 pkg (如果在 Ubuntu 容器中)
        elif [ -x "$TERMUX_BIN_PATH/pkg" ]; then
            echo -e "   检测到 Ubuntu/PRoot 环境，尝试调用宿主机 pkg..."
            # 必须设置 LD_LIBRARY_PATH 以避免库冲突，或者直接调用
            # 这里简单尝试直接调用
            "$TERMUX_BIN_PATH/pkg" install termux-api -y >/dev/null 2>&1
            if [ $? -eq 0 ]; then INSTALLED=1; fi
        fi

        if [ $INSTALLED -eq 1 ]; then
             echo -e "${GREEN}✅ termux-api 安装成功！${NC}"
        else
             echo -e "${RED}❌ 无法自动安装 termux-api。${NC}"
             echo -e "${YELLOW}请手动修复: ${NC}"
             echo -e "1. 打开 Termux 原生终端 (退出 Ubuntu)"
             echo -e "2. 运行: ${GREEN}pkg install termux-api${NC}"
             echo -e "3. 确保已安装 Google Play 上的 'Termux:API' 应用"
             echo ""
        fi
    else
        echo -e "${GREEN}✅ 检测到 Termux API 工具${NC}"
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

# 启动 Tunnel 的核心逻辑
# 参数 $1: Token (可选)
# 参数 $2: 模式 (auto: 自动模式，不交互)
run_tunnel_logic() {
    INPUT_TOKEN="$1"
    MODE="$2"
    TOKEN_FILE=".tunnel_token"
    
    check_cloudflared
    check_pm2

    # 1. 确定 Token
    TOKEN=""
    # 如果传入了 Token 且不是 "auto" (处理脚本参数错位情况)
    if [ -n "$INPUT_TOKEN" ] && [ "$INPUT_TOKEN" != "auto" ]; then
        TOKEN="$INPUT_TOKEN"
        echo "$TOKEN" > "$TOKEN_FILE"
    fi

    # 如果没传入，尝试读取文件
    if [ -z "$TOKEN" ] && [ -f "$TOKEN_FILE" ]; then
        TOKEN=$(cat "$TOKEN_FILE")
    fi

    # 如果还是没有，且不是自动模式，则询问
    if [ -z "$TOKEN" ]; then
        if [ "$MODE" == "auto" ]; then
            return 0 # 自动模式下如果没有 Token，直接跳过
        fi
        
        echo -e "${GREEN}=== Cloudflare Tunnel 配置 ===${NC}"
        echo -e "${YELLOW}请输入您的 Cloudflare Tunnel Token:${NC}"
        echo "(在 Cloudflare Dashboard > Zero Trust > Access > Tunnels 中获取)"
        read -r USER_TOKEN
        if [ -n "$USER_TOKEN" ]; then
            TOKEN="$USER_TOKEN"
            echo "$TOKEN" > "$TOKEN_FILE"
        else
            echo -e "${RED}错误: 未提供 Token，无法启动隧道。${NC}"
            return 1
        fi
    fi

    # 2. 启动 PM2 进程
    CMD="cloudflared"
    if [ -f "./cloudflared" ] && ! command -v cloudflared &> /dev/null; then
        CMD="./cloudflared"
    fi

    # 检查是否已经在运行
    if pm2 describe $TUNNEL_NAME > /dev/null 2>&1; then
        # 获取当前运行的参数，检查是否需要更新 Token? 
        # 简化起见，如果已运行，我们重启它以确保应用最新配置
        pm2 restart $TUNNEL_NAME
    else
        pm2 start "$CMD" --name $TUNNEL_NAME -- tunnel run --token "$TOKEN"
    fi
    
    if [ "$MODE" != "auto" ]; then
        echo -e "${GREEN}✅ Cloudflare Tunnel 已启动!${NC}"
        echo -e "请确保后台指向: ${YELLOW}http://localhost:5173${NC}"
    fi
}


start_bot() {
    echo -e "${GREEN}=== Termux Telegram Bot 启动程序 ===${NC}"
    check_termux_api
    check_python
    check_pm2

    # 1. 启动 Bot
    if pm2 describe $PM2_NAME > /dev/null 2>&1; then
        echo -e "${BLUE}Bot 已经在运行，正在重启...${NC}"
        pm2 restart $PM2_NAME
    else
        echo -e "${GREEN}正在启动 Bot 守护进程...${NC}"
        pm2 start $BOT_FILE --name $PM2_NAME --interpreter python
    fi

    # 2. 自动启动 Tunnel (如果已配置)
    if [ -f ".tunnel_token" ]; then
        echo -e "${BLUE}>> 检测到隧道配置，正在启动 Cloudflare Tunnel...${NC}"
        run_tunnel_logic "" "auto"
    fi

    pm2 save
    echo -e "${GREEN}✅ 所有服务已在后台运行！${NC}"
    echo "使用 './start_bot.sh log' 查看日志"
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
        # $2 是 Token
        run_tunnel_logic "$2" "manual"
        pm2 save
        ;;
    stop)
        stop_all
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
        echo "  start       启动/重启 Bot (及隧道)"
        echo "  tunnel      配置并启动 Cloudflare 隧道"
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
