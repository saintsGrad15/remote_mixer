import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  root: '.',
  base: '/static/dist/',
  build: {
    outDir: 'static/dist',
    emptyOutDir: true,
    rollupOptions: {
      input: path.resolve(__dirname, 'index.html')
    }
  },
  server: {
    proxy: {
      '/config': 'http://localhost:5001',
      '/ws': {
        target: 'ws://localhost:5001',
        ws: true
      }
    }
  }
})

