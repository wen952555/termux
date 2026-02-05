# Termux BotGen AI

这是一个基于 React 和 Google Gemini AI 的 Web 应用，专为 Android Termux 用户设计。它可以帮助你生成用于管理 Termux 和 Ubuntu (PRoot) 环境的 Telegram Bot Python 脚本。

## 功能

- **AI 代码生成**: 根据你的需求生成 Python Telegram Bot 代码。
- **Termux 优化**: 针对 Termux:API 和 Android 环境优化的脚本逻辑。
- **环境适配**: 支持 Native Termux 和 Ubuntu (PRoot) 环境的配置建议。

## 部署指南 (Termux)

### 1. 准备工作

确保你的 Termux 已经更新：

```bash
pkg update && pkg upgrade
pkg install git
```

### 2. 克隆与安装

```bash
# 1. 克隆仓库
git clone https://github.com/你的用户名/仓库名.git
cd 仓库名

# 2. 运行部署脚本 (推荐)
chmod +x deploy.sh
./deploy.sh
```

### 3. 手动安装 (如果不使用脚本)

如果你更喜欢手动操作：

```bash
# 安装 Node.js
pkg install nodejs

# 安装依赖
npm install

# 设置 API Key
# 创建一个 .env 文件，并写入 VITE_API_KEY=你的API_KEY
echo "VITE_API_KEY=AIzaSyxxxxxxxxxxxxxxx" > .env

# 启动
npm run dev
```

启动后，打开手机浏览器访问 Termux 显示的地址（通常是 `http://localhost:5173`）。

## 关于 API Key

本项目需要 Google Gemini API Key 才能工作。
请前往 [Google AI Studio](https://aistudio.google.com/app/apikey) 免费申请。
