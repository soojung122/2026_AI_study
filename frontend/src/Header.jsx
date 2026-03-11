import React from "react";
import { clearToken, getToken } from "./auth";

export default function Header({ sidebarCollapsed, onToggleSidebar, onNewSession }) {
  const handleLogout = () => {
    clearToken();
    window.location.href = "/login";
  };

  const loggedIn = !!getToken();

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
        {loggedIn && (
          <button className="btn" onClick={handleLogout}>
            로그아웃
          </button>
        )}

        <button className="primary-btn" onClick={onNewSession}>
          + New Session
        </button>
      </div>
    </div>
  );
}