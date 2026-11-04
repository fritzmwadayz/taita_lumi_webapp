import axios from "axios";

// ── Axios instance ────────────────────────────────────────────
//
// In dev, Vite proxies /api/* to localhost:8000 (see vite.config.js),
// so baseURL = "" (relative) works.
//
// In production, VITE_API_BASE_URL is set to the deployed API URL,
// e.g. https://taitalumi-api.onrender.com

const baseURL = import.meta.env.VITE_API_BASE_URL || "";

const api = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
});

// ── Request interceptor: attach JWT if logged in ─────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("taitalumi_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor: handle 401 globally ────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid — clear and let the user re-auth.
      localStorage.removeItem("taitalumi_token");
      // (Phase 2: redirect to /login if not already there)
    }
    return Promise.reject(error);
  },
);

export default api;
