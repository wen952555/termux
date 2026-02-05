# Termux Telegram Bot

专为 Termux 和 Ubuntu (PRoot/Chroot) 环境设计的全能监控卫士。

## 🚀 极速部署

### 1. 启动 Bot
```bash
cd ~/termux && git pull && ./start_bot.sh
```

### 2. 开启 Web 监控台
Bot 启动后，Web 监控台默认运行在本地端口 `5173`。
```bash
npm run dev -- --host
```

### 3. 开启外网访问 (Cloudflare Tunnel)
如果您想在任何地方访问监控台，可以使用 Cloudflare Tunnel：

1.  在 [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/) 创建一个新的 Tunnel。
2.  获取您的 **Tunnel Token**。
3.  在后台添加 Public Hostname，设置 Service 为 `http://localhost:5173`。
4.  在 Termux 中运行：
    ```bash
    ./start_bot.sh tunnel <你的Token>
    ```
    *(如果不加 Token 参数运行，脚本会提示你输入)*

## 🎮 功能列表

### 监控与控制 (新版)
*   **📸 拍摄照片**: 调用后置摄像头拍照并发送。
*   **📹 录制视频**: 录制 30 秒短视频（需设备支持）。
*   **🎤 录制音频**: 录制 30 秒环境音频并发送。
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

### 2. 视频录制失败？
视频录制功能依赖 `termux-camera-record` 指令。该指令在某些新版 Termux API 中可能被移除或不兼容。如果点击按钮后提示错误，说明您的环境不支持此功能，请使用拍照功能代替。
