import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { loginApi } from "./api";
import { setToken } from "./auth";

export default function Login({ onLoginSuccess }) {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [msg, setMsg] = useState("");

  const handleLogin = async () => {
    setMsg("");
    try {
      const data = await loginApi({ email, password }); // {access_token}
      setToken(data.access_token);

      // ✅ 로그인 상태 갱신(앱에서 사용자 정보 다시 불러오게)
      if (onLoginSuccess) await onLoginSuccess();

      nav("/MainScreen", { replace: true });
    } catch (err) {
      setMsg("로그인 실패: " + err.message);
    }
  };

  return (
    <div style={{ padding: 20 }}>
      <h2>로그인</h2>

      <div>
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="이메일" />
      </div>
      <div>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="비밀번호"
        />
      </div>

      <button onClick={handleLogin}>로그인</button>

      <p style={{ whiteSpace: "pre-wrap" }}>{msg}</p>
      <Link to="/register"> 회원가입</Link>
    </div>
  );
}
