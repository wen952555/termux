import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import mime from 'mime-types' // 需要确保运行环境中能处理mime，或者我们手动处理

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// 简单的 mime 类型映射，避免引入 extra dependency 导致 Termux 安装困难
const getMimeType = (filename) => {
  const ext = path.extname(filename).toLowerCase();
  const map = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.mp4': 'video/mp4',
    '.m4a': 'audio/mp4', // m4a 通常是 audio/mp4 或 audio/x-m4a
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.json': 'application/json'
  };
  return map[ext] || 'application/octet-stream';
};

// 自定义中间件：提供文件列表、删除功能以及静态文件服务
const mediaServerPlugin = () => ({
  name: 'media-server-plugin',
  configureServer(server) {
    server.middlewares.use((req, res, next) => {
      const mediaDir = path.resolve(__dirname, 'captured_media');
      if (!fs.existsSync(mediaDir)) {
        fs.mkdirSync(mediaDir);
      }

      // 1. 获取文件列表 API
      if (req.url === '/api/files' && req.method === 'GET') {
        try {
          const fileNames = fs.readdirSync(mediaDir);
          const files = fileNames
            .filter(file => /\.(jpg|jpeg|png|mp4|m4a|mp3|wav)$/i.test(file))
            .map(file => {
              try {
                const filePath = path.join(mediaDir, file);
                const stats = fs.statSync(filePath);
                
                let type = 'image';
                if (file.endsWith('.mp4')) type = 'video';
                else if (/\.(m4a|mp3|wav)$/i.test(file)) type = 'audio';

                return {
                  name: file,
                  url: `/captured_media/${file}`,
                  type: type,
                  time: stats.mtime.getTime(),
                  size: stats.size
                };
              } catch (e) { return null; }
            })
            .filter(Boolean)
            .sort((a, b) => b.time - a.time);

          res.statusCode = 200;
          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify(files));
        } catch (err) {
          res.statusCode = 500;
          res.end(JSON.stringify({ error: String(err) }));
        }
        return;
      }

      // 2. 删除文件 API
      if (req.url === '/api/delete' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', () => {
          try {
            const { filename } = JSON.parse(body || '{}');
            if (!filename) {
              res.statusCode = 400;
              res.end(JSON.stringify({ error: "Filename required" }));
              return;
            }
            const safeFilename = path.basename(filename);
            const filePath = path.join(mediaDir, safeFilename);
            
            if (fs.existsSync(filePath)) {
              fs.unlinkSync(filePath);
              res.end(JSON.stringify({ success: true }));
            } else {
              res.statusCode = 404;
              res.end(JSON.stringify({ error: "File not found" }));
            }
          } catch (err) {
            res.statusCode = 500;
            res.end(JSON.stringify({ error: String(err) }));
          }
        });
        return;
      }

      // 3. 静态文件服务拦截 (针对 /captured_media/ 路径)
      // 这确保即使在某些环境下 Vite 不会自动 serve 根目录文件，我们也能强制 serve
      if (req.url?.startsWith('/captured_media/')) {
        const fileName = path.basename(req.url); // 安全起见只取文件名
        // 解码 URL (处理空格等)
        const safeFileName = decodeURIComponent(fileName);
        const filePath = path.join(mediaDir, safeFileName);

        if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
           const mimeType = getMimeType(safeFileName);
           res.setHeader('Content-Type', mimeType);
           // 创建读取流并 piping 到 response
           const stream = fs.createReadStream(filePath);
           stream.pipe(res);
           return; 
        }
      }

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