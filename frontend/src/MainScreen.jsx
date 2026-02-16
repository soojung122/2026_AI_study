import React, { useEffect, useMemo, useRef, useState } from "react";
import { startSession, turnSession, endSession } from "./api";

const uid = () => Math.random().toString(36).slice(2, 10);

function formatTime(ts) {
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function truncate(s, n = 28) {
  if (!s) return "";
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

function toApiProfile(p) {
  return {
    name: p.name,
    job: p.job,
    city: p.city,
    hobbies: p.hobbies ?? [],
    speaking_style: p.speakingStyle ?? "natural",
  };
}

function Bubble({ role, content, meta }) {
  const isUser = role === "user";
  return (
    <div className={`msg-row ${isUser ? "right" : "left"}`}>
      <div className={`avatar ${isUser ? "me" : "ai"}`}>{isUser ? "ME" : "AI"}</div>
      <div className={`bubble ${isUser ? "user" : "assistant"}`}>
        <div className="bubble-text">{content}</div>
        {meta ? <div className="bubble-meta">{meta}</div> : null}
      </div>
    </div>
  );
}

function Sidebar({
  collapsed,
  query,
  setQuery,
  sessions,
  activeId,
  setActiveId,
  onRenameSession,
  onDeleteSession,
}) {
  return (
    <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
      <div className="sidebar-search">
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="세션 검색…" />
      </div>

      <div className="sidebar-list">
        {sessions.map((s) => (
          <button
            key={s.id}
            className={`session-item ${s.id === activeId ? "active" : ""}`}
            onClick={() => setActiveId(s.id)}
          >
            <div className="session-title">{truncate(s.title)}</div>
            <div className="session-sub">
              {s.targetGrade} · {new Date(s.updatedAt).toLocaleDateString()}
            </div>
            <div className="session-actions" onClick={(e) => e.stopPropagation()}>
              <button className="icon-btn small" onClick={() => onRenameSession(s.id)} title="rename">
                ✎
              </button>
              <button className="icon-btn small" onClick={() => onDeleteSession(s.id)} title="delete">
                🗑
              </button>
            </div>
          </button>
        ))}
      </div>
    </aside>
  );
}

function SettingsPanel({ session, onChange }) {
  const profile = session.profile;

  const set = (key, val) =>
    onChange((s) => ({
      ...s,
      updatedAt: Date.now(),
      [key]: val,
    }));

  const setProfile = (k, v) =>
    onChange((s) => ({
      ...s,
      updatedAt: Date.now(),
      profile: { ...s.profile, [k]: v },
    }));

  return (
    <div className="panel">
      <div className="panel-title">세션 설정</div>

      <div className="form-row">
        <label>목표 등급</label>
        <select value={session.targetGrade} onChange={(e) => set("targetGrade", e.target.value)}>
          <option value="IM">IM</option>
          <option value="IH">IH</option>
          <option value="AL">AL</option>
        </select>
      </div>

      <div className="form-row">
        <label>이름</label>
        <input value={profile.name} onChange={(e) => setProfile("name", e.target.value)} />
      </div>
      <div className="form-row">
        <label>직업/역할</label>
        <input value={profile.job} onChange={(e) => setProfile("job", e.target.value)} />
      </div>
      <div className="form-row">
        <label>도시</label>
        <input value={profile.city} onChange={(e) => setProfile("city", e.target.value)} />
      </div>
      <div className="form-row">
        <label>취미 (콤마로 구분)</label>
        <input
          value={profile.hobbies.join(", ")}
          onChange={(e) =>
            setProfile(
              "hobbies",
              e.target.value.split(",").map((x) => x.trim()).filter(Boolean)
            )
          }
        />
      </div>
      <div className="form-row">
        <label>말하기 톤</label>
        <select value={profile.speakingStyle} onChange={(e) => setProfile("speakingStyle", e.target.value)}>
          <option value="natural">natural</option>
          <option value="confident">confident</option>
          <option value="calm">calm</option>
        </select>
      </div>

      <div className="hint">
        * 이제부터 “턴 진행”은 백엔드(/api/opic/turn)로 수행합니다. (평가 JSON은 다음 단계에서 추가)
      </div>
    </div>
  );
}

function ResultPanel({ session }) {
  const turns = session.turns || [];
  const evals = turns.filter((t) => t.kind === "eval").map((t) => t.evalJson);

  const avg = useMemo(() => {
    if (!evals.length) return null;
    const keys = ["fluency", "coherence", "lexical", "grammar", "pronunciation_proxy"];
    const sums = Object.fromEntries(keys.map((k) => [k, 0]));
    for (const e of evals) {
      for (const k of keys) sums[k] += e?.scores?.[k] ?? 0;
    }
    const out = {};
    for (const k of keys) out[k] = Math.round((sums[k] / evals.length) * 10) / 10;
    const total = keys.reduce((a, k) => a + out[k], 0) / keys.length;
    out.total = Math.round(total * 10) / 10;
    return out;
  }, [evals]);

  const inferredBand = useMemo(() => {
    if (!avg) return null;
    if (avg.total >= 4.0) return "AL";
    if (avg.total >= 3.0) return "IH";
    return "IM";
  }, [avg]);

  return (
    <div className="panel">
      <div className="panel-title">결과(임시)</div>
      {!avg ? (
        <div className="muted">아직 평가 데이터가 없습니다. (백엔드 평가 연동 전)</div>
      ) : (
        <>
          <div className="result-kpi">
            <div className="kpi">
              <div className="kpi-label">추정 등급</div>
              <div className="kpi-value">{inferredBand}</div>
            </div>
            <div className="kpi">
              <div className="kpi-label">평균 점수</div>
              <div className="kpi-value">{avg.total}/5</div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}


export default function MainScreen() {
  // if (!active.profile?.name || !active.profile?.job) {
  // throw new Error("프로필의 name/job를 먼저 입력하세요.");
  // }

  const [sessions, setSessions] = useState(() => [
    {
      id: uid(),
      title: "OPIc Practice",
      targetGrade: "IH",
      updatedAt: Date.now(),
      // 백엔드와 연결되는 식별자(지금 단계에서는 생성만 받고 저장)
      serverSessionId: null,
      serverProfileId: null,
      profile: {
        name: "",
        job: "",
        city: "",
        hobbies: [],
        speakingStyle: "natural",
      },
      turns: [],
    },
  ]);

  const [activeId, setActiveId] = useState(sessions[0].id);
  const active = sessions.find((s) => s.id === activeId) ?? sessions[0];

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [query, setQuery] = useState("");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [activeTab, setActiveTab] = useState("chat");

  const listFiltered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return sessions;
    return sessions.filter((s) => (s.title || "").toLowerCase().includes(q));
  }, [sessions, query]);

  const scrollRef = useRef(null);

  const updateActiveSession = (updater) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === activeId ? (typeof updater === "function" ? updater(s) : updater) : s))
    );
  };

  const onRenameSession = (id) => {
    const title = prompt("새 세션 이름", sessions.find((s) => s.id === id)?.title ?? "");
    if (!title) return;
    setSessions((prev) =>
      prev.map((s) => (s.id === id ? { ...s, title, updatedAt: Date.now() } : s))
    );
  };

  const onDeleteSession = (id) => {
    if (!confirm("세션을 삭제할까요?")) return;
    setSessions((prev) => prev.filter((s) => s.id !== id));
    if (activeId === id) {
      const remaining = sessions.filter((s) => s.id !== id);
      if (remaining.length) setActiveId(remaining[0].id);
    }
  };

  const onCreateSession = () => {
    const id = uid();
    const now = Date.now();
    setSessions((prev) => [
      {
        id,
        title: "New Session",
        targetGrade: "IH",
        updatedAt: now,
        serverSessionId: null,
        serverProfileId: null,
        profile: { name: "", job: "", city: "", hobbies: [], speakingStyle: "natural" },
        turns: [],
      },
      ...prev,
    ]);
    setActiveId(id);
  };

  const appendTurn = (role, content) => {
    updateActiveSession((s) => ({
      ...s,
      updatedAt: Date.now(),
      turns: [...(s.turns ?? []), { id: uid(), role, content, ts: Date.now() }],
    }));
    // 간단 스크롤(있으면)
    setTimeout(() => {
      if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }, 0);
  };

const runTurn = async () => {
  if (!active) return;

  const userText = input.trim();
  if (!userText) return;

  setErr("");
  setLoading(true);

  // ✅ 사용자 답변 먼저 UI에 반영
  appendTurn("user", userText);

  try {
    let serverSessionId = active.serverSessionId;
    let serverProfileId = active.serverProfileId;

    // ✅ 세션이 아직 없으면 먼저 startSession (firstQuestion까지 받는 /api/opic/start 기준)
    if (!serverSessionId) {
      const started = await startSession({
        goalGrade: active.targetGrade,
        targetCount: 12,
        profile: toApiProfile(active.profile),
      });
      // started: { profileId, sessionId, firstQuestion, turnIndex }

      serverSessionId = started.sessionId;
      serverProfileId = started.profileId;

      updateActiveSession((s) => ({
        ...s,
        serverSessionId,
        serverProfileId,
        updatedAt: Date.now(),
      }));

      // ✅ 첫 질문을 UI에 반영 (start에서 내려줄 때)
      if (started.firstQuestion) {
        appendTurn("interviewer", started.firstQuestion);
      }
    }

    // ✅ 턴 진행: 두 번째 인자는 "문자열 userInput" 이어야 함
    const data = await turnSession(serverSessionId, userText);
    // data: { sessionId, questionText, turnIndex }

    appendTurn("interviewer", data.questionText);

    setInput("");
  } catch (e) {
    setErr(e?.message ?? "Unknown error");
  } finally {
    setLoading(false);
  }
};


  return (
    <div className="layout">
      <Sidebar
        collapsed={sidebarCollapsed}
        query={query}
        setQuery={setQuery}
        sessions={listFiltered}
        activeId={activeId}
        setActiveId={setActiveId}
        onRenameSession={onRenameSession}
        onDeleteSession={onDeleteSession}
      />

      <main className="main">
        <header className="topbar">
          <button className="icon-btn" onClick={() => setSidebarCollapsed((v) => !v)} title="toggle sidebar">
            ☰
          </button>
          <div className="topbar-title">{active?.title ?? "Session"}</div>
          <div className="topbar-tabs">
            <button className={`tab-btn ${activeTab === "chat" ? "active" : ""}`} onClick={() => setActiveTab("chat")}>채팅</button>
            <button className={`tab-btn ${activeTab === "profile" ? "active" : ""}`} onClick={() => setActiveTab("profile")}>프로필 생성</button>
          </div>
          <div className="topbar-actions">
            <button
              className="btn"
              onClick={async () => {
                if (!active?.serverSessionId) return;
                setErr("");
                setLoading(true);
                try {
                  const res = await endSession(active.serverSessionId, { force: false });
                  appendTurn("interviewer", "=== SESSION REPORT ===");
                  appendTurn("interviewer", JSON.stringify(res.report ?? res, null, 2));
                } catch (e) {
                  setErr(e?.message ?? "Unknown error");
                } finally {
                  setLoading(false);
                }
              }}

              disabled={loading || !active?.serverSessionId}
            >
              세션 종료
            </button>

          </div>
        </header>

        <div className="content">
          {activeTab === "chat" ? (
            <>
              <section className="chat">
                <div className="chat-stream" ref={scrollRef}>
                  {(active?.turns ?? []).map((t) => (
                  <Bubble
                    key={t.id}
                    role={t.role === "interviewer" ? "assistant" : t.role}             // "user" | "interviewer"
                    content={t.content}
                    meta={formatTime(t.ts)}
                  />
                ))}

                </div>

                <div className="chat-input">
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    rows={2}
                    placeholder="내 답변을 입력하세요…"

                  />
                  <button className="btn primary" onClick={runTurn} disabled={loading}>
                    {loading ? "생성 중..." : "턴 진행"}
                  </button>
                </div>

                {err ? <div className="error">Error: {err}</div> : null}
              </section>

              <aside className="sidepanels">
                {active ? <ResultPanel session={active} /> : null}
              </aside>
            </>
          ) : (
            // Profile tab: show SettingsPanel prominently
            <section className="profile-panel">
              {active ? (
                <SettingsPanel session={active} onChange={(updater) => updateActiveSession(updater)} />
              ) : null}
            </section>
          )}
        </div>
      </main>
    </div>
  );
}
