// src/pages/CompetePage.jsx
import "./compete.css";
import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function CompetePage() {
  const [username, setUsername] = useState("");
  const [userId, setUserId] = useState(null);
  const [lbItems, setLbItems] = useState([]);      // [{rank, user_id, username, elo}]
  const [lbLoading, setLbLoading] = useState(true);
  const [lbError, setLbError] = useState(null);

  const navigate = useNavigate();

  // Auth check + load basic user info from localStorage
  useEffect(() => {
    const token = localStorage.getItem("token");
    const user = localStorage.getItem("username");
    const uid = Number(localStorage.getItem("user_id"));
    if (!token || !user) {
      navigate("/login");
    } else {
      setUsername(user);
      if (!Number.isNaN(uid)) setUserId(uid);
    }
  }, [navigate]);

  // Fetch leaderboard
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLbLoading(true);
      setLbError(null);
      try {
        const res = await fetch(`${API_BASE}/api/leaderboard/?limit=50`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!cancelled) {
          setLbItems(data.items || []);
        }
      } catch (e) {
        if (!cancelled) setLbError("Failed to load leaderboard.");
      } finally {
        if (!cancelled) setLbLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="compete-wrapper">
      <header className="compete-hero">
        <h1 className="compete-title">Hi, {username}, ready to play?</h1>
        <p className="compete-subtitle">
          Choose your battle mode and challenge opponents in real-time.
        </p>
      </header>

      <div className="compete-options">
        <Link to="/compete/mcq" className="compete-card">
          <h2>📝 MCQ Battles</h2>
          <p>
            Answer multiple-choice coding questions against your opponent.
            Fast, intense, and perfect for quick practice.
          </p>
        </Link>

        <Link to="/compete/coding" className="compete-card">
          <h2>💻 Coding Problems</h2>
          <p>
            Solve actual coding problems in timed duels.
            Showcase your problem-solving skills and climb the leaderboard.
          </p>
        </Link>
      </div>

      {/* Leaderboard */}
      <section className="compete-leaderboard">
        <h2 className="compete-leaderboard-title">🏆 Leaderboard</h2>

        {lbLoading && <p className="compete-subtitle">Loading leaderboard…</p>}
        {lbError && <p className="compete-error">{lbError}</p>}

        {!lbLoading && !lbError && (
          <div className="leaderboard-table-wrapper">
            <table className="leaderboard-table">
              <thead>
                <tr>
                  <th style={{textAlign: "left"}}>#</th>
                  <th style={{textAlign: "left"}}>Player</th>
                  <th style={{textAlign: "right"}}>ELO</th>
                </tr>
              </thead>
              <tbody>
                {lbItems.length === 0 && (
                  <tr>
                    <td colSpan={3} style={{padding: "12px 0"}}>No players yet.</td>
                  </tr>
                )}
                {lbItems.map((r) => {
                  const isMe = userId && r.user_id === userId;
                  return (
                    <tr key={`${r.user_id}-${r.rank}`} className={isMe ? "lb-row lb-row--me" : "lb-row"}>
                      <td>{r.rank}</td>
                      <td>{r.username}</td>
                      <td style={{textAlign: "right"}}>{r.elo}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
