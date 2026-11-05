import axios from "axios";
import { useAuthStore } from "../stores/auth";
import { getAnonCookie } from "../stores/anon";

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

// ── Request interceptor: attach JWT + anon session cookie ────
api.interceptors.request.use((config) => {
  const authStore = useAuthStore();
  if (authStore.accessToken) {
    config.headers.Authorization = `Bearer ${authStore.accessToken}`;
  }
  // Always attach the anon session cookie (for rate limiting + audit)
  // — even authed users keep their session for continuity.
  config.headers["X-Session-Cookie"] = getAnonCookie();
  return config;
});

// ── Response interceptor: handle 401 with token refresh ──────
// When a request gets 401, we try to refresh the access token
// and retry the original request once. If refresh fails, we
// clear tokens (user is logged out).

let isRefreshing = false;
let failedQueue = [];

function processQueue(error, token = null) {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // ── Skip if not 401, or if we've already retried ────────
    if (error.response?.status !== 401 || originalRequest._retry) {
      // If 401 on auth endpoints (login/register/refresh), clear tokens
      if (
        error.response?.status === 401 &&
        (originalRequest.url?.includes("/api/auth/login") ||
          originalRequest.url?.includes("/api/auth/register") ||
          originalRequest.url?.includes("/api/auth/refresh"))
      ) {
        const authStore = useAuthStore();
        authStore._clearTokens();
      }
      return Promise.reject(error);
    }

    // ── If refresh endpoint itself failed, clear and reject ─
    if (originalRequest.url?.includes("/api/auth/refresh")) {
      const authStore = useAuthStore();
      authStore._clearTokens();
      return Promise.reject(error);
    }

    // ── Mark as retried to avoid infinite loop ──────────────
    originalRequest._retry = true;

    // ── If already refreshing, queue this request ───────────
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      })
        .then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        })
        .catch((err) => Promise.reject(err));
    }

    // ── Try to refresh ──────────────────────────────────────
    isRefreshing = true;
    const authStore = useAuthStore();

    try {
      const refreshed = await authStore.tryRefresh();
      if (!refreshed) {
        processQueue(error, null);
        return Promise.reject(error);
      }

      // Update the original request's header with new token
      originalRequest.headers.Authorization = `Bearer ${authStore.accessToken}`;
      processQueue(null, authStore.accessToken);
      return api(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);

export default api;
