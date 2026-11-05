import { defineStore } from "pinia";
import {
  register as apiRegister,
  login as apiLogin,
  loginWithGoogle as apiLoginWithGoogle,
  refreshToken as apiRefreshToken,
  fetchMe as apiFetchMe,
  logout as apiLogout,
} from "../api/auth";

// ── Storage keys ──────────────────────────────────────────────
const ACCESS_TOKEN_KEY = "taitalumi_access_token";
const REFRESH_TOKEN_KEY = "taitalumi_refresh_token";

// ── Refresh state (avoid concurrent refresh calls) ───────────
let refreshPromise = null;

export const useAuthStore = defineStore("auth", {
  state: () => ({
    accessToken: localStorage.getItem(ACCESS_TOKEN_KEY) || null,
    refreshToken: localStorage.getItem(REFRESH_TOKEN_KEY) || null,
    user: null,
    loading: false,
  }),

  getters: {
    isAuthenticated: (state) => !!state.accessToken,
    isAdmin: (state) => state.user?.role === "admin",
    isReviewer: (state) =>
      state.user?.role === "reviewer" || state.user?.role === "admin",
    displayName: (state) =>
      state.user?.display_name || state.user?.email?.split("@")[0] || "User",
  },

  actions: {
    // ── Internal: persist tokens ─────────────────────────────
    _setTokens(accessToken, refreshToken) {
      this.accessToken = accessToken;
      this.refreshToken = refreshToken;
      if (accessToken) {
        localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
      } else {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
      }
      if (refreshToken) {
        localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
      } else {
        localStorage.removeItem(REFRESH_TOKEN_KEY);
      }
    },

    _clearTokens() {
      this.accessToken = null;
      this.refreshToken = null;
      this.user = null;
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
    },

    // ── Public actions ───────────────────────────────────────

    async register(email, password, displayName = null) {
      const tokens = await apiRegister(email, password, displayName);
      this._setTokens(tokens.access_token, tokens.refresh_token);
      await this.fetchMe();
      return tokens;
    },

    async login(email, password) {
      const tokens = await apiLogin(email, password);
      this._setTokens(tokens.access_token, tokens.refresh_token);
      await this.fetchMe();
      return tokens;
    },

    async loginWithGoogle(idToken) {
      const tokens = await apiLoginWithGoogle(idToken);
      this._setTokens(tokens.access_token, tokens.refresh_token);
      await this.fetchMe();
      return tokens;
    },

    async fetchMe() {
      if (!this.accessToken) return null;
      try {
        this.user = await apiFetchMe();
        return this.user;
      } catch (err) {
        // 401 means token is expired — try refresh, or clear
        if (err.response?.status === 401) {
          const refreshed = await this.tryRefresh();
          if (refreshed) {
            this.user = await apiFetchMe();
            return this.user;
          }
          this._clearTokens();
        }
        throw err;
      }
    },

    /**
     * Try to refresh the access token using the stored refresh token.
     * Returns true on success, false on failure.
     * Idempotent — concurrent calls share the same promise.
     */
    async tryRefresh() {
      if (!this.refreshToken) return false;

      // Avoid concurrent refresh calls
      if (refreshPromise) return refreshPromise;

      refreshPromise = (async () => {
        try {
          const tokens = await apiRefreshToken(this.refreshToken);
          this._setTokens(tokens.access_token, tokens.refresh_token);
          return true;
        } catch (err) {
          this._clearTokens();
          return false;
        } finally {
          refreshPromise = null;
        }
      })();

      return refreshPromise;
    },

    async logout() {
      try {
        await apiLogout();
      } catch {
        // Server returns 204, errors are fine — we clear locally anyway
      }
      this._clearTokens();
    },

    /**
     * Called on app startup — if tokens exist, fetch the user.
     * Best-effort; failures clear the tokens.
     */
    async init() {
      if (!this.accessToken) return;
      this.loading = true;
      try {
        await this.fetchMe();
      } catch {
        this._clearTokens();
      } finally {
        this.loading = false;
      }
    },
  },
});
