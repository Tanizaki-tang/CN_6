# WebChat 前端

Vue 3 + Vite。接口约定见上级目录的 [API.md](../API.md)。

## 运行

先启动后端（另开一个终端，占用 8888）：

```powershell
python WebChat\backend\application.py
```

再启动前端：

```powershell
cd WebChat\frontend
npm install      # 首次运行
npm run dev
```

打开 <http://localhost:8080>。

> 前端必须跑在 **8080**：后端 CORS 白名单里只有 8080。`vite.config.js` 开了 `strictPort`，端口被占用会直接报错，不会偷偷换端口。

## 目录结构

```
frontend/
├── index.html              # Vite 入口
├── vite.config.js          # 端口 8080 + strictPort
├── API.md → ../API.md      # 接口文档
└── src/
    ├── main.js             # 挂载 Vue + 路由
    ├── App.vue
    ├── config.js           # 后端地址集中配置（换机器只改这里）
    ├── style.css           # 全局样式与 CSS 变量
    ├── router/index.js     # / 昵称页，/chat 聊天页
    └── views/
        ├── NameView.vue    # 输入昵称 → 查重 → 进房
        └── ChatView.vue    # WebSocket 长连接、消息收发、在线列表
```

## 两个页面

| 路由 | 页面 | 做什么 |
| --- | --- | --- |
| `/` | `NameView` | 输入昵称，调 `GET /list/{name}` 查重，通过后把昵称存进 `sessionStorage` 并跳转 |
| `/chat` | `ChatView` | 连 `ws://localhost:8888/socket/{name}`，收发消息、显示在线用户 |

昵称存在 `sessionStorage`，所以刷新 `/chat` 不会掉线重问；关掉标签页则清空。

## 实现要点

- **消息分流**：`onmessage` 里用 `data.userlist` 是否存在来区分"在线列表"和"聊天消息"。
- **不重复显示**：服务端广播给所有人（含发送者），所以发送后只等广播回来，本地不再 push。
- **气泡左右**：用 `msg.name === 自己的昵称` 判断。
- **时间由前端生成**：后端只转发，不填 `time`。
