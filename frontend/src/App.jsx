import React, { useEffect, useMemo, useState } from "react";
import Header from "./Header";
import MainScreen from "./MainScreen";

// 260221 서은 파일 추가
import Login from "./Login";
import Register from "./Register";
import ProtectedRoute from "./ProtectedRoute";
import PublicOnlyRoute from "./PublicOnlyRoute";

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import { startSession, turnSession, endSession } from "./api";

// 260221 서은 - 경로 관련 라이브러리 추가 +  토큰, 세션연결
import { clearToken, restoreSession } from "./auth";

const uid = () => Math.random().toString(36).slice(2, 10);

const DEFAULT_PROFILE = {
  name: "jung",
  job: "college student",
  city: "Yongin",
  hobbies: ["photo shooting", "cooking"],
  speakingStyle: "natural", // UI용 키
};

const seedSessions = () => [
  {
    id: "s1",
    title: "새 오픽 세션",
    targetGrade: "IH",
    targetCount: 12,
    profile: DEFAULT_PROFILE,
    createdAt: Date.now(),
    updatedAt: Date.now(),
    turns: [],
    result: null,

    // ✅ 백엔드 연동용
    backend: {
      sessionId: null, // int
      profileId: null, // int
      status: "IDLE", // IDLE|RUNNING|ENDED
    },
  },
];

function toApiProfile(p) {
  // 백엔드 schema: speaking_style, hobbies list
  return {
    name: p.name,
    job: p.job,
    city: p.city,
    hobbies: p.hobbies ?? [],
    speaking_style: p.speakingStyle ?? "natural",
  };
}

/** ✅ 기존 오픽 화면(세션 UI)을 컴포넌트로 분리 */
function OpicAppScreen({ onLogout }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [query, setQuery] = useState("");

  const [sessions, setSessions] = useState(() => {
    const raw = localStorage.getItem("opic_sessions_v2");
    return raw ? JSON.parse(raw) : seedSessions();
  });

  const [activeId, setActiveId] = useState(sessions[0]?.id ?? null);

  useEffect(() => {
    localStorage.setItem("opic_sessions_v2", JSON.stringify(sessions));
  }, [sessions]);

  const activeSession = useMemo(
    () => sessions.find((s) => s.id === activeId) ?? null,
    [sessions, activeId]
  );

  const filteredSessions = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = [...sessions].sort((a, b) => b.updatedAt - a.updatedAt);
    if (!q) return list;
    return list.filter((s) => (s.title || "").toLowerCase().includes(q));
  }, [sessions, query]);

  const updateActiveSession = (patchFn) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === activeId ? patchFn(s) : s))
    );
  };

  const createSessionLocal = () => {
    const id = uid();
    const now = Date.now();
    const s = {
      id,
      title: "새 오픽 세션",
      targetGrade: "IH",
      targetCount: 12,
      profile: DEFAULT_PROFILE,
      createdAt: now,
      updatedAt: now,
      turns: [],
      result: null,
      backend: { sessionId: null, profileId: null, status: "IDLE" },
    };
    setSessions((prev) => [s, ...prev]);
    setActiveId(id);
  };

  const deleteSession = (id) => {
    if (!confirm("이 세션을 삭제할까요?")) return;
    setSessions((prev) => prev.filter((s) => s.id !== id));
    if (activeId === id) {
      const remain = sessions.filter((s) => s.id !== id);
      setActiveId(remain[0]?.id ?? null);
    }
  };

  const renameSession = (id) => {
    const s = sessions.find((x) => x.id === id);
    const next = prompt("세션 제목", s?.title ?? "");
    if (next == null) return;
    setSessions((prev) =>
      prev.map((x) =>
        x.id === id
          ? { ...x, title: next.trim() || x.title, updatedAt: Date.now() }
          : x
      )
    );
  };

  /**
   * ✅ 프로필/목표등급 기반으로 백엔드 세션 시작 + 첫 질문을 UI에 반영
   * MainScreen(프로필 탭)에서 호출해야 함.
   */
  const startBackendSession = async ({ goalGrade, targetCount, profile }) => {
    if (!activeSession) throw new Error("활성 세션이 없습니다.");

    // 이미 세션이 RUNNING이면 중복 시작 방지
    if (activeSession.backend?.sessionId) {
      return activeSession.backend.sessionId;
    }

    const payload = {
      goalGrade,
      targetCount,
      profile: toApiProfile(profile),
    };

    const res = await startSession(payload);

    updateActiveSession((s) => ({
      ...s,
      targetGrade: goalGrade,
      targetCount,
      profile,
      updatedAt: Date.now(),
      backend: {
        sessionId: res.sessionId,
        profileId: res.profileId,
        status: "RUNNING",
      },
      turns: [
        ...s.turns,
        {
          id: uid(),
          role: "assistant",
          kind: "question",
          content: res.firstQuestion,
          ts: Date.now(),
        },
      ],
    }));

    return res.sessionId;
  };

  /**
   * ✅ 채팅 전송 -> 백엔드 turn -> 다음 질문을 UI에 append
   * MainScreen(채팅 탭 전송 버튼/엔터)에서 호출해야 함.
   */
  const sendTurn = async (userText) => {
    if (!activeSession) throw new Error("활성 세션이 없습니다.");
    const text = (userText ?? "").trim();
    if (!text) return;

    updateActiveSession((s) => ({
      ...s,
      updatedAt: Date.now(),
      turns: [
        ...s.turns,
        { id: uid(), role: "user", kind: "answer", content: text, ts: Date.now() },
      ],
    }));

    let backendSessionId = activeSession.backend?.sessionId;
    if (!backendSessionId) {
      backendSessionId = await startBackendSession({
        goalGrade: activeSession.targetGrade ?? "IH",
        targetCount: activeSession.targetCount ?? 12,
        profile: activeSession.profile ?? DEFAULT_PROFILE,
      });
    }

    const res = await turnSession(backendSessionId, text);

    updateActiveSession((s) => ({
      ...s,
      updatedAt: Date.now(),
      turns: [
        ...s.turns,
        {
          id: uid(),
          role: "assistant",
          kind: "followup",
          content: res.questionText,
          ts: Date.now(),
        },
      ],
    }));
  };

  /**
   * ✅ 세션 종료(채점)
   */
  const endBackendSession = async ({ force = false } = {}) => {
    if (!activeSession?.backend?.sessionId) {
      throw new Error("종료할 백엔드 세션이 없습니다. 먼저 세션을 시작하세요.");
    }
    const report = await endSession(activeSession.backend.sessionId, { force });

    updateActiveSession((s) => ({
      ...s,
      updatedAt: Date.now(),
      backend: { ...s.backend, status: "ENDED" },
      result: report?.report ?? report,
    }));
  };

  return (
    <div className="app-root">
      <Header
        sidebarCollapsed={sidebarCollapsed}
        onToggleSidebar={() => setSidebarCollapsed((v) => !v)}
        onNewSession={createSessionLocal}
        onLogout={onLogout}
      />

      <MainScreen
        sidebarCollapsed={sidebarCollapsed}
        query={query}
        setQuery={setQuery}
        sessions={filteredSessions}
        activeId={activeId}
        setActiveId={setActiveId}
        onDeleteSession={deleteSession}
        onRenameSession={renameSession}
        activeSession={activeSession}
        updateActiveSession={updateActiveSession}
        onStartSession={startBackendSession}
        onSendTurn={sendTurn}
        onEndSession={endBackendSession}
      />
    </div>
  );
}

export default function App() {
  const [booting, setBooting] = useState(true);
  const [isAuthed, setIsAuthed] = useState(false);
  const [user, setUser] = useState(null);

  // 260221 서은 - 토큰 기반 세션 복구
  const boot = async () => {
    const { ok, user } = await restoreSession();
    setIsAuthed(ok);
    setUser(user);
    setBooting(false);
  };

  useEffect(() => {
    boot();
  }, []);

  // 260221 서은 - 로그아웃 시 토큰 제거 + 상태 초기화
  const handleLogout = () => {
    clearToken();
    setIsAuthed(false);
    setUser(null);
  };

  if (booting) return <div style={{ padding: 20 }}>로딩중...</div>;

  return (
    <BrowserRouter>
      <Routes>
        {/* 로그인 여부에 따라 바로 메인스크린으로 */}
        <Route path="/" element={<Navigate to={isAuthed ? "/MainScreen" : "/login"} replace />} />

        <Route
          path="/login"
          element={
            <PublicOnlyRoute isAuthed={isAuthed}>
              <Login onLoginSuccess={boot} />
            </PublicOnlyRoute>
          }
        />

        <Route
          path="/register"
          element={
            <PublicOnlyRoute isAuthed={isAuthed}>
              <Register />
            </PublicOnlyRoute>
          }
        />

        {/* ✅ 메인스크린(=오픽 화면) */}
        <Route
          path="/MainScreen"
          element={
            <ProtectedRoute isAuthed={isAuthed}>
              <OpicAppScreen onLogout={handleLogout} />
            </ProtectedRoute>
          }
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}