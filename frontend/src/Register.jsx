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
      nav("/login", { replace: true });
    } catch (err) {
      setMsg("회원가입 실패: " + err.message);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h2 style={styles.title}>Register</h2>

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
          placeholder="Password (8자 이상)"
        />

        <input
          style={styles.input}
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Name (optional)"
        />

        <button style={styles.button} onClick={handleRegister}>
          회원가입
        </button>

        {msg && <p style={styles.error}>{msg}</p>}

        <Link style={styles.link} to="/login">
          로그인으로 이동
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