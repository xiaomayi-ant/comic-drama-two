import path from 'path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
    return {
      // build 后静态资源默认从 /fronter/ 下加载（对应后端 StaticFiles mount）
      base: '/fronter/',
      server: {
        port: 3000,
        host: '0.0.0.0',
        proxy: {
          // 本地开发：前端 /api -> 后端 http://127.0.0.1:8000/api
          '/api': {
            target: 'http://127.0.0.1:8003',
            changeOrigin: true,
          },
        },
      },
      plugins: [react()],
      resolve: {
        alias: {
          '@': path.resolve(__dirname, '.'),
        }
      }
    };
});
