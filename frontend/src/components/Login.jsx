import "./auth.css";
import { useState } from "react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const res = await fetch("http://127.0.0.1:8000/api/login/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      if (res.ok) {
        const data = await res.json();
        setMessage(`✅ Login successful! Welcome, ${data.username || email}`);
        // If backend returns a token, store it:
        // localStorage.setItem("token", data.token);
      } else {
        const err = await res.json();
        setMessage(`❌ Login failed: ${err.error || "Invalid credentials"}`);
      }
    } catch (error) {
      setMessage("⚠️ Server error, try again later.");
    }
  };

  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <h1 className="auth-title">Welcome Back</h1>
        <form className="auth-form" onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="Email"
            className="auth-input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            type="password"
            placeholder="Password"
            className="auth-input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button type="submit" className="btn-primary full-btn">
            Log In
          </button>
        </form>
        {message && <p style={{ marginTop: "10px" }}>{message}</p>}
        <p className="auth-switch">
          Don’t have an account? <a href="/signup">Sign up</a>
        </p>
      </div>
    </div>
  );
}
