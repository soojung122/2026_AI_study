import React, { useEffect, useMemo, useRef, useState } from "react";

const uid = () => Math.random().toString(36).slice(2, 10);

function formatTime(ts) {
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function truncate(s, n = 28) {
  if (!s) return "";
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

/** === MOCK API ===
 * 나중에 여기만 실제 API로 교체:
 * - POST /api/sessions (start)
 * - POST /api/sessions/:id/turns (answer -> eval + followup)
 * - GET /api/sessions/:id/result
 */
async function mockApiTurn({ targetGrade, profile, history, userAnswer }) {
  await new Promise((r) => setTimeout(r, 600));

  // 아주 단순한 mock 파생질문/평가 (UI 개발용)
  const followUps = [
    "Can you describe a typical day at home?",
    "What changes would you like to make to your home in the future?",
    "Tell me about a memorable moment you had at home.",
    "How is your home different from where you lived before?",
  ];
  const q = followUps[Math.floor(Math.random() * followUps.length)];

  const evalJson = {
    scores: {
      fluency: 3,
      coherence: 3,
      lexical: 3,
      grammar: 3,
      pronunciation_proxy: 2,
    },
    bandEstimate: targetGrade === "AL" ? "IH" : targetGrade,
    strengths: ["Clear structure", "Good detail"],
    fixes: ["More connectors (because/so/however)", "Tense consistency"],
    nextFocus: "Add a mini-story (when/where/what happened).",
  };

  return { followUpQuestion: q, evalJson };
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
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="세션 검색…"
        />
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

  const set = (key, val) => onChange((s) => ({
    ...s,
    updatedAt: Date.now(),
    [key]: val
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
        * 프론트 MVP에서는 설정만 저장하고, 실제 질문 생성/평가는 mock API가 처리합니다.
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
      for (const k of keys) sums[k] += (e?.scores?.[k] ?? 0);
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
        <div className="muted">아직 평가 데이터가 없습니다. 대화를 진행하세요.</div>
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

          <div className="result-grid">
            <div className="card">
              <div className="card-label">Fluency</div>
              <div className="card-value">{avg.fluency}</div>
            </div>
            <div className="card">
              <div className="card-label">Coherence</div>
              <div className="card-value">{avg.coherence}</div>
            </div>
            <div className="card">
              <div className="card-label">Lexical</div>
              <div className="card-value">{avg.lexical}</div>
            </div>
            <div className="card">
              <div className="card-label">Grammar</div>
              <div className="card-value">{avg.grammar}</div>
            </div>
            <div className="card">
              <div className="card-label">Pronun(Proxy)</div>
              <div className="card-value">{avg.pronunciation_proxy}</div>
            </div>
          </div>

          <div className="hint">
            * 이 등급/점수는 mock 평가를 평균낸 것입니다. 백엔드 연동 시 Rater JSON을 기반으로 실제 산정 로직을 적용하세요.
          </div>
        </>
      )}
    </div>
  );
}

export default function MainScreen({
  sidebarCollapsed,
  query,
  setQuery,
  sessions,
  activeId,
  setActiveId,
  onDeleteSession,
  onRenameSession,
  activeSession,
  updateActiveSession,
}) {
  const [tab, setTab] = useState("chat"); // chat | settings | result
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);

  const scrollRef = useRef(null);
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [activeId, activeSession?.turns?.length]);

  const send = async () => {
    if (!activeSession) return;
    const text = draft.trim();
    if (!text || busy) return;

    setBusy(true);
    setDraft("");

    const userMsg = {
      id: uid(),
      role: "user",
      kind: "answer",
      content: text,
      ts: Date.now(),
    };

    // append user message
    updateActiveSession((s) => ({
      ...s,
      updatedAt: Date.now(),
      turns: [...s.turns, userMsg],
      title: s.title === "새 오픽 세션" ? truncate(text, 24) : s.title,
    }));

    // call API -> eval + followup
    try {
      const history = activeSession.turns.map((t) => ({ role: t.role, content: t.content }));
      const { followUpQuestion, evalJson } = await mockApiTurn({
        targetGrade: activeSession.targetGrade,
        profile: activeSession.profile,
        history,
        userAnswer: text,
      });

      const evalTurn = {
        id: uid(),
        role: "assistant",
        kind: "eval",
        content:
          `평가(임시): ${evalJson.bandEstimate} · ` +
          `F${evalJson.scores.fluency}/C${evalJson.scores.coherence}/L${evalJson.scores.lexical}/G${evalJson.scores.grammar}`,
        evalJson,
        ts: Date.now(),
      };

      const followUp = {
        id: uid(),
        role: "assistant",
        kind: "followup",
        content: followUpQuestion,
        ts: Date.now(),
      };

      updateActiveSession((s) => ({
        ...s,
        updatedAt: Date.now(),
        turns: [...s.turns, evalTurn, followUp],
      }));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="main">
      <Sidebar
        collapsed={sidebarCollapsed}
        query={query}
        setQuery={setQuery}
        sessions={sessions}
        activeId={activeId}
        setActiveId={setActiveId}
        onRenameSession={onRenameSession}
        onDeleteSession={onDeleteSession}
      />

      <section className="content">
        <div className="content-top">
          <div className="tabs">
            <button className={`tab ${tab === "chat" ? "active" : ""}`} onClick={() => setTab("chat")}>
              Chat
            </button>
            <button className={`tab ${tab === "settings" ? "active" : ""}`} onClick={() => setTab("settings")}>
              Settings
            </button>
            <button className={`tab ${tab === "result" ? "active" : ""}`} onClick={() => setTab("result")}>
              Result
            </button>
          </div>

          <div className="content-title">
            {activeSession ? activeSession.title : "세션이 없습니다"}
          </div>
        </div>

        {tab === "settings" && activeSession ? (
          <div className="pane">
            <SettingsPanel session={activeSession} onChange={updateActiveSession} />
          </div>
        ) : tab === "result" && activeSession ? (
          <div className="pane">
            <ResultPanel session={activeSession} />
          </div>
        ) : (
          <>
            <div className="chat" ref={scrollRef}>
              {!activeSession ? (
                <div className="empty">
                  왼쪽에서 세션을 선택하거나 상단 New Session으로 시작하세요.
                </div>
              ) : (
                activeSession.turns.map((m) => (
                  <Bubble
                    key={m.id}
                    role={m.role}
                    content={m.content}
                    meta={`${m.kind} · ${formatTime(m.ts)}`}
                  />
                ))
              )}
            </div>

            <div className="composer">
              <div className="composer-inner">
                <textarea
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder="답변을 입력하세요… (Enter: 전송 / Shift+Enter: 줄바꿈)"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      send();
                    }
                  }}
                  disabled={!activeSession || busy}
                />
                <button className="send-btn" onClick={send} disabled={!activeSession || busy || !draft.trim()}>
                  {busy ? "..." : "Send"}
                </button>
              </div>

              <div className="composer-hint">
                * 오픽 대화형: 질문(assistant) → 답변(user) → 평가/파생질문(assistant)
              </div>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
