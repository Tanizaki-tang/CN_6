import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    // 后端 CorConfig.py 的 allow_origins 里只有 8080，
    // 所以开发服务器必须也用 8080，否则浏览器的跨域校验会拦掉 /list 请求
    port: 8080,
    // 8080 被占用时直接报错退出，而不是自动换成 8081
    // （偷偷换端口 = Origin 变了 = 立刻被 CORS 拦掉，不如早点报错）
    strictPort: true
  }
})
