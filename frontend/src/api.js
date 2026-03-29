// src/api.js

const API_BASE = "http://localhost:8000";

// 260221 서은 - 토큰 가져오기
function getToken() {
  return localStorage.getItem("accessToken");
}

/**
 * 공통 fetch 함수 (토큰 자동 포함)
 */
async function apiFetch(url, options = {}) {
  const token = getToken();

  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  const useAuth = options.auth !== false;

  if (useAuth && token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers,
    body:
      options.body && typeof options.body === "object"
        ? JSON.stringify(options.body)
        : options.body,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }

  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return res.json();
  }

  return null;
}

/**
 * 오픽 세션 시작
 */
export function startSession(payload) {
  return apiFetch("/api/opic/start", {
    method: "POST",
    body: payload,
  });
}

/**
 * 프로필 가져오기
 */
export async function getMyOpicProfile() {
  return apiFetch("/api/opic/profile", {
    method: "GET",
  });
}

/**
 * 턴 진행
 */
export function turnSession(sessionId, userInput) {
  return apiFetch(`/api/opic/sessions/${sessionId}/turn`, {
    method: "POST",
    body: { userInput },
  });
}

/**
 * 세션 조회
 */
export function getSession(sessionId) {
  return apiFetch(`/api/opic/sessions/${sessionId}`);
}

/**
 * 세션 종료
 */
export function endSession(sessionId, payload = {}) {
  return apiFetch(`/api/opic/sessions/${sessionId}/end`, {
    method: "POST",
    body: payload,
  });
}

// 260217 서은 - 로그인
export function loginApi({ email, password }) {
  return apiFetch("/api/auth/login", {
    method: "POST",
    auth: false,
    body: { email, password },
  });
}

// 260217 서은 - 회원가입
export function registerApi({ email, password, name }) {
  return apiFetch("/api/auth/register", {
    method: "POST",
    auth: false,
    body: { email, password, name },
  });
}

// 260217 서은 - 현재 사용자 조회
export function meApi() {
  return apiFetch("/api/auth/me");
}

/* 프로필 저장하기 */
export function saveMyOpicProfile(profile) {
  return apiFetch("/api/opic/profile", {
    method: "POST",
    body: profile,
  });
}