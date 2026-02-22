import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { registerApi } from "./api";

export default function Register() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [msg, setMsg] = useState("");

  const handleRegister = async () => {
    setMsg("");
    try {
      await registerApi({ email, password, name });
      // ✅ 회원가입 성공하면 로그인으로 이동
      nav("/login", { replace: true });
    } catch (err) {
      setMsg("회원가입 실패: " + err.message);
    }
  };

  return (
    <div style={{ padding: 20 }}>
      <h2>회원가입</h2>

      <div>
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="이메일" />
      </div>
      <div>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="비밀번호(8자 이상)"
        />
      </div>
      <div>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="이름(선택)" />
      </div>

      <button onClick={handleRegister}>회원가입</button>

      <p style={{ whiteSpace: "pre-wrap" }}>{msg}</p>
      <Link to="/login"> 로그인</Link>
    </div>
  );
}
