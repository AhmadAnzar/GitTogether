// Thin wrapper around the GitTogether REST API. Nginx (Docker/K8s) or Vite (dev) proxies /api.
// The session lives in an httpOnly cookie that the browser sends automatically (same origin).
const PROFILES = '/api/profiles';
const AUTH = '/api/auth';
const CONNECTIONS = '/api/connections';

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(url, options = {}) {
  const isJson = typeof options.body === 'string';
  const res = await fetch(url, {
    credentials: 'same-origin',
    ...options,
    headers: isJson ? { 'Content-Type': 'application/json', ...options.headers } : options.headers,
  });
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === 'string') message = body.detail;
      else if (Array.isArray(body.detail)) {
        message = body.detail.map((d) => `${d.loc?.at(-1)}: ${d.msg.replace(/^Value error, /, '')}`).join(' · ');
      }
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(message, res.status);
  }
  return res.status === 204 ? null : res.json();
}

const json = (method, body) => ({ method, body: JSON.stringify(body) });

// ---------- profiles ----------

export function listProfiles({ q, skill, availability } = {}) {
  const params = new URLSearchParams();
  if (q) params.set('q', q);
  if (skill) params.set('skill', skill);
  if (availability && availability !== 'ALL') params.set('availability', availability);
  const qs = params.toString();
  return request(qs ? `${PROFILES}?${qs}` : PROFILES);
}

export const getStats = () => request(`${PROFILES}/stats`);
export const getProfile = (id) => request(`${PROFILES}/${id}`);
export const createProfile = (data) => request(PROFILES, json('POST', data));
export const updateProfile = (id, data) => request(`${PROFILES}/${id}`, json('PUT', data));
export const deleteProfile = (id) => request(`${PROFILES}/${id}`, { method: 'DELETE' });

// ---------- resume ----------

export const resumeUrl = (profileId) => `${PROFILES}/${profileId}/resume`;

export function uploadResume(profileId, file) {
  const form = new FormData();
  form.append('file', file);
  // No Content-Type header: the browser sets multipart/form-data with the right boundary.
  return request(resumeUrl(profileId), { method: 'PUT', body: form });
}

export const deleteResume = (profileId) => request(resumeUrl(profileId), { method: 'DELETE' });

// ---------- accounts ----------

export const register = (email, password) => request(`${AUTH}/register`, json('POST', { email, password }));
export const login = (email, password) => request(`${AUTH}/login`, json('POST', { email, password }));
export const logout = () => request(`${AUTH}/logout`, { method: 'POST' });

/** The logged-in user, or null when logged out. */
export async function me() {
  try {
    return await request(`${AUTH}/me`);
  } catch (err) {
    if (err.status === 401) return null;
    throw err;
  }
}

// ---------- connections ----------

export const listConnections = () => request(CONNECTIONS);
export const listRequests = () => request(`${CONNECTIONS}/requests`);
export const sendRequest = (userId) => request(`${CONNECTIONS}/requests`, json('POST', { user_id: userId }));
export const acceptRequest = (id) => request(`${CONNECTIONS}/requests/${id}/accept`, { method: 'POST' });
export const declineRequest = (id) => request(`${CONNECTIONS}/requests/${id}/decline`, { method: 'POST' });
export const cancelRequest = (id) => request(`${CONNECTIONS}/requests/${id}`, { method: 'DELETE' });
export const removeConnection = (userId) => request(`${CONNECTIONS}/${userId}`, { method: 'DELETE' });
