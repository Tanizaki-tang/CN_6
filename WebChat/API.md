# WebChat 接口文档

后端基于 FastAPI，前端基于 Vue 3 + Vite。本文档描述前后端之间的全部通信约定。

- 后端目录：`WebChat/backend/`
- 前端目录：`WebChat/frontend/`

---

## 1. 启动方式

**后端**（默认占用 `8888` 端口）

```powershell
python WebChat\backend\application.py
```

启动后访问 <http://localhost:8888/> 自检，应返回：

```json
{ "msg": "Chat Server 服务运行中", "author": "Tang", "version": "1.0" }
```

**前端**（开发服务器固定占用 `8080` 端口）

```powershell
cd WebChat\frontend
npm install      # 首次运行
npm run dev
```

浏览器打开 <http://localhost:8080>。

> ⚠️ 前端**必须**跑在 8080。后端 CORS 白名单里只写了 `http://localhost:8080` 和 `http://127.0.0.1:8080`，换成别的端口（Vite 自动跳到 8081 之类）会立刻被浏览器拦掉。所以 `vite.config.js` 里设置了 `strictPort: true`，端口被占用时直接报错而不是偷偷换端口。

---

## 2. 地址总览

| 类型 | 地址 |
| --- | --- |
| HTTP 基址 | `http://localhost:8888` |
| WebSocket 基址 | `ws://localhost:8888` |

---

## 3. HTTP 接口

### 3.1 服务自检

```
GET /
```

**响应** `200 OK`

```json
{
  "msg": "Chat Server 服务运行中",
  "author": "Tang",
  "version": "1.0"
}
```

### 3.2 查询某昵称是否被占用

```
GET /list/{username}
```

| 参数 | 位置 | 类型 | 说明 |
| --- | --- | --- | --- |
| `username` | 路径 | string | 待查询的昵称，中文需 URL 编码 |

**响应** `200 OK`

```json
{
  "isEmpty": false,
  "isExist": true
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `isEmpty` | bool | 当前聊天室是否一个人都没有 |
| `isExist` | bool | 该昵称是否已在线。`isEmpty` 为 `true` 时恒为 `false` |

**典型用法**：用户输入昵称后、建立 WebSocket 之前先调这个接口。若 `isExist` 为 `true` 说明重名，提示用户换一个，避免出现"两个同名用户"。

**curl 示例**

```bash
curl "http://localhost:8888/list/%E5%B0%8F%E6%98%8E"    # 查询"小明"
```

---

## 4. WebSocket 协议

### 4.1 建立连接

```
ws://localhost:8888/socket/{username}
```

| 参数 | 位置 | 类型 | 说明 |
| --- | --- | --- | --- |
| `username` | 路径 | string | 用户昵称，需 URL 编码 |

**示例**：`ws://localhost:8888/socket/小明`

连接建立后服务端立即 `accept`，无需客户端发送任何握手消息。

### 4.2 服务端 → 客户端

服务端只会下发**两种** JSON 消息，客户端靠**有没有 `userlist` 字段**来区分：

#### (a) 在线用户列表

有人**加入**或**退出**时，向所有在线用户广播。

```json
{ "userlist": ["小明", "小红"] }
```

⚠️ 注意：某人自己加入时，**他自己也会收到**这条消息，因此客户端不需要自己去维护用户列表，直接整体替换即可。

#### (b) 聊天消息

任何人发言时，向所有在线用户广播（**包括发送者本人**）。

```json
{
  "name": "小明",
  "time": "2026-10-09 15:04:05",
  "msg": "大家好"
}
```

⚠️ 因为广播包含发送者自己，客户端 `send()` 之后**不要**再本地 push 一条，否则自己的消息会显示两遍。判断气泡靠左还是靠右，用 `msg.name === 自己的昵称`。

### 4.3 客户端 → 服务端

只有一种消息：**发送聊天内容**。

```json
{
  "name": "小明",
  "time": "2026-10-09 15:04:05",
  "msg": "大家好"
}
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `name` | string | ✅ | 发言者昵称 |
| `time` | string | ✅ | 发言时间，格式 `YYYY-MM-DD HH:mm:ss`。**由前端生成**，后端只做转发 |
| `msg` | string | ✅ | 消息正文 |

> ⚠️ 三个字段**全部必填**。后端用 Pydantic 的 `Message` 模型做校验（见 `backend/Model.py`），少一个字段会抛 `ValidationError`，该消息不会被广播。

---

## 5. 数据模型

定义在 `backend/Model.py`，前端需要与之对齐。

```python
class UserList(BaseModel):
    userlist: List[str]        # {"userlist": ["小明", "小红"]}

class Message(BaseModel):
    name: str                  # 昵称
    time: str                  # "2026-10-09 15:04:05"
    msg: str                   # 正文
```

---

## 6. 完整时序

```
浏览器                        后端 (:8888)
  │
  │  GET /list/小明                    ← ① 查重名
  │ ─────────────────────────────>
  │  { "isEmpty": true, "isExist": false }
  │ <─────────────────────────────
  │
  │  WebSocket 握手 ws://…/socket/小明  ← ② 进房
  │ ─────────────────────────────>
  │ <───────────── 连接建立 ────────────
  │
  │                    服务端把"小明"写入 session_map
  │ <─── {"userlist": ["小明"]} ─────── ← ③ 广播在线列表（所有人，含自己）
  │
  │  {"name":"小明","time":"…","msg":"hi"}  ← ④ 发言
  │ ─────────────────────────────>
  │                    服务端广播给 session_map 里所有人
  │ <─── {"name":"小明","time":"…","msg":"hi"}   ← ⑤ 连自己也会收到
  │
  │  （另一个用户小红加入）
  │ <─── {"userlist": ["小明","小红"]} ── ← ⑥ 列表更新
  │
  │  close()                            ← ⑦ 关页面/点退出
  │ ─────────────────────────────>
  │                    服务端从 session_map 删除，广播新列表
```

---

## 7. 前端接入示例

### 7.1 查询昵称 + 建立连接

```js
const HTTP_BASE = 'http://localhost:8888'
const WS_BASE = 'ws://localhost:8888'

// ① 查重名
const res = await fetch(`${HTTP_BASE}/list/${encodeURIComponent(name)}`)
const { isExist } = await res.json()
if (isExist) throw new Error('昵称已被占用')

// ② 建立长连接
const socket = new WebSocket(`${WS_BASE}/socket/${encodeURIComponent(name)}`)

socket.onopen = () => console.log('已连接')

socket.onmessage = (event) => {
  const data = JSON.parse(event.data)

  if (data.userlist) {
    // (a) 在线列表 —— 整体替换
    userList.value = data.userlist
  } else {
    // (b) 聊天消息 —— 直接追加即可，自己的消息也走这里
    messages.value.push(data)
  }
}

socket.onclose = () => console.log('连接已关闭')
socket.onerror = () => console.error('WebSocket 出错')
```

### 7.2 发送消息

```js
function send(text) {
  if (socket.readyState !== WebSocket.OPEN) return

  socket.send(JSON.stringify({
    name: myName,
    time: formatTime(new Date()),   // 必须前端生成
    msg: text
  }))
}

function formatTime(d) {
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ` +
         `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}
```

### 7.3 退出

```js
socket.close()   // 服务端在 WebSocketDisconnect 分支里删除用户并广播新列表
```

---

## 8. 常见问题排查

| 现象 | 原因 | 解决 |
| --- | --- | --- |
| `/list` 请求被浏览器拦截，控制台报 CORS | 前端没跑在 8080，Origin 不在白名单 | 确认 `npm run dev` 输出的是 `http://localhost:8080` |
| fetch 直接抛异常，提示连接不上 | 后端没启动 / 端口不是 8888 | 确认 `python WebChat\backend\application.py` 在跑 |
| WebSocket 一直"连接中"后断开 | 后端没启动 | 同上。WebSocket 不受 CORS 限制，所以它出错基本就是服务没开 |
| 自己发的消息出现两遍 | `send()` 后又本地 push 了一次 | 只依赖服务端广播，本地不要重复添加 |
| 后端报 `ValidationError`，消息发不出去 | 发送的 JSON 缺了 `name`/`time`/`msg` 之一 | 三个字段都要传 |
| 时间显示不对 | 时间由前端生成，后端不填 | 检查前端的 `formatTime()` |
| 用户列表不更新 | 加入/退出才广播 | 正常现象，列表只在人员变动时刷新 |
| 两个同名用户同时在线 | 后端遇到重名不拒绝也不覆盖 | 进房前先调 `/list/{username}` 挡一下 |

---

## 9. 已知限制

- **重名不拦截**：`websocket_server.py` 中若 `is_exist` 为 `True`，既不覆盖 `session_map` 也不拒绝连接，连接会继续进入消息循环，产生"幽灵用户"。前端查重是目前的唯一防线。
- **无历史消息**：不落库，刷新即丢失，新加入者看不到之前的聊天内容。
- **无鉴权**：任何人知道昵称即可加入。
- **消息无长度限制**：前端限制昵称 12 字，消息正文未做限制。
