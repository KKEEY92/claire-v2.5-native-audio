import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({ registerType: 'autoUpdate' }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/token': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
      // Live-Monitor: roher Container-stdout via SSE (log_server.py auf dem Host)
      '/logs': {
        target: 'http://localhost:3002',
        changeOrigin: true,
      }
    }
  }
});

