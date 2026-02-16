import React, { useEffect, useMemo, useState } from "react";
import Header from "./Header";
import MainScreen from "./MainScreen";
import { startSession, turnSession, endSession } from "./api";

const uid = () => Math.random().toString(36).slice(2, 10);

const DEFAULT_PROFILE = {
  name: "jung",
  job: "college student",
  city: "Yongin",
  hobbies: ["photo shooting", "cooking"],
  speakingStyle: "natural", // UI용 키
};

const seedSessions = () => ([
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
      sessionId: null,  // int
      profileId: null,  // int
      status: "IDLE",   // IDLE|RUNNING|ENDED
    },
  },
]);

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

export default function App() {
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
        x.id === id ? { ...x, title: next.trim() || x.title, updatedAt: Date.now() } : x
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
    // res: { profileId, sessionId, firstQuestion, turnIndex }

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

    // 1) 사용자 메시지 즉시 append
    updateActiveSession((s) => ({
      ...s,
      updatedAt: Date.now(),
      turns: [
        ...s.turns,
        { id: uid(), role: "user", kind: "answer", content: text, ts: Date.now() },
      ],
    }));

    // 2) 백엔드 sessionId 없으면 먼저 시작
    let backendSessionId = activeSession.backend?.sessionId;
    if (!backendSessionId) {
      backendSessionId = await startBackendSession({
        goalGrade: activeSession.targetGrade ?? "IH",
        targetCount: activeSession.targetCount ?? 12,
        profile: activeSession.profile ?? DEFAULT_PROFILE,
      });
    }

    // 3) 턴 진행
    const res = await turnSession(backendSessionId, text);
    // res: { sessionId, questionText, turnIndex }

    // 4) 다음 질문 append
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
      result: report?.report ?? report, // 백엔드 응답 형태에 맞춰 유연 처리
    }));
  };

  return (
    <div className="app-root">
      <Header
        sidebarCollapsed={sidebarCollapsed}
        onToggleSidebar={() => setSidebarCollapsed((v) => !v)}
        onNewSession={createSessionLocal}
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
        // ✅ 새로 추가: UI가 호출해야 실제로 움직임
        onStartSession={startBackendSession}
        onSendTurn={sendTurn}
        onEndSession={endBackendSession}
      />
    </div>
  );
}
