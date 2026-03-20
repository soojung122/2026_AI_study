import React, { useEffect, useMemo, useRef, useState } from "react";
import { startSession, turnSession, endSession, getMyOpicProfile, saveMyOpicProfile  } from "./api";

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
  const s = p.survey || {};

  return {
    name: "user",
    job: s.occupation || "",
    city: s.residence || "",
    hobbies: s,   // ⭐ survey 전체를 hobbies에 넣음
    speaking_style: p.speakingStyle || "natural",
  };
}

/** ✅ Web Speech API TTS */
function speakText(text, opts = {}) {
  const t = (text ?? "").trim();
  if (!t) return;

  if (!("speechSynthesis" in window)) {
    console.warn("Web Speech API (TTS) not supported");
    return;
  }

  window.speechSynthesis.cancel();

  const utter = new SpeechSynthesisUtterance(t);
  utter.lang = opts.lang || "en-US";
  utter.rate = opts.rate ?? 1.0;
  utter.pitch = opts.pitch ?? 1.0;
  utter.volume = opts.volume ?? 1.0;

  window.speechSynthesis.speak(utter);
}

function stopSpeak() {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
}

/** ✅ Web Speech API STT */
function getSpeechRecognition() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

function Bubble({ role, content, meta, onReplay, showReplay }) {
  const isUser = role === "user";
  return (
    <div className={`msg-row ${isUser ? "right" : "left"}`}>
      <div className={`avatar ${isUser ? "me" : "ai"}`}>{isUser ? "ME" : "AI"}</div>
      <div className={`bubble ${isUser ? "user" : "assistant"}`}>
        <div className="bubble-text">{content}</div>

        <div className="bubble-footer">
          {meta ? <div className="bubble-meta">{meta}</div> : <div />}
          {showReplay ? (
            <button type="button" className="icon-btn small" title="다시 듣기" onClick={onReplay}>
              🔊
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function Sidebar({ collapsed, query, setQuery, sessions, activeId, setActiveId, onRenameSession, onDeleteSession }) {
  return (
    <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
      <div className="sidebar-search">
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="세션 검색…" />
      </div>

      <div className="sidebar-list">
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`session-item ${s.id === activeId ? "active" : ""}`}
            onClick={() => setActiveId(s.id)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                setActiveId(s.id);
              }
            }}
          >
            <div className="session-title">{truncate(s.title)}</div>
            <div className="session-sub">
              {s.targetGrade} · {new Date(s.updatedAt).toLocaleDateString()}
            </div>
            <div className="session-actions" onClick={(e) => e.stopPropagation()}>
              <button
                type="button"
                className="icon-btn small"
                onClick={() => onRenameSession(s.id)}
                title="rename"
              >
                ✎
              </button>
              <button
                type="button"
                className="icon-btn small"
                onClick={() => onDeleteSession(s.id)}
                title="delete"
              >
                🗑
              </button>
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}

function SettingsPanel({ session, onChange, onSave, saving }) {
  const profile = session.profile;

  const survey = profile.survey ?? {
    occupation: "",
    isStudent: "",
    recentCourse: "",
    residence: "",
    leisure: [],
    hobby: [],
    exercise: [],
    travel: [],
  };

  const set = (key, val) =>
    onChange((s) => ({
      ...s,
      updatedAt: Date.now(),
      [key]: val,
    }));

  const setSurvey = (key, value) =>
    onChange((s) => ({
      ...s,
      updatedAt: Date.now(),
      profile: {
        ...s.profile,
        survey: {
          ...s.profile.survey,
          [key]: value,
        },
      },
    }));

  const toggleSurveyArray = (key, item) => {
    const current = survey[key] ?? [];
    const next = current.includes(item)
      ? current.filter((x) => x !== item)
      : [...current, item];

    setSurvey(key, next);
  };

  const leisureGroups = [
  {
    key: "leisure",
    title: "여가 활동",
    items: [
      "영화 보기",
      "클럽/나이트 가기",
      "박물관 가기",
      "주거 개선",
      "해변 가기",
      "스포츠 관람",
      "요리 관련 프로그램 시청",
      "공연 보기",
      "게임하기",
      "캠핑하기",
      "SNS글 올리기",
      "구직 활동",
      "해변 가기",
      "술집 / 바 가기",
      "친구들과 문자 하기",
      "당구 치기",
      "자원 봉사",
      "차 드라이브 하기",
      "시험 대비 과정 수강",
      "뉴스 보거나 듣기",
      "카페 / 커피 전문점 가기",
      "체스",
      "콘서트 보기",
      "TV 시청",
      "쇼핑",
      "음악 감상",
      "리얼리티 쇼 보기",
    ],
  },
  {
    key: "hobby",
    title: "취미 / 관심사",
    items: [
      "아이에게 책 읽어주기",
      "악기 연주하기",
      "독서",
      "사진 촬영하기",
      "글쓰기",
      "요리 하기",
      "신문 읽기",
      "음악 감상하기",
      "애완동물 키우기",
      "그림 그리기",
      "혼자 노래 부르거나 합창",
      "춤추기",
      "주식 투자",
      "여행 관련 잡지나 블로그 읽기",
    ],
  },
  {
    key: "exercise",
    title: "운동",
    items: [
      "농구",
      "야구/소프트볼",
      "축구",
      "미식축구",
      "하키",
      "크로켓",
      "골프",
      "배구",
      "테니스",
      "배드민턴",
      "탁구",
      "수영",
      "자전거",
      "스키/스노보드",
      "아이스 스케이트",
      "태권도",
      "운동 수업 수강하기",
      "조깅",
      "걷기",
      "요가",
      "하이킹, 트레킹",
      "낚시",
      "헬스",
      "운동을 전혀 하지 않음",
    ],
  },
  {
    key: "travel",
    title: "여행 / 휴가",
    items: [
      "국내 출장",
      "회외 출장",
      "집에서 보내는 휴가",
      "국내 여행",
      "해외 여행",
    ],
  },
];

  return (
    <div className="panel">
      <div className="panel-title">오픽 서베이</div>

      <div className="survey-section compact-top-row">
        <div className="compact-field">
          <label>목표 등급</label>
          <select
            value={session.targetGrade}
            onChange={(e) => set("targetGrade", e.target.value)}
          >
            <option value="IM">IM</option>
            <option value="IH">IH</option>
            <option value="AL">AL</option>
          </select>
        </div>

        <div className="compact-field">
          <label>말하기 톤</label>
          <select
            value={profile.speakingStyle ?? "natural"}
            onChange={(e) =>
              onChange((s) => ({
                ...s,
                updatedAt: Date.now(),
                profile: {
                  ...s.profile,
                  speakingStyle: e.target.value,
                },
              }))
            }
          >
            <option value="natural">natural</option>
            <option value="confident">confident</option>
            <option value="calm">calm</option>
          </select>
        </div>
      </div>

      <div className="survey-section">
        <div className="question-title">1. 현재 귀하는 어느 분야에 종사하고 계신가요?</div>
        <div className="form-row">
          <select
            value={survey.occupation}
            onChange={(e) => setSurvey("occupation", e.target.value)}
          >
            <option value="">선택하세요</option>
            <option value="사업 / 회사">사업 / 회사</option>
            <option value="재택근무 / 재택사업">재택근무 / 재택사업</option>
            <option value="교사 / 교육자">교사 / 교육자</option>
            <option value="일 경험 없음">일 경험 없음</option>
          </select>
        </div>
      </div>

      <div className="survey-section">
        <div className="question-title">2. 현재 당신은 학생인가요?</div>
        <div className="form-row">
          <select
            value={survey.isStudent}
            onChange={(e) => setSurvey("isStudent", e.target.value)}
          >
            <option value="">선택하세요</option>
            <option value="예">예</option>
            <option value="아니요">아니요</option>
          </select>
        </div>
      </div>

      <div className="survey-section">
        <div className="question-title">3. 최근 어떤 강의를 수강했습니까?</div>
        <div className="form-row">
          <select
            value={survey.recentCourse}
            onChange={(e) => setSurvey("recentCourse", e.target.value)}
          >
            <option value="">선택하세요</option>
            <option value="학위 과정 수업">학위 과정 수업</option>
            <option value="전문 기술 향상을 위한 평생 학습">전문 기술 향상을 위한 평생 학습</option>
            <option value="어학 수업">어학 수업</option>
            <option value="수강 후 5년 이상 지남">수강 후 5년 이상 지남</option>
          </select>
        </div>
      </div>

      <div className="survey-section">
        <div className="question-title">4. 현재 어디에 살고 계십니까?</div>
        <div className="form-row">
          <select
            value={survey.residence}
            onChange={(e) => setSurvey("residence", e.target.value)}
          >
            <option value="">선택하세요</option>
            <option value="개인 주택이나 아파트에 홀로 거주">개인 주택이나 아파트에 홀로 거주</option>
            <option value="친구 / 룸메이트와 함께 거주">친구 / 룸메이트와 함께 거주</option>
            <option value="가족과 함께 거주">가족과 함께 거주</option>
            <option value="학교 기숙사">학교 기숙사</option>
            <option value="군대 막사 / 군 시설">군대 막사 / 군 시설</option>
          </select>
        </div>
      </div>

      <div className="survey-section">
        <div className="question-title">5. 여가 활동 (여러 개 선택 가능)</div>

        {leisureGroups.map((group) => (
          <div key={group.title} className="leisure-group">
            <div className="leisure-group-title">{group.title}</div>
            <div className="check-grid">
              {group.items.map((item) => (
                <label key={item} className="check-card">
                  <input
                    type="checkbox"
                    checked={(survey[group.key] ?? []).includes(item)}
                    onChange={() => toggleSurveyArray(group.key, item)}
                  />
                  <span>{item}</span>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="survey-save">
        <button
          type="button"
          className="btn primary"
          onClick={onSave}
          disabled={saving}
        >
          {saving ? "저장 중..." : "저장하기"}
        </button>
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
/*
직업: 사업 / 회사

학생 여부: 

최근 강의: 

거주 형태: 

여가 활동: 
*/
export default function MainScreen() {
  

  const [sessions, setSessions] = useState(() => [
    {
      id: uid(),
      title: "OPIc Practice",
      targetGrade: "IH",
      updatedAt: Date.now(),
      serverSessionId: null,
      serverProfileId: null,
      profile: {
        survey: {
          occupation: "",
          isStudent: "",
          recentCourse: "",
          residence: "",
          leisure: [],      // 여가 활동 (외출/활동)
          hobby: [],        // 취미/관심사
          exercise: [],     // 운동
          travel: [],       // 여행
        },
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

  const [profileSaving, setProfileSaving] = useState(false);

  const handleSaveProfile = async () => {
    if (!active) return;

    setProfileSaving(true);

    try {
      const payload = toApiProfile(active.profile);

      const res = await saveMyOpicProfile(payload);

      updateActiveSession((s) => ({
        ...s,
        serverProfileId: res.profileId,
      }));

      alert("프로필 저장 완료");
    } catch (e) {
      alert("저장 실패: " + (e.message || ""));
    } finally {
      setProfileSaving(false);
    }
  };

  /** ✅ STT state */
  const [isRecording, setIsRecording] = useState(false);
  const sttRef = useRef(null);

  // ✅ STT 누적용 버퍼들
  const baseInputRef = useRef("");   // 녹음 시작 시점 input
  const finalBufferRef = useRef(""); // 확정(final) 누적
  const interimRef = useRef("");     // interim(말하는 중)

  // ✅ 마지막 interviewer 질문 저장 (스피커 버튼 재생용)
  const lastQuestionText = useMemo(() => {
    const turns = active?.turns ?? [];
    for (let i = turns.length - 1; i >= 0; i--) {
      if (turns[i].role === "interviewer" && (turns[i].content ?? "").trim()) {
        return turns[i].content;
      }
    }
    return "";
  }, [active?.turns]);

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
    setSessions((prev) => prev.map((s) => (s.id === id ? { ...s, title, updatedAt: Date.now() } : s)));
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
        profile: {
          survey: {
            occupation: "",
            isStudent: "",
            recentCourse: "",
            residence: "",
            leisure: [],      // 여가 활동 (외출/활동)
            hobby: [],        // 취미/관심사
            exercise: [],     // 운동
            travel: [],       // 여행
          },
          speakingStyle: "natural",
        },
        turns: [],
      },
      ...prev,
    ]);
    setActiveId(id);
  };

  // ✅ appendTurn에 옵션을 추가해서 interviewer면 자동 TTS
  const appendTurn = (role, content, options = {}) => {
    updateActiveSession((s) => ({
      ...s,
      updatedAt: Date.now(),
      turns: [...(s.turns ?? []), { id: uid(), role, content, ts: Date.now() }],
    }));

    if (options.speak && role === "interviewer") {
      speakText(content, { lang: "en-US", rate: 1.0, pitch: 1.0 });
    }

    setTimeout(() => {
      if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }, 0);
  };

  /** ✅ STT: 누적 버전 start/stop */
  const startSTT = () => {
    const SR = getSpeechRecognition();
    if (!SR) {
      alert("이 브라우저는 STT(Web Speech API)를 지원하지 않습니다. 크롬(Chrome)에서 시도해 주세요.");
      return;
    }
    if (loading) return;

    setErr("");
    stopSpeak();

    // ✅ 시작 시 버퍼 초기화
    baseInputRef.current = input;
    finalBufferRef.current = "";
    interimRef.current = "";

    const rec = new SR();
    rec.lang = "en-US";        // 필요하면 "ko-KR"
    rec.interimResults = true;
    rec.continuous = true;
    rec.maxAlternatives = 1;

    rec.onresult = (e) => {
      let finalChunk = "";
      let interimChunk = "";

      for (let i = e.resultIndex; i < e.results.length; i++) {
        const transcript = e.results[i][0]?.transcript || "";
        if (e.results[i].isFinal) finalChunk += transcript;
        else interimChunk += transcript;
      }

      // ✅ final은 누적
      if (finalChunk.trim()) {
        const add = finalChunk.trim();
        finalBufferRef.current = (finalBufferRef.current + " " + add).trim();
        interimRef.current = ""; // final 확정되면 interim은 비움
      } else {
        interimRef.current = interimChunk.trim();
      }

      const base = (baseInputRef.current || "").trim();
      const finalAll = (finalBufferRef.current || "").trim();
      const interim = (interimRef.current || "").trim();

      const combined = [base, finalAll, interim].filter(Boolean).join(" ").replace(/\s+/g, " ");
      setInput(combined);
    };

    rec.onerror = (e) => {
      console.error("STT error:", e);
      setErr(`STT error: ${e?.error || "unknown"}`);
      setIsRecording(false);
    };

    rec.onend = () => {
      setIsRecording(false);
      // onend 되어도 finalBufferRef는 이미 input에 반영되어 있으니 그대로 남습니다.
    };

    sttRef.current = rec;
    setIsRecording(true);

    try {
      rec.start();
    } catch (err) {
      console.error(err);
      setIsRecording(false);
    }
  };

  const stopSTT = () => {
    try {
      sttRef.current?.stop();
    } catch (e) {}
    setIsRecording(false);
  };

  const runTurn = async () => {
  if (!active) return;

  const userText = input.trim();
  if (!userText) return;

  setErr("");
  setLoading(true);

  appendTurn("user", userText);

  if (isRecording) stopSTT();

  try {
    let serverSessionId = active.serverSessionId;

    if (!serverSessionId) {
      const started = await startSession({
        goalGrade: active.targetGrade,
        targetCount: 12,
      });

      serverSessionId = started.sessionId;

      updateActiveSession((s) => ({
        ...s,
        serverSessionId: started.sessionId,
        serverProfileId: started.profileId,
        updatedAt: Date.now(),
        profile: started.profile
          ? {
              ...s.profile,
              name: started.profile.name ?? "",
              job: started.profile.job ?? "",
              city: started.profile.city ?? "",
              survey: started.profile.hobbies ?? s.profile.survey,
              speakingStyle: started.profile.speaking_style ?? "natural",
            }
          : s.profile,
      }));

      if (started.firstQuestion) {
        appendTurn("interviewer", started.firstQuestion, { speak: true });
      }
    }

    const data = await turnSession(serverSessionId, userText);
    appendTurn("interviewer", data.questionText, { speak: true });

    setInput("");
  } catch (e) {
    setErr(e?.message ?? "Unknown error");
  } finally {
    setLoading(false);
  }
};

  useEffect(() => {
    stopSpeak();
    stopSTT();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId, activeTab]);

  useEffect(() => {
    return () => {
      stopSTT();
      stopSpeak();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (activeTab !== "chat" || !active) return;

    let cancelled = false;

    async function loadProfileFromDB() {
      try {
        const res = await getMyOpicProfile();

        if (cancelled) return;
        if (!res?.profile) return;

        updateActiveSession((s) => ({
          ...s,
          serverProfileId: res.profileId ?? s.serverProfileId,
          updatedAt: Date.now(),
          profile: {
            ...s.profile,
            name: res.profile.name ?? "",
            job: res.profile.job ?? "",
            city: res.profile.city ?? "",
            survey: res.profile.hobbies ?? s.profile.survey,
            speakingStyle: res.profile.speaking_style ?? "natural",
          },
        }));
      } catch (e) {
        console.error("profile load failed:", e);
      }
    }

    loadProfileFromDB();

    return () => {
      cancelled = true;
    };
  }, [activeTab, activeId]);

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
            <button className={`tab-btn ${activeTab === "chat" ? "active" : ""}`} onClick={() => setActiveTab("chat")}>
              채팅
            </button>
            <button className={`tab-btn ${activeTab === "profile" ? "active" : ""}`} onClick={() => setActiveTab("profile")}>
              프로필 생성
            </button>
          </div>

          <div className="topbar-actions">

            <button
              type="button"
              className="btn"
              onClick={() => speakText(lastQuestionText, { lang: "en-US", rate: 1.0, pitch: 1.0 })}
              disabled={!lastQuestionText}
              title="마지막 질문 다시 듣기"
            >
              🔊 다시 듣기
            </button>

            <button type="button" className="btn" onClick={stopSpeak} title="읽기 중지">
              ⏹ 중지
            </button>

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
                      role={t.role === "interviewer" ? "assistant" : t.role}
                      content={t.content}
                      meta={formatTime(t.ts)}
                      showReplay={false}
                      onReplay={() => {}}
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

                  <button
                    type="button"
                    className={`btn ${isRecording ? "danger" : ""}`}
                    onClick={isRecording ? stopSTT : startSTT}
                    disabled={loading}
                    title="마이크로 말하면 입력칸에 자동으로 적혀요"
                  >
                    {isRecording ? "🛑 말하기 중지" : "🎤 말하기"}
                  </button>

                  <button className="btn primary" onClick={runTurn} disabled={loading}>
                    {loading ? "생성 중..." : "턴 진행"}
                  </button>
                </div>

                {err ? <div className="error">Error: {err}</div> : null}
              </section>

              <aside className="sidepanels">{active ? <ResultPanel session={active} /> : null}</aside>
            </>
          ) : (
            <section className="profile-panel">
              {active ? <SettingsPanel
                          session={active}
                          onChange={(updater) => updateActiveSession(updater)}
                          onSave={handleSaveProfile}
                          saving={profileSaving}
                        /> : null}
            </section>
          )}
        </div>
      </main>
    </div>
  );
}