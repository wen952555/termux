# Termux Telegram Bot

专为 Termux 和 Ubuntu (PRoot/Chroot) 环境设计的全能管理机器人。

## 🚀 极速更新/部署

复制以下命令在 Termux 中运行，可以强制修复冲突并更新到最新版本：

```bash
cd ~/termux && git fetch --all && git reset --hard origin/main && git pull && chmod +x start_bot.sh
./start_bot.sh
```

## ⚠️ 重要说明：Termux API

如果要使用 **电池信息** 或 **拍照** 功能，必须满足以下条件：

1.  **安装 APP**: 手机上必须安装 [Termux:API](https://f-droid.org/packages/com.termux.api/) 安卓应用。
2.  **安装包**: Termux 中必须安装 `termux-api` 包 (脚本会自动尝试安装)。
3.  **授权**: 首次使用时，需在手机上允许 Termux 获取相机/位置/文件权限。

## 功能列表

1.  **系统监控**: CPU、内存、磁盘、网络、进程 (Top 5)。
2.  **📂 文件管理 (新增)**:
    *   **浏览**: 点击菜单或输入 `/ls` 查看当前目录。
    *   **下载**: 使用 `/get <文件名>` 将 Termux 中的文件发送到 Telegram。
    *   **上传**: 直接发送文件给机器人，会自动保存到 `Downloads` 文件夹。
3.  **硬件控制**: 电池状态查询、远程拍照 (需 Termux:API)。
4.  **服务探测**: 自动扫描 SSH, MySQL, HTTP 等端口。
5.  **进程守护**: 支持 PM2 后台运行，掉线自动重启。

## 常用命令

*   `/start` - 显示主菜单
*   `/ls [路径]` - 列出文件
*   `/get <文件路径>` - 下载文件
*   `/exec <命令>` - 执行 Shell 命令
*   `/photo` - 拍照

## 依赖安装

如果自动安装失败：
```bash
# Termux 原生环境
pkg install python nodejs termux-api -y
pip install python-telegram-bot psutil
npm install -g pm2
```