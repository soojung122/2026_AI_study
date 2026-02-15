import React, { useEffect, useMemo, useState } from "react";
import Header from "./Header";
import MainScreen from "./MainScreen";

const uid = () => Math.random().toString(36).slice(2, 10);

const DEFAULT_PROFILE = {
  name: "jung",
  job: "college student",
  city: "Yongin",
  hobbies: ["photo shooting", "cooking"],
  speakingStyle: "natural", // natural | confident | calm
};

const seedSessions = () => ([
  {
    id: "s1",
    title: "OPIc 홈 토픽",
    targetGrade: "IH",
    profile: DEFAULT_PROFILE,
    createdAt: Date.now() - 1000 * 60 * 60,
    updatedAt: Date.now() - 1000 * 60 * 10,
    turns: [
      {
        id: uid(),
        role: "assistant",
        kind: "question",
        content: "Let’s start. Tell me about your home and what you like about it.",
        ts: Date.now() - 1000 * 60 * 9,
      },
      {
        id: uid(),
        role: "user",
        kind: "answer",
        content: "I live in a small apartment in Yongin. I like it because it's quiet and convenient...",
        ts: Date.now() - 1000 * 60 * 8,
      },
      {
        id: uid(),
        role: "assistant",
        kind: "followup",
        content: "Nice. What’s your favorite spot at home, and what do you usually do there?",
        ts: Date.now() - 1000 * 60 * 7,
      },
    ],
    // 결과(나중에 백엔드에서 계산)
    result: null,
  },
]);

export default function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [query, setQuery] = useState("");
  const [sessions, setSessions] = useState(() => {
    const raw = localStorage.getItem("opic_sessions_v1");
    return raw ? JSON.parse(raw) : seedSessions();
  });
  const [activeId, setActiveId] = useState(sessions[0]?.id ?? null);

  useEffect(() => {
    localStorage.setItem("opic_sessions_v1", JSON.stringify(sessions));
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

  const createSession = () => {
    const id = uid();
    const now = Date.now();
    const s = {
      id,
      title: "새 오픽 세션",
      targetGrade: "IH",
      profile: DEFAULT_PROFILE,
      createdAt: now,
      updatedAt: now,
      turns: [
        {
          id: uid(),
          role: "assistant",
          kind: "system",
          content:
            "세션이 시작됐어요. 목표 등급(IM/IH/AL)과 프로필을 확인하고, 질문을 진행합니다.",
          ts: now,
        },
      ],
      result: null,
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

  const updateActiveSession = (patchFn) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === activeId ? patchFn(s) : s))
    );
  };

  return (
    <div className="app-root">
      <Header
        sidebarCollapsed={sidebarCollapsed}
        onToggleSidebar={() => setSidebarCollapsed((v) => !v)}
        onNewSession={createSession}
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
      />
    </div>
  );
}
