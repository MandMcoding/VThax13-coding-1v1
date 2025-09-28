// SignupPage.jsx
import { useState } from "react";
import "./auth.css";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export default function SignupPage() {
  const [fname, setFname] = useState("");
  const [lname, setLname] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("user");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setOk(false);

    if (!fname || !lname || !username || !email || !password) {
      setError("Please fill in all fields.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/users/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fname,
          lname,
          email,
          username,
          password: password, // WARNING: raw string; backend should hash
          role,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(
          data?.detail || Object.values(data).flat().join(" ") || "Signup failed"
        );
      }

      setOk(true);
      // maybe redirect: window.location.href = "/login";
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <h1 className="auth-title">Create Your Account</h1>

        <form className="auth-form" onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="First Name"
            className="auth-input"
            value={fname}
            onChange={(e) => setFname(e.target.value)}
          />
          <input
            type="text"
            placeholder="Last Name"
            className="auth-input"
            value={lname}
            onChange={(e) => setLname(e.target.value)}
          />
          <input
            type="text"
            placeholder="Username"
            className="auth-input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
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
          <button type="submit" className="btn-primary full-btn" disabled={loading}>
            {loading ? "Signing up..." : "Sign Up"}
          </button>
        </form>

        {error && <p className="auth-error">{error}</p>}
        {ok && <p className="auth-success">User created successfully 🎉</p>}

        <p className="auth-switch">
          Already have an account? <a href="/login">Log in</a>
        </p>
      </div>
    </div>
  );
}
