import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
})

// 响应拦截器：401 → 跳转登录并携带来源路径
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 避免在登录页循环跳转
      if (window.location.pathname !== '/login') {
        const redirect = encodeURIComponent(
          window.location.pathname + window.location.search
        )
        window.location.href = `/login?redirect=${redirect}`
      }
    }
    return Promise.reject(error)
  }
)

export default api
