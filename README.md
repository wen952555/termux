# Termux Telegram Bot

这是一个专为 Termux 设计的 Telegram 管理机器人。

## 快速开始

### 1. 运行 Bot (推荐)

如果你只是想运行机器人，不需要使用 Web 生成器，只需在 Termux/Ubuntu 中运行以下命令：

```bash
chmod +x start_bot.sh
./start_bot.sh
```

这个脚本会自动：
1. 安装 Python 环境。
2. 安装必要的库 (`python-telegram-bot`, `psutil`)。
3. 启动 `bot.py`。

### 2. Bot 功能

你的机器人 (`bot.py`) 已经配置了以下功能：

- **Token**: `8091415322:...`
- **Admin**: `1878794912`
- **命令**:
    - `/status`: 查看 CPU、内存、磁盘使用情况。
    - `/battery`: 查看 Termux 电池状态。
    - `/photo`: 调用摄像头拍照。
    - `/exec <命令>`: 执行 Shell 命令 (仅限管理员)。

## Web 生成器 (可选)

如果你想通过 AI 生成新的、功能不同的脚本，可以运行 Web 界面：

```bash
chmod +x deploy.sh
./deploy.sh
```

然后访问 `http://localhost:5173`。
