// import axios from "axios";
// import Cookies from "js-cookie";

// const api = axios.create({
//   baseURL: process.env.NEXT_PUBLIC_API_BASE_URL,
//   withCredentials: true,
// });

// api.interceptors.request.use((config) => {
//   const token = Cookies.get("access");
//   if (token) {
//     config.headers.Authorization = `Bearer ${token}`;
//   }
//   return config;
// });

// api.interceptors.response.use(
//   (response) => response,
//   async (error) => {
//     const originalRequest = error.config;

//     if (error.response?.status === 401 && !originalRequest._retry) {
//       originalRequest._retry = true;

//       const refresh = Cookies.get("refresh");
//       if (!refresh) return Promise.reject(error);

//       try {
//         const res = await axios.post(
//           `${process.env.NEXT_PUBLIC_API_BASE_URL}/auth/refresh/`,
//           { refresh }
//         );

//         Cookies.set("access", res.data.access);
//         originalRequest.headers.Authorization = `Bearer ${res.data.access}`;

//         return api(originalRequest);
//       } catch (err) {
//         Cookies.remove("access");
//         Cookies.remove("refresh");
//       }
//     }

//     return Promise.reject(error);
//   }
// );

// export default api;