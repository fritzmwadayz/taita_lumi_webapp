import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// ── Dev server proxy ──────────────────────────────────────────
// During dev, the Vue app runs on :5173 and the FastAPI app on :8000.
// This proxy forwards /api/* requests to the backend so we avoid
// CORS issues and keep the frontend code simple (it just calls /api/...).
//
// In production, VITE_API_BASE_URL is set to the deployed API URL
// (e.g. https://taitalumi-api.onrender.com) and the proxy is not used.

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
  },
});
