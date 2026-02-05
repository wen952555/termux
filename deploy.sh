#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Termux 监控仪表盘启动器 ===${NC}"

# 1. 检查并安装 Node.js
echo -e "${YELLOW}[1/3] 检查 Node.js 环境...${NC}"
if ! command -v node &> /dev/null; then
    echo "未检测到 Node.js，正在安装..."
    pkg install nodejs -y
else
    echo "Node.js 已安装: $(node -v)"
fi

# 2. 安装依赖
echo -e "${YELLOW}[2/3] 安装前端依赖...${NC}"
if [ ! -d "node_modules" ]; then
    npm install
else
    echo "node_modules 已存在，跳过安装。"
fi

# 3. 启动服务
echo -e "${GREEN}=== 准备就绪 ===${NC}"
echo -e "${YELLOW}[3/3] 正在启动监控画廊...${NC}"

# 尝试获取局域网 IP
IP_ADDR=$(ifconfig 2>/dev/null | grep -oE 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | awk '{print $2}' | sed 's/addr://')

echo "-----------------------------------"
echo -e "${GREEN}Web 监控台已启动！请访问:${NC}"
if [ -n "$IP_ADDR" ]; then
    for ip in $IP_ADDR; do
        echo -e "👉 http://$ip:5173"
    done
else
    echo -e "👉 http://<你的手机IP>:5173"
fi
echo -e "(本机访问使用: http://localhost:5173)"
echo "-----------------------------------"
echo "提示: 这里可以看到 Bot 拍摄的所有照片和视频。"
echo "按 Ctrl + C 停止 Web 服务 (Bot 会继续运行)"

# 确保 captured_media 目录存在
mkdir -p captured_media

npm run dev -- --host