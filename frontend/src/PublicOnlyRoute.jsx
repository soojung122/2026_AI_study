import { Navigate } from "react-router-dom";

export default function PublicOnlyRoute({ isAuthed, children }) {
  // ✅ 로그인 상태면 로그인/회원가입 페이지 대신 메인 화면으로
  if (isAuthed) return <Navigate to="/MainScreen" replace />;
  return children;
}
