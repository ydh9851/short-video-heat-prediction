import axios from 'axios'
import { ElLoading, ElNotification } from 'element-plus'
import { router } from '@/router'

/**
 * 取出本次请求的 traceId：响应头优先（后端 TraceIdFilter 回写 X-Trace-Id），其次响应体。
 * 有了它，用户就能在截图里给出 traceId，运维/开发直接在后端日志里定位到那一行。
 */
function extractTraceId (e) {
  const headers = e && e.response && e.response.headers
  if (headers) {
    const v = headers['x-trace-id'] || headers['X-Trace-Id']
    if (v) return v
  }
  const body = e && (e.response ? e.response.data : e)
  if (body && body.traceId) return body.traceId
  return ''
}

/**
 * 统一错误提示：右下角通知，右下角不遮挡主内容。
 * 消息体带上 traceId 与排查指引，便于按 traceId 定位后端日志。
 */
function notifyError (e, fallback) {
  const body = e && e.response ? e.response.data : e
  // 业务提示优先于 axios 的英文状态码文案，保证错误信息可读
  const msg = (body && body.message) || fallback || (e && e.message) || '请求失败'
  const traceId = extractTraceId(e)
  ElNotification({
    title: '操作失败',
    type: 'error',
    duration: 6000,
    dangerouslyUseHTMLString: true,
    message: traceId
      ? `${msg}<div style="margin-top:6px;font-size:12px;color:#94a3b8">traceId：<b>${traceId}</b>（可在后端日志中按此检索）</div>`
      : `${msg}<div style="margin-top:6px;font-size:12px;color:#94a3b8">请检查网络或稍后重试</div>`
  })
}

const request = function (loadtip, query) {
  let loading
  if (loadtip) {
    loading = ElLoading.service({
      lock: false,
      text: '正在加载中…',
      spinner: 'el-icon-loading',
      background: 'rgba(0, 0, 0, 0.5)'
    })
  }
  return axios.request(query)
    .then(res => {
      if (loadtip) {
        loading.close()
      }
      const body = res.data || {}
      const traceId = (res.headers && (res.headers['x-trace-id'] || res.headers['X-Trace-Id'])) || body.traceId || ''
      // 只有 code === 1 代表业务成功；其余一律按失败处理，避免把错误响应当成正常数据渲染
      if (body.code === 1) {
        return Promise.resolve(body)
      }
      if (body.code === 400 || body.code === 401 || body.code === 402) {
        // 登录接口本身失败（如账号密码错误）：交给登录页提示，不触发“会话失效”跳转
        const isLoginApi = (query.url || '').indexOf('/api/user/login') === 0
        if (!isLoginApi) {
          router.push({ path: '/login' })
        }
        return Promise.reject({ message: body.message || '登录状态已失效，请重新登录', code: body.code, traceId, silent: true })
      }
      if (body.code === 404) {
        // 资源不存在由调用方自行处理（如任务轮询），不弹全局提示避免重复打扰
        return Promise.reject({ message: body.message || '资源不存在', code: 404, traceId, silent: true })
      }
      return Promise.reject({
        message: body.message || (body.code === 502 ? '没有权限执行该操作' : '请求失败，请稍后重试'),
        code: body.code,
        traceId
      })
    })
    .catch(e => {
      if (loadtip) {
        loading.close()
      }
      if (e && e.silent) {
        return Promise.reject(e)
      }
      const status = e && e.response && e.response.status
      if (status === 401) {
        router.push({ path: '/login' })
        notifyError(e, '登录状态已失效，请重新登录')
      } else if (status === 403) {
        notifyError(e, '没有权限执行该操作')
      } else if (status === 429) {
        notifyError(e, '请求过于频繁，请稍后再试')
      } else {
        notifyError(e)
      }
      return Promise.reject(e)
    })
}

const post = function (url, params, timeoutMs) {
  const query = {
    baseURL: import.meta.env.VITE_APP_URL,
    url: url,
    method: 'post',
    withCredentials: true,
    timeout: timeoutMs || 30000,
    data: params,
    headers: { 'Content-Type': 'application/json', 'request-ajax': true }
  }
  return request(false, query)
}

const postWithLoadTip = function (url, params) {
  const query = {
    baseURL: import.meta.env.VITE_APP_URL,
    url: url,
    method: 'post',
    withCredentials: true,
    timeout: 30000,
    data: params,
    headers: { 'Content-Type': 'application/json', 'request-ajax': true }
  }
  return request(true, query)
}

const postWithOutLoadTip = function (url, params) {
  const query = {
    baseURL: import.meta.env.VITE_APP_URL,
    url: url,
    method: 'post',
    withCredentials: true,
    timeout: 30000,
    data: params,
    headers: { 'Content-Type': 'application/json', 'request-ajax': true }
  }
  return request(false, query)
}

const get = function (url, params, timeoutMs) {
  const query = {
    baseURL: import.meta.env.VITE_APP_URL,
    url: url,
    method: 'get',
    withCredentials: true,
    timeout: timeoutMs || 30000,
    params: params,
    headers: { 'request-ajax': true }
  }
  return request(false, query)
}

const form = function (url, params, timeoutMs) {
  const query = {
    baseURL: import.meta.env.VITE_APP_URL,
    url: url,
    method: 'post',
    withCredentials: true,
    timeout: timeoutMs || 30000,
    data: params,
    headers: { 'Content-Type': 'multipart/form-data', 'request-ajax': true }
  }
  return request(false, query)
}

const put = function (url, params, timeoutMs) {
  const query = {
    baseURL: import.meta.env.VITE_APP_URL,
    url: url,
    method: 'put',
    withCredentials: true,
    timeout: timeoutMs || 30000,
    data: params,
    headers: { 'Content-Type': 'application/json', 'request-ajax': true }
  }
  return request(false, query)
}

const del = function (url, params, timeoutMs) {
  const query = {
    baseURL: import.meta.env.VITE_APP_URL,
    url: url,
    method: 'delete',
    withCredentials: true,
    timeout: timeoutMs || 30000,
    params: params,
    headers: { 'request-ajax': true }
  }
  return request(false, query)
}

export {
  post,
  postWithLoadTip,
  postWithOutLoadTip,
  get,
  put,
  del,
  form,
  notifyError
}
