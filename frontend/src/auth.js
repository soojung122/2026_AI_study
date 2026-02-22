const BASE = "http://localhost:8000/api/auth";

const TOKEN_KEY = "accessToken";

/**
 * 토큰 저장
 */
export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

/**
 * 토큰 가져오기
 */
export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

/**
 * 토큰 삭제 (로그아웃)
 */
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

/**
 * 현재 사용자 정보 조회
 * GET /api/auth/me
 */
export async function fetchMe() {
  const token = getToken();

  // 토큰 없으면 로그인 안된 상태
  if (!token) {
    return { ok: false, user: null };
  }

  try {
    const res = await fetch(`${BASE}/me`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    // 토큰이 유효하지 않은 경우
    if (!res.ok) {
      clearToken();
      return { ok: false, user: null };
    }

    const user = await res.json();

    return {
      ok: true,
      user,
    };
  } catch (err) {
    // 네트워크 오류 등
    clearToken();
    return { ok: false, user: null };
  }
}

/**
 * 새로고침 시 로그인 유지용
 */
export async function restoreSession() {
  return await fetchMe();
}