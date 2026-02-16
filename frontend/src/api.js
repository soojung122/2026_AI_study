// src/api.js
async function apiFetch(url, options) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

export async function startSession(payload) {
  const res = await fetch("/api/opic/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function turnSession(sessionId, userInput) {
  const res = await fetch(`/api/opic/sessions/${sessionId}/turn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ userInput }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getSession(sessionId) {
  const res = await fetch(`/api/opic/sessions/${sessionId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function endSession(sessionId, payload = {}) {
  return apiFetch(`/api/opic/sessions/${sessionId}/end`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
