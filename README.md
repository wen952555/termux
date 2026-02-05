# Termux Telegram Bot

这是一个专为 Termux 设计的 Telegram 管理机器人，支持 Ubuntu/Proot 环境。

## 功能列表

*   **键盘菜单**: 方便的底部菜单，无需记忆命令。
*   **系统监控**: CPU、内存、磁盘、网络流量、运行时间。
*   **电池监控**: 详细的电量、温度、健康状态 (需 Termux:API)。
*   **远程拍照**: 调用后置摄像头拍照 (需 Termux:API)。
*   **命令执行**: 只有管理员可用的 Shell 命令执行器 (`/exec`)。
*   **进程守护**: 集成 PM2，支持掉线自动重启、开机自启（需配置 Termux-services）。

## 快速开始

### 1. 启动管理面板

在 Termux 或 Ubuntu 终端中运行：

```bash
chmod +x start_bot.sh
./start_bot.sh
```

### 2. 选择启动方式

脚本会显示一个菜单：
*   选择 **1** 使用 **PM2** 启动（推荐）。它会自动安装 Node.js 和 PM2，并将机器人作为后台服务运行。
*   选择 **4** 进行前台调试。

### 3. Telegram 使用

给机器人发送 `/start`。
如果你的 ID 是管理员 ID，你会看到一个包含以下按钮的键盘：

*   📊 **系统状态**
*   🔋 **电池信息**
*   📸 **拍摄照片**
*   🐚 **终端命令** (提示如何使用 /exec)
*   🔄 **重启机器人**

## 常用 PM2 命令

如果你选择使用 PM2 管理，也可以手动使用以下命令：

*   `pm2 list` - 查看运行状态
*   `pm2 log termux-bot` - 查看机器人日志
*   `pm2 stop termux-bot` - 停止机器人
*   `pm2 restart termux-bot` - 重启机器人

## 配置修改

编辑 `bot.py` 文件顶部：
```python
BOT_TOKEN = "你的Token"
ADMIN_ID = 你的ID
```
