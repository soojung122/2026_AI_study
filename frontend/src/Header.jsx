import React from "react";

export default function Header({ sidebarCollapsed, onToggleSidebar, onNewSession }) {
  return (
    <div className="topbar">
      <div className="topbar-left">
        <button className="icon-btn" onClick={onToggleSidebar} aria-label="toggle sidebar">
          {sidebarCollapsed ? "⟩" : "⟨"}
        </button>
        <div className="brand">
          <div className="brand-title">OPIc Chat</div>
          <div className="brand-sub">대화형 모의 오픽 · 질문/파생질문/평가</div>
        </div>
      </div>

      <div className="topbar-right">
        <button className="primary-btn" onClick={onNewSession}>
          + New Session
        </button>
      </div>
    </div>
  );
}
