# WebChat

学校作业用：一个基于 **FastAPI + WebSocket** 的在线多人聊天室。

输入昵称即可加入，消息实时广播给房间内所有人，右侧同步显示在线用户列表。

本项目是对github项目EZ-Chat（SpringBoot + Vue 版本）的 Python 实现，感谢大佬开源
原项目链接：https://github.com/baobaoJK/EZ-Chat.git

后端由 Java 换成 FastAPI，前端由 Vue 2 + Element-Plus 换成 Vue 3 + Vite。

---

## 功能

- **匿名进房**：输入昵称即可聊天，进房前自动查重名
- **实时消息**：WebSocket 长连接，消息毫秒级广播
- **在线列表**：有人加入或退出时，全体自动刷新
- **连接状态**：顶栏显示「连接中 / 已连接 / 已断开」
- **消息气泡**：自己的消息靠右、他人靠左，带昵称与时间
- **退出聊天室**：主动断开连接并从在线列表移除
- 支持表情符号与 emoji 😊
- 昵称上限 12 字，正文支持多行（Enter 发送，Shift + Enter 换行）

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.13 · FastAPI · Uvicorn · Pydantic |
| 通信 | HTTP（昵称查重）+ WebSocket（消息收发） |
| 前端 | Vue 3 · Vue Router 4 · Vite |
| 端口 | 后端 `8888`，前端 `8080`（固定） |


## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+

### 1. 启动后端（占用 8888）

```powershell
pip install fastapi uvicorn pydantic
python WebChat\backend\application.py
```

> 本项目实际只依赖 **fastapi / uvicorn / pydantic** 三个包。

自检：访问 <http://localhost:8888/>，应返回

```json
{ "msg": "Chat Server 服务运行中", "author": "Tang", "version": "1.0" }
```

### 2. 启动前端（占用 8080）

```powershell
cd WebChat\frontend
npm install
npm run dev
```

浏览器打开 <http://localhost:8080>。

> ⚠️ 前端**必须**跑在 8080。后端 CORS 白名单里只写了 `http://localhost:8080` 和
> `http://127.0.0.1:8080`，换成别的端口会立刻被浏览器拦掉。因此 `vite.config.js` 开了
> `strictPort: true`，端口被占用时直接报错，而不是偷偷换到 8081。

### 3. 验证多人聊天

再开一个浏览器窗口（或使用无痕模式）访问 <http://localhost:8080>，用另一个昵称进入，
即可看到双方消息实时同步、在线列表变为两人。

## 通信约定

完整协议见 [API.md](API.md)

两个容易踩的坑：

1. **广播包含发送者自己** —— `send()` 之后本地不要再 push 一条，否则自己的消息显示两遍。
2. **时间由前端生成** —— 后端只做转发，不填 `time` 字段。

## 已知限制

- **重名不拦截**：后端若发现昵称已存在，既不覆盖也不拒绝，连接会继续进入消息循环，
  产生「幽灵用户」。前端的查重请求是目前唯一防线。
- **无历史消息**：不落库，刷新即丢失，新加入者看不到之前的聊天内容。
- **无鉴权**：任何人知道昵称即可加入。
- **正文无长度限制**：前端只限制了昵称长度。
- **单进程内存存储**：用户表存在进程内存中，重启即清空，也无法多实例部署。

## 相关

- [API.md](API.md) —— 接口与 WebSocket 协议详解、时序图、排错表
- [EZ-Chat](../EZ-Chat/) —— 同功能的 Java（SpringBoot）参考实现
