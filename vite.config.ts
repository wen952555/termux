import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'
import os from 'os'
import { exec } from 'child_process'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const getMimeType = (filename) => {
  const ext = path.extname(filename).toLowerCase();
  const map = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.mp4': 'video/mp4',
    '.m4a': 'audio/mp4',
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.json': 'application/json'
  };
  return map[ext] || 'application/octet-stream';
};

const mediaServerPlugin = () => ({
  name: 'media-server-plugin',
  configureServer(server) {
    server.middlewares.use((req, res, next) => {
      const mediaDir = path.resolve(__dirname, 'captured_media');
      if (!fs.existsSync(mediaDir)) {
        fs.mkdirSync(mediaDir);
      }

      // 1. System Stats API
      if (req.url === '/api/system' && req.method === 'GET') {
        const cpus = os.cpus();
        // Calculate CPU usage roughly based on load avg for simplicity in this context, 
        // or just use loadavg[0] normalized by core count.
        const loadAvg = os.loadavg();
        const cpuUsage = Math.min(100, (loadAvg[0] / cpus.length) * 100);
        
        const totalMem = os.totalmem();
        const freeMem = os.freemem();
        const usedMem = totalMem - freeMem;

        // Get Disk Usage asynchronously
        exec('df -k /', (err, stdout) => {
          let diskInfo = { total: 0, free: 0, used: 0, percent: 0 };
          if (!err && stdout) {
            const lines = stdout.trim().split('\n');
            if (lines.length > 1) {
              const parts = lines[1].replace(/\s+/g, ' ').split(' ');
              // df -k output: Filesystem 1K-blocks Used Available Use% Mounted on
              // Index might vary slightly depending on OS implementation, usually:
              // total=1, used=2, available=3, percent=4
              if (parts.length >= 5) {
                diskInfo = {
                  total: parseInt(parts[1]) * 1024,
                  used: parseInt(parts[2]) * 1024,
                  free: parseInt(parts[3]) * 1024,
                  percent: parseInt(parts[4].replace('%', ''))
                };
              }
            }
          }

          const stats = {
            cpu: parseFloat(cpuUsage.toFixed(1)),
            memory: {
              total: totalMem,
              free: freeMem,
              used: usedMem,
              percent: parseFloat(((usedMem / totalMem) * 100).toFixed(1))
            },
            disk: diskInfo,
            uptime: os.uptime(),
            platform: os.platform() + ' ' + os.release()
          };

          res.statusCode = 200;
          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify(stats));
        });
        return;
      }

      // 2. Get Files List API
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

      // 3. Delete File API
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

      // 4. Static File Serving (captured_media)
      if (req.url?.startsWith('/captured_media/')) {
        const fileName = path.basename(req.url);
        const safeFileName = decodeURIComponent(fileName);
        const filePath = path.join(mediaDir, safeFileName);
        if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
           const mimeType = getMimeType(safeFileName);
           res.setHeader('Content-Type', mimeType);
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
