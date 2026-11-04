import { createRouter, createWebHistory } from "vue-router";

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
  },
  {
    path: "/admin",
    name: "admin",
    component: () => import("../pages/Admin.vue"),
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

export default router;
