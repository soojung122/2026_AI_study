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
      const data = await loginApi({ email, password });
      setToken(data.access_token);

      if (onLoginSuccess) await onLoginSuccess();

      nav("/MainScreen", { replace: true });
    } catch (err) {
      setMsg("로그인 실패: " + err.message);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h2 style={styles.title}>Login</h2>

        <input
          style={styles.input}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
        />

        <input
          style={styles.input}
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
        />

        <button style={styles.button} onClick={handleLogin}>
          로그인
        </button>

        {msg && <p style={styles.error}>{msg}</p>}

        <Link style={styles.link} to="/register">
          회원가입
        </Link>
      </div>
    </div>
  );
}

const styles = {
  container: {
    height: "100vh",
    backgroundColor: "#000",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
  },

  card: {
    backgroundColor: "#111",
    padding: "40px",
    borderRadius: "12px",
    width: "320px",
    display: "flex",
    flexDirection: "column",
    gap: "15px",
    boxShadow: "0 0 15px rgba(255,255,255,0.05)",
  },

  title: {
    color: "#fff",
    textAlign: "center",
    marginBottom: "10px",
  },

  input: {
    padding: "12px",
    borderRadius: "8px",
    border: "1px solid #333",
    backgroundColor: "#1a1a1a",
    color: "#fff",
    outline: "none",
  },

  button: {
    padding: "12px",
    borderRadius: "8px",
    border: "none",
    backgroundColor: "#fff",
    color: "#000",
    fontWeight: "bold",
    cursor: "pointer",
  },

  link: {
    color: "#aaa",
    textAlign: "center",
    fontSize: "14px",
    textDecoration: "none",
  },

  error: {
    color: "#ff6b6b",
    fontSize: "14px",
    textAlign: "center",
  },
};