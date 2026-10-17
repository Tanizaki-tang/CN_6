/**
 * 登录态：uid + 用户名存在 sessionStorage，刷新不掉线，关标签页即清空。
 * 后端的 WS 是按 uid 连的，所以 uid 必须留着。
 */
const KEY = 'webchat.user'

/** @returns {{uid:number, name:string}|null} */
export function getUser() {
  try {
    const raw = sessionStorage.getItem(KEY)
    if (!raw) return null
    const u = JSON.parse(raw)
    if (!u || typeof u.uid !== 'number' || !u.name) return null
    return u
  } catch {
    // 存进去的不是合法 JSON（手改过 / 旧版本遗留）→ 当没登录
    sessionStorage.removeItem(KEY)
    return null
  }
}

export function setUser(user) {
  sessionStorage.setItem(KEY, JSON.stringify({ uid: user.uid, name: user.name }))
}

export function clearUser() {
  sessionStorage.removeItem(KEY)
}
