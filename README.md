# Termux Telegram Bot

专为 Termux 和 Ubuntu (PRoot/Chroot) 环境设计的全能管理机器人。

## 🚀 极速部署

一条命令即可完成安装、环境配置和后台启动：

```bash
cd ~/termux && git pull && ./start_bot.sh
```

**脚本将自动执行以下操作：**
1. 检查 Python、Termux API、PM2 等依赖。
2. 自动安装缺失的包。
3. 启动（或重启）后台守护进程。

## 🎮 使用方法

### 脚本命令
不再需要手动选择菜单，直接使用参数控制：

*   **启动/重启** (默认): `./start_bot.sh`
*   **查看日志**: `./start_bot.sh log`
*   **停止服务**: `./start_bot.sh stop`
*   **强制更新**: `./start_bot.sh update` (解决 Git 冲突)

### Telegram 机器人指令
*   `/start` - 显示面板和菜单
*   `/update` - **[新]** 远程更新 Bot 代码并自动重启
*   `/ls` - 查看文件
*   `/get <文件>` - 下载文件
*   `/exec <命令>` - 执行 Shell 命令

## ⚠️ 常见问题

### Git 冲突 (Merge Error)
如果在更新时遇到错误，可以使用 Bot 内的 `/update` 指令，或者在终端运行：
```bash
./start_bot.sh update
```
这将强制覆盖本地文件以保持与仓库同步。

### Termux API
要使用电池或拍照功能，请确保手机安装了 **Termux:API** 应用，并授予 Termux 相应权限。