# Termux Telegram Bot

专为 Termux 和 Ubuntu (PRoot/Chroot) 环境设计的全能管理机器人。

## 🔧 常见问题修复

### Git 冲突 (Merge Error)
如果你在运行时遇到 `error: Your local changes...` 提示，这是因为你本地的文件与远程仓库不一致。

**解决方法：**
运行以下命令强制覆盖本地文件：
```bash
git fetch --all && git reset --hard origin/main && git pull && chmod +x start_bot.sh
```

## 🚀 部署命令

```bash
# 1. 修复并更新
git fetch --all && git reset --hard origin/main && git pull && chmod +x start_bot.sh

# 2. 启动
./start_bot.sh
```

## ⚠️ Termux API 说明

要使用 **电池** 或 **拍照** 功能：
1.  手机安装 **Termux:API** APP。
2.  Termux 内安装 `termux-api` 包 (脚本会自动安装)。
3.  **Ubuntu 用户**: 在 Ubuntu 内可能无法直接调用 API，建议在原生 Termux 环境下运行 Bot，或者配置 socket 穿透。

## 功能列表

*   **系统监控**: CPU、内存、磁盘、网络、进程。
*   **📂 文件管理**: `/ls` 浏览, `/get` 下载, 直接发送文件上传。
*   **硬件控制**: 电池状态、远程拍照。
*   **服务探测**: 自动扫描常用端口。
*   **进程守护**: PM2 自动重启。
