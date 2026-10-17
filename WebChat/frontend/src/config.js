/**
 * 后端地址集中配置
 * 换机器 / 换端口只需要改这里，别在组件里硬编码
 */
const HOST = 'localhost'
export const PORT = 8888

export const HTTP_BASE = `http://${HOST}:${PORT}`
// 后端是 app.mount("/static", StaticFiles(directory=static))，
// 上传接口返回的 /static/uploads/xxx 就是挂在这里
export const STATIC_BASE = HTTP_BASE
export const WS_BASE = `ws://${HOST}:${PORT}`
