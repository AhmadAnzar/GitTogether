// Thin wrapper around the GitTogether REST API. Nginx (Docker/K8s) or Vite (dev) proxies /api.
const BASE = '/api/profiles';

async function request(url, options = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
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
    throw new Error(message);
  }
  return res.status === 204 ? null : res.json();
}

export function listProfiles({ q, skill, availability } = {}) {
  const params = new URLSearchParams();
  if (q) params.set('q', q);
  if (skill) params.set('skill', skill);
  if (availability && availability !== 'ALL') params.set('availability', availability);
  const qs = params.toString();
  return request(qs ? `${BASE}?${qs}` : BASE);
}

export const getStats = () => request(`${BASE}/stats`);
export const createProfile = (data) => request(BASE, { method: 'POST', body: JSON.stringify(data) });
export const updateProfile = (id, data) => request(`${BASE}/${id}`, { method: 'PUT', body: JSON.stringify(data) });
export const deleteProfile = (id) => request(`${BASE}/${id}`, { method: 'DELETE' });
