/**
 * 后端地址集中配置
 * 换机器 / 换端口只需要改这里，别在组件里硬编码
 */
const HOST = 'localhost'
const PORT = 8888

export const HTTP_BASE = `http://${HOST}:${PORT}` // 普通接口，如 http://localhost:8888/list/小明
export const WS_BASE = `ws://${HOST}:${PORT}` // WebSocket，如 ws://localhost:8888/socket/小明
