import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // 加载当前目录下的环境变量，包括 .env 文件
  const env = loadEnv(mode, '.', '');

  return {
    plugins: [react()],
    // 允许在前端代码中使用 process.env.API_KEY
    define: {
      'process.env.API_KEY': JSON.stringify(env.VITE_API_KEY || env.API_KEY)
    },
    server: {
      // 强制监听所有 IPv4 接口，确保 192.168.x.x 可以访问
      host: '0.0.0.0',
      port: 5173,
      // 允许任何 host header，防止某些防火墙或代理阻拦
      strictPort: true,
      cors: true,
      allowedHosts: true
    }
  }
})