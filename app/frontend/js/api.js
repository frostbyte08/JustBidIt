/* ── JustBidIt API Client ───────────────────────────────────── */

// In production this points to your Railway backend URL
// Change this to your Railway URL after deploying the backend
const API = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://localhost:8000"
  : "https://checkout-technique-geological-consultants.trycloudflare.com";  // ← UPDATE THIS after Railway deploy

const state = {
  tenderId:  null,
  companyId: null,
  sessionId: null,
  user:      null,
};

function loadState() {
  state.tenderId  = localStorage.getItem("jbi_tender_id");
  state.companyId = localStorage.getItem("jbi_company_id");
  state.sessionId = localStorage.getItem("jbi_session_id");
  try { state.user = JSON.parse(localStorage.getItem("jbi_user")); } catch {}
}

function saveState() {
  if (state.tenderId)  localStorage.setItem("jbi_tender_id",  state.tenderId);
  if (state.companyId) localStorage.setItem("jbi_company_id", state.companyId);
  if (state.sessionId) localStorage.setItem("jbi_session_id", state.sessionId);
  if (state.user)      localStorage.setItem("jbi_user",       JSON.stringify(state.user));
}

function clearState() {
  ["jbi_tender_id","jbi_company_id","jbi_session_id","jbi_user","jbi_token","jbi_company_form"].forEach(k => localStorage.removeItem(k));
  Object.assign(state, { tenderId: null, companyId: null, sessionId: null, user: null });
}

function getToken() { return localStorage.getItem("jbi_token"); }

function authHeaders() {
  const t = getToken();
  return t ? { "Authorization": `Bearer ${t}` } : {};
}

function requireAuth() {
  if (!getToken()) { window.location.href = "login.html"; return false; }
  return true;
}

function redirectIfLoggedIn() {
  const token = getToken();
  if (token && token.length > 20) window.location.href = "dashboard.html";
}

/* ── Helpers ────────────────────────────────────────────────── */
function showToast(msg, type = "success") {
  document.querySelector(".toast")?.remove();
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

async function apiCall(endpoint, options = {}) {
  const res = await fetch(`${API}${endpoint}`, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers || {}) }
  });

  // Token expired — redirect to login
  if (res.status === 401) {
    clearState();
    window.location.href = "login.html";
    return;
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

/* ── Auth ───────────────────────────────────────────────────── */
async function register(email, fullName, password) {
  return apiCall("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, full_name: fullName, password }),
  });
}

async function login(email, password) {
  const data = await apiCall("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  localStorage.setItem("jbi_token", data.access_token);
  const user = await apiCall("/auth/me");
  state.user = user;
  saveState();
  return user;
}

function logout() {
  clearState();
  window.location.href = "login.html";
}

/* ── Tenders ────────────────────────────────────────────────── */
async function uploadTender(file) {
  const form = new FormData();
  form.append("file", file);
  const data = await apiCall("/tenders/upload", { method: "POST", body: form });
  state.tenderId = String(data.id);
  saveState();
  return data;
}

async function getTender(id) { return apiCall(`/tenders/${id}`); }
async function listTenders() { return apiCall("/tenders"); }

/* ── Company ────────────────────────────────────────────────── */
async function saveCompany(payload) {
  const data = await apiCall("/companies", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  state.companyId = String(data.id);
  saveState();
  return data;
}

async function getCompany(id) { return apiCall(`/companies/${id}`); }

/* ── Compliance ─────────────────────────────────────────────── */
async function checkCompliance(tenderId, companyId) {
  return apiCall("/compliance/score", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tender_id: Number(tenderId), company_id: Number(companyId) }),
  });
}

/* ── Draft & Copilot ────────────────────────────────────────── */
async function generateDraft(tenderId, companyId, ctx = null) {
  const body = { tender_id: Number(tenderId), company_id: Number(companyId) };
  if (ctx) body.additional_context = ctx;
  return apiCall("/copilot/generate-draft", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

async function askCopilot(tenderId, question, sessionId = null) {
  const body = { tender_id: Number(tenderId), question };
  if (sessionId) body.session_id = Number(sessionId);
  const data = await apiCall("/copilot/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  state.sessionId = String(data.session_id);
  saveState();
  return data;
}

/* ── Health ─────────────────────────────────────────────────── */
async function healthCheck() {
  try { const r = await fetch(`${API}/health`); return r.ok; }
  catch { return false; }
}
