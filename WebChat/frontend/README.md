# WebChat 前端

Vue 3 + Vite。接口清单见 [`src/api.js`](src/api.js) 顶部的注释；后端路由的定义在
`../backend/Service/auth_service.py` 与 `../backend/Service/chat_service.py`。
（原先这里指向的 `../API.md` 已不存在。）

## 运行

> 最省事的方式：回到仓库根目录，双击 **`start.bat`**（或跑 `start.ps1`），
> 它会自动把前后端都起起来并打开浏览器。下面是手动方式。

先启动后端（另开一个终端，占用 8888）：

```powershell
cd WebChat\backend
python application.py
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
└── src/
    ├── main.js             # 挂载 Vue + 路由
    ├── App.vue
    ├── config.js           # 后端地址集中配置（换机器只改这里）
    ├── api.js              # REST 封装 + HttpError
    ├── auth.js             # 登录态（sessionStorage：uid + 用户名）
    ├── style.css           # 全局样式与 CSS 变量
    ├── router/index.js     # / 登录注册页，/chat 聊天页（带守卫）
    └── views/
        ├── LoginView.vue   # 登录 / 注册（一个页面两个 tab）
        └── ChatView.vue    # WebSocket 长连接、消息收发、在线列表、群聊、图片
```

## 两个页面

| 路由 | 页面 | 做什么 |
| --- | --- | --- |
| `/` | `LoginView` | `POST /auth/login` 或 `POST /auth/register`（注册成功后再自动登录一次，因为 register 不返回 uid），拿到 `{uid,name}` 存进 `sessionStorage` 后跳 `/chat` |
| `/chat` | `ChatView` | 连 `ws://localhost:8888/chat/ws/{uid}`，收发消息、在线用户、私聊/群聊（建群、加入、退出）、历史消息、图片、退出登录 |

登录态存在 `sessionStorage`，所以刷新 `/chat` 不会掉线重问；关掉标签页则清空。
`router/index.js` 里有全局前置守卫：没登录访问 `/chat` 直接回 `/`。

## 实现要点

- **消息分流**：`onmessage` 里用 `data.userlist` 是否存在来区分"在线列表"和"聊天消息"。
- **在线名单带 uid**：后端 `users: [{uid,name}]`，前端靠它才能对任意在线用户发起私聊
  （`target_uid` 是必填的，光有昵称发不出去）。
- **消息归位**：下行消息用 `target_uid`（私聊）/ `group_id`（群聊）判断该塞进哪个会话，
  不是靠昵称比较。
- **发送后不本地 push**：后端会广播给所有人（含发送者），等回执回来即可；自己给自己发时
  后端只回一条。
- **气泡左右**：用 `data.sender_id === 自己的 uid` 判断。
- **图片消息**：`POST /chat/post/upload_img` 返回 `img_url`（形如 `/static/uploads/xxx.png`
  的相对路径），渲染时用 `config.js` 里的 `STATIC_BASE` 拼成完整地址。
- **时间由后端给**：下行消息里的 `time` 直接显示。
- **退出**：`POST /auth/logout/{uid}` 把库里的 `is_online` 置否，然后清 `sessionStorage`。

## 群聊

后端 `group_members` 表决定"谁在这个群里"，前端据此分成两块：

- **我加入的群聊**：`GET /chat/get/groups?uid=`，显示 `#群号 · N 人`，行尾有"退出"按钮
  （自己建的群按钮是禁用的——后端也不允许群主退出）。
- **发现群聊**：`GET /chat/get/groups/discover?uid=`，过滤出 `is_member === false` 的群，
  点"加入"调 `POST /chat/post/group/join`，成功后刷新列表并直接进入这个群。
- **建群**：`POST /chat/post/group`，后端会把建群者加成第一个成员，所以建完就能直接聊。
- **加入/退出提示**：后端推 `{system:true, sender_id:null, msg:"xxx 加入了群聊"}`，
  前端渲染成居中的灰色小条（`.sys-line`），不计未读；它**不入库**，刷新后消失。
- **非成员**：既收不到群消息，群历史也会返回 403，所以发现列表里的群点不进去。
