// Anon session cookie management.
//
// On first visit, the frontend generates a random UUID and stores it
// in localStorage. This UUID is sent as the X-Session-Cookie header
// on every request, so the backend can track anon users for rate
// limiting and audit.
//
// If the user later logs in, the JWT takes precedence (the Axios
// client attaches Authorization: Bearer), but we still send the
// session cookie for continuity.

const ANON_COOKIE_KEY = "taitalumi_anon_cookie";

/**
 * Get or create the anon session cookie.
 * Returns the cookie value (a UUID string).
 */
export function getAnonCookie() {
  let cookie = localStorage.getItem(ANON_COOKIE_KEY);
  if (!cookie) {
    cookie = generateUuid();
    localStorage.setItem(ANON_COOKIE_KEY, cookie);
  }
  return cookie;
}

/**
 * Generate a v4 UUID (browser-native if available, fallback to manual).
 */
function generateUuid() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback (older browsers)
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}
