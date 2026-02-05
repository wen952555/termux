# Termux Telegram Bot

专为 Termux 和 Ubuntu (PRoot/Chroot) 环境设计的全能监控卫士。

## 🚀 极速部署

一条命令即可完成安装、环境配置和后台启动：

```bash
cd ~/termux && git pull && ./start_bot.sh
```

**脚本将自动执行以下操作：**
1. 检查 Python、Termux API、PM2 等依赖。
2. 自动安装缺失的包。
3. 启动（或重启）后台守护进程。

## 🎮 功能列表

### 监控与控制 (新版)
*   **📸 拍摄照片**: 调用后置摄像头拍照并发送。
*   **🎤 录制音频**: 录制 10 秒环境音频并发送。
*   **🗑 清理媒体**: 一键删除所有拍摄的照片和音频缓存，释放空间。
*   **🔋 电池信息**: 查看电量、温度和充电状态。
*   **🔦 手电筒**: 远程控制闪光灯开关。

### 系统管理
*   **📊 系统状态**: CPU、内存、磁盘、网络流量实时看板。
*   **🛠 服务探测**: 自动扫描 SSH, MySQL, Web 等常用端口。
*   **🐚 远程终端**: 使用 `/exec` 执行任意 Shell 命令。

## 🤖 机器人指令

*   `/start` - 显示主菜单
*   `/update` - **强制更新** Bot 代码并自动重启
*   `/exec <命令>` - 执行 Shell 命令 (例如: `/exec ls -lh`)

## ⚠️ 常见问题

### 1. 摄像头/麦克风错误
Termux API 需要 Android 权限支持：
1.  确保手机已安装 **Termux:API** 应用（Google Play 或 F-Droid）。
2.  在 Android 设置中授予 Termux **相机** 和 **麦克风** 权限。
3.  如果是在 Ubuntu (PRoot) 下运行，Bot 会尝试自动调用 Termux 路径，但若失败，请尝试在 Native Termux 下运行。

### 2. 视频功能去哪了？
由于 Termux API 目前**不支持**视频录制指令 (`termux-camera-record` 不存在)，该功能已被移除以保证系统稳定性。