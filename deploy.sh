#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Termux BotGen AI 部署助手 ===${NC}"

# 1. 检查并安装 Node.js
echo -e "${YELLOW}[1/4] 检查 Node.js 环境...${NC}"
if ! command -v node &> /dev/null; then
    echo "未检测到 Node.js，正在安装..."
    pkg install nodejs -y
else
    echo "Node.js 已安装: $(node -v)"
fi

# 2. 安装依赖
echo -e "${YELLOW}[2/4] 安装项目依赖 (这可能需要几分钟)...${NC}"
if [ ! -d "node_modules" ]; then
    npm install
else
    echo "node_modules 已存在，跳过安装 (如果运行失败请手动运行 npm install)"
fi

# 3. 配置 API Key
echo -e "${YELLOW}[3/4] 配置环境变量...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}未找到配置文件！${NC}"
    echo "请输入你的 Google Gemini API Key (从 aistudio.google.com 获取):"
    read -p "API Key > " USER_API_KEY
    
    if [ -z "$USER_API_KEY" ]; then
        echo -e "${RED}错误: API Key 不能为空。${NC}"
        exit 1
    fi
    
    echo "VITE_API_KEY=$USER_API_KEY" > .env
    echo -e "${GREEN}.env 文件已创建。${NC}"
else
    echo ".env 文件已存在，跳过配置。"
fi

# 4. 启动服务
echo -e "${GREEN}=== 准备就绪 ===${NC}"
echo -e "${YELLOW}[4/4] 正在启动 Web 界面...${NC}"

# 尝试获取局域网 IP
IP_ADDR=$(ifconfig 2>/dev/null | grep -oE 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | awk '{print $2}' | sed 's/addr://')

echo "-----------------------------------"
echo -e "${GREEN}服务已启动！请在同一 Wi-Fi 下的设备访问:${NC}"
if [ -n "$IP_ADDR" ]; then
    for ip in $IP_ADDR; do
        echo -e "👉 http://$ip:5173"
    done
else
    echo -e "👉 http://<你的手机IP>:5173"
fi
echo -e "(本机访问使用: http://localhost:5173)"
echo "-----------------------------------"
echo "按 Ctrl + C 停止 Web 服务 (不会影响 Bot 运行)"

npm run dev -- --host