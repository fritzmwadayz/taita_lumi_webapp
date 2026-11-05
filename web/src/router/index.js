import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";

const routes = [
  { path: "/", name: "home", component: () => import("../pages/Home.vue") },
  {
    path: "/search",
    name: "search",
    component: () => import("../pages/Search.vue"),
  },
  {
    path: "/words/:id",
    name: "word-detail",
    component: () => import("../pages/WordDetail.vue"),
  },
  {
    path: "/suggest",
    name: "suggest",
    component: () => import("../pages/Suggest.vue"),
    meta: { requiresAuth: false }, // anon can suggest
  },
  {
    path: "/suggestions",
    name: "suggestions",
    component: () => import("../pages/Suggestions.vue"),
  },
  {
    path: "/suggestions/:id",
    name: "suggestion-detail",
    component: () => import("../pages/SuggestionDetail.vue"),
  },
  {
    path: "/login",
    name: "login",
    component: () => import("../pages/Login.vue"),
    meta: { guestOnly: true },
  },
  {
    path: "/guide",
    name: "guide",
    component: () => import("../pages/ReadingGuide.vue"),
  },
  {
    path: "/donate",
    name: "donate",
    component: () => import("../pages/Donate.vue"),
  },
  {
    path: "/me",
    name: "profile",
    component: () => import("../pages/Profile.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/admin",
    name: "admin",
    component: () => import("../pages/Admin.vue"),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  // Catch-all 404
  {
    path: "/:pathMatch(.*)*",
    name: "not-found",
    component: () => import("../pages/NotFound.vue"),
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 };
  },
});

// ── Route guard ───────────────────────────────────────────────
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();

  // Init auth store on first navigation (loads user from stored token)
  if (authStore.accessToken && !authStore.user && !authStore.loading) {
    await authStore.init();
  }

  // ── Protected routes ───────────────────────────────────────
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return next({ path: "/login", query: { next: to.fullPath } });
  }

  // ── Admin-only routes ──────────────────────────────────────
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    return next("/");
  }

  // ── Guest-only routes (e.g. /login) — redirect if logged in ─
  if (to.meta.guestOnly && authStore.isAuthenticated) {
    return next("/");
  }

  next();
});

export default router;
