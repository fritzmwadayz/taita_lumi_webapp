// Auth API service — endpoints under /api/auth.

import api from "./client";

/**
 * @typedef {Object} TokenResponse
 * @property {string} access_token
 * @property {string} refresh_token
 * @property {string} token_type
 * @property {number} expires_in
 */

/**
 * @typedef {Object} UserResponse
 * @property {string} id
 * @property {string} email
 * @property {string|null} display_name
 * @property {string} role
 * @property {string} created_at
 * @property {string|null} last_seen_at
 */

/**
 * Register with email + password.
 * @param {string} email
 * @param {string} password
 * @param {string|null} [displayName]
 * @returns {Promise<TokenResponse>}
 */
export async function register(email, password, displayName = null) {
  const body = { email, password };
  if (displayName) body.display_name = displayName;
  const res = await api.post("/api/auth/register", body);
  return res.data;
}

/**
 * Login with email + password.
 * @param {string} email
 * @param {string} password
 * @returns {Promise<TokenResponse>}
 */
export async function login(email, password) {
  const res = await api.post("/api/auth/login", { email, password });
  return res.data;
}

/**
 * Exchange a Google ID token for our JWT pair.
 * @param {string} idToken - Google ID token from Google Identity Services
 * @returns {Promise<TokenResponse>}
 */
export async function loginWithGoogle(idToken) {
  const res = await api.post("/api/auth/oauth/google", { id_token: idToken });
  return res.data;
}

/**
 * Exchange a refresh token for a new access + refresh token pair.
 * @param {string} refreshToken
 * @returns {Promise<TokenResponse>}
 */
export async function refreshToken(refreshToken) {
  const res = await api.post("/api/auth/refresh", { refresh_token: refreshToken });
  return res.data;
}

/**
 * Get the current user's profile. Requires Authorization header.
 * @returns {Promise<UserResponse>}
 */
export async function fetchMe() {
  const res = await api.get("/api/auth/me");
  return res.data;
}

/**
 * Logout (server returns 204, client discards tokens).
 * @returns {Promise<void>}
 */
export async function logout() {
  await api.post("/api/auth/logout");
}
