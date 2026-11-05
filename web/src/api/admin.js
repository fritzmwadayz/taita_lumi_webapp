// Admin API service — all endpoints under /api/admin/*.
// All require admin role (JWT with role='admin').

import api from "./client";

// ── Dashboard stats ──────────────────────────────────────────

export async function getStats() {
  const res = await api.get("/api/admin/stats");
  return res.data;
}

// ── User management ──────────────────────────────────────────

export async function listUsers(params = {}) {
  const res = await api.get("/api/admin/users", { params });
  return res.data;
}

export async function updateUser(userId, { role, is_blocked }) {
  const body = {};
  if (role !== undefined) body.role = role;
  if (is_blocked !== undefined) body.is_blocked = is_blocked;
  const res = await api.patch(`/api/admin/users/${userId}`, body);
  return res.data;
}

// ── Suggestion decide ────────────────────────────────────────

export async function decideSuggestion(suggestionId, decision) {
  const res = await api.post(`/api/admin/suggestions/${suggestionId}/decide`, {
    decision,
  });
  return res.data;
}

// ── Word edit / hide / merge ─────────────────────────────────

export async function editWord(wordId, data) {
  const res = await api.patch(`/api/admin/words/${wordId}`, data);
  return res.data;
}

export async function hideWord(wordId) {
  const res = await api.post(`/api/admin/words/${wordId}/hide`);
  return res.data;
}

export async function mergeWords(sourceId, targetId) {
  const res = await api.post("/api/admin/words/merge", {
    source_id: sourceId,
    target_id: targetId,
  });
  return res.data;
}

// ── Audit log ────────────────────────────────────────────────

export async function getAuditLog(params = {}) {
  const res = await api.get("/api/admin/audit-log", { params });
  return res.data;
}
