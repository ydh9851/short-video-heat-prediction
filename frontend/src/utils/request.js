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
 * 消息体带上 traceId 与排查指引——答辩现场出错时，这一行就能说明系统是可追溯的。
 */
function notifyError (e, fallback) {
  const body = e && e.response ? e.response.data : e
  const msg = (e && e.message) || (body && body.message) || fallback || '请求失败'
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
      if (body.code === 401 || body.code === 502) {
        router.push({ path: '/login' })
        return Promise.reject({ message: body.message || '登录状态已失效，请重新登录', code: body.code, traceId })
      } else if (body.code === 500 || body.code === 501) {
        return Promise.reject({ message: body.message || '服务处理失败，请稍后重试', code: body.code, traceId })
      } else {
        return Promise.resolve(body)
      }
    })
    .catch(e => {
      if (loadtip) {
        loading.close()
      }
      notifyError(e)
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

export {
  post,
  postWithLoadTip,
  postWithOutLoadTip,
  get,
  form,
  notifyError
}
