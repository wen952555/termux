# Termux Telegram Bot

专为 Termux 和 Ubuntu (PRoot/Chroot) 环境设计的管理机器人。

## 🚀 极速部署 (Termux 原生)

如果你是第一次运行，或者遇到了 git 错误，直接复制下面的命令运行：

```bash
# 强制更新代码并修复冲突
git fetch --all && git reset --hard origin/main && git pull && chmod +x start_bot.sh

# 启动管理菜单
./start_bot.sh
```

在菜单中选择 **1** 即可全自动安装依赖并后台运行。

## 功能特性

*   **跨环境兼容**: 自动检测 Native Termux 或 Ubuntu PRoot 环境。
*   **PM2 进程守护**: 掉线自动重启，后台稳定运行。
*   **服务探测**: 自动检测 SSH, HTTP, MySQL 等常用服务端口。
*   **进程监控**: 查看 Top 5 CPU 占用进程。
*   **Termux API 集成**: 支持电池查询、拍照等功能。

## 手动安装依赖

如果脚本自动安装失败，可以尝试手动运行：

```bash
# Ubuntu
apt update && apt install python3 python3-pip nodejs npm -y
pip3 install python-telegram-bot psutil
npm install -g pm2

# Termux Native
pkg update && pkg install python nodejs -y
pip install python-telegram-bot psutil
npm install -g pm2
```
