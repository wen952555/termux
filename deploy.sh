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
echo -e "${YELLOW}[4/4] 正在启动服务...${NC}"
echo "启动后请在浏览器访问显示的 Local 地址 (通常是 http://localhost:5173)"
echo "按 Ctrl + C 停止服务"
echo "-----------------------------------"

npm run dev -- --host
