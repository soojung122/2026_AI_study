// src/api.js

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

  // ✅ auth 옵션이 false면 토큰을 안 붙임 (로그인/회원가입 등에 사용)
  const useAuth = options.auth !== false;

  // 토큰 자동 포함
  if (useAuth && token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(url, {
    ...options,
    headers,

    // body가 객체면 JSON 변환
    body:
      options.body && typeof options.body === "object"
        ? JSON.stringify(options.body)
        : options.body,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }

  return res.json();
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
    auth: false, // ✅ 로그인 요청에는 토큰 불필요
    body: { email, password },
  });
}

// 260217 서은 - 회원가입
export function registerApi({ email, password, name }) {
  return apiFetch("/api/auth/register", {
    method: "POST",
    auth: false, // ✅ 회원가입 요청에는 토큰 불필요
    body: { email, password, name },
  });
}

// 260217 서은 - 현재 사용자 조회
export function meApi() {
  return apiFetch("/api/auth/me");
}