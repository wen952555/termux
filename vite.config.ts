import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// 自定义中间件：提供文件列表和删除功能
const mediaServerPlugin = () => ({
  name: 'media-server-plugin',
  configureServer(server) {
    server.middlewares.use((req, res, next) => {
      // 1. 获取文件列表 API
      // 使用严格匹配，防止路径混乱
      if (req.url === '/api/files' && req.method === 'GET') {
        const mediaDir = path.resolve(__dirname, 'captured_media');
        
        if (!fs.existsSync(mediaDir)) {
          fs.mkdirSync(mediaDir);
        }

        try {
          const fileNames = fs.readdirSync(mediaDir);
          const files = fileNames
            // 增加音频格式支持
            .filter(file => /\.(jpg|jpeg|png|mp4|m4a|mp3|wav)$/i.test(file))
            .map(file => {
              try {
                const filePath = path.join(mediaDir, file);
                const stats = fs.statSync(filePath);
                
                // 确定文件类型
                let type = 'image';
                if (file.endsWith('.mp4')) {
                  type = 'video';
                } else if (/\.(m4a|mp3|wav)$/i.test(file)) {
                  type = 'audio';
                }

                return {
                  name: file,
                  url: `/captured_media/${file}`,
                  type: type,
                  time: stats.mtime.getTime(),
                  size: stats.size
                };
              } catch (e) {
                return null;
              }
            })
            .filter((f): f is NonNullable<typeof f> => f !== null)
            .sort((a, b) => b.time - a.time);

          res.statusCode = 200;
          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify(files));
        } catch (err) {
          console.error('API Error:', err);
          res.statusCode = 500;
          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify({ error: String(err) }));
        }
        return; // 结束处理
      }

      // 2. 删除文件 API
      if (req.url === '/api/delete' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', () => {
          try {
            const parsedBody = JSON.parse(body || '{}');
            const { filename } = parsedBody;
            
            if (!filename) {
              res.statusCode = 400;
              res.end(JSON.stringify({ error: "Filename required" }));
              return;
            }

            // 安全检查：仅允许文件名，不允许路径
            const safeFilename = path.basename(filename);
            const filePath = path.resolve(__dirname, 'captured_media', safeFilename);
            
            if (fs.existsSync(filePath)) {
              fs.unlinkSync(filePath);
              res.setHeader('Content-Type', 'application/json');
              res.end(JSON.stringify({ success: true }));
            } else {
              res.statusCode = 404;
              res.setHeader('Content-Type', 'application/json');
              res.end(JSON.stringify({ error: "File not found" }));
            }
          } catch (err) {
            console.error('Delete Error:', err);
            res.statusCode = 500;
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify({ error: String(err) }));
          }
        });
        return; // 结束处理
      }

      // 非 API 请求，继续下一个中间件
      next();
    });
  }
});

export default defineConfig({
  plugins: [react(), mediaServerPlugin()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    fs: {
      allow: ['.']
    }
  }
})