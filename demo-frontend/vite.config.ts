import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const proxy = { '/api': { target: 'http://127.0.0.1:8010', changeOrigin: true, rewrite: (path: string) => path.replace(/^\/api/, '') } }
export default defineConfig({ plugins: [vue()], server: { proxy }, preview: { proxy } })
