import { defineStore } from "pinia";
import api from "../api/client";

// ── Auth store (stub for Phase 2) ─────────────────────────────
//
// This will be fleshed out with real register/login/logout actions
// when we build the auth endpoints. For Phase 0b it just tracks
// whether a token exists in localStorage.

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: localStorage.getItem("taitalumi_token") || null,
    user: null,
  }),

  getters: {
    isAuthenticated: (state) => !!state.token,
  },

  actions: {
    // Phase 2: async register(email, password)
    // Phase 2: async login(email, password)
    // Phase 2: async loginWithGoogle(idToken)
    // Phase 2: async fetchMe()
    // Phase 2: async logout()

    _setToken(token) {
      this.token = token;
      if (token) {
        localStorage.setItem("taitalumi_token", token);
      } else {
        localStorage.removeItem("taitalumi_token");
      }
    },
  },
});
