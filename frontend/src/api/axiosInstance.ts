import axios from 'axios';
import Cookies from 'js-cookie';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
});

// Interceptor สำหรับแนบ Token
api.interceptors.request.use((config) => {
  const token = Cookies.get('access');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Refresh Token Logic เมื่อเจอ 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refresh = Cookies.get('refresh');
      if (refresh) {
        try {
          const res = await axios.post(`${import.meta.env.VITE_API_BASE_URL}/user/token/refresh/`, { refresh });
          Cookies.set('access', res.data.access);
          return api(originalRequest);
        } catch (err) {
          Cookies.remove('access');
          Cookies.remove('refresh');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;