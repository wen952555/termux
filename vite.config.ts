import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // 加载当前目录下的环境变量，包括 .env 文件
  // VITE_ 前缀的变量会默认加载，但我们需要手动处理非 VITE_ 前缀的变量如果需要
  const env = loadEnv(mode, '.', '');

  return {
    plugins: [react()],
    // 允许在前端代码中使用 process.env.API_KEY
    define: {
      'process.env.API_KEY': JSON.stringify(env.VITE_API_KEY || env.API_KEY)
    },
    server: {
      // 设置为 true 以监听所有地址，方便在 Termux (Android) 环境下通过 localhost 访问
      host: true,
      port: 5173,
    }
  }
})