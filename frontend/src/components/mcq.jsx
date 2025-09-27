// src/pages/MCQPage.jsx
import "./mcq.css";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

export default function MCQPage() {
  const [status, setStatus] = useState("idle"); // idle | queued | matched | error
  const [opponentId, setOpponentId] = useState(null);
  const [matchId, setMatchId] = useState(null);
  const [msg, setMsg] = useState("Waiting for a Match...");
  const pollRef = useRef(null);
  const navigate = useNavigate();

  // Get userId you stored at login (adjust if you used a different key)
  const userId = Number(localStorage.getItem("user_id"));
  const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
  const API = `${API_BASE}/api`;

  useEffect(() => {
    let cancelled = false;

    async function join() {
      if (!userId) {
        setStatus("error");
        setMsg("No user id (login first).");
        return;
      }
      setStatus("queued");
      setMsg("Joining queue…");

      try {
        const res = await fetch(`${API}/queue/join/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: userId }),
        });
        const data = await res.json();

        if (cancelled) return;

        if (data.status === "matched") {
          setMatchId(data.match_id);
          setOpponentId(data.opponent_id);
          setStatus("matched");
          setMsg("Matched! Redirecting…");
          // tiny delay so UI shows "Matched!"
          setTimeout(() => goToMatch(data.match_id, data.opponent_id), 300);
        } else {
          setMsg("In queue… searching for opponent.");
          startPolling();
        }
      } catch (e) {
        setStatus("error");
        setMsg("Server error while joining queue.");
      }
    }

    join();
    return () => {
      cancelled = true;
      stopPolling();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startPolling = () => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API}/queue/check/?user_id=${userId}`);
        const data = await res.json();
        if (data.status === "matched") {
          setMatchId(data.match_id);
          setOpponentId(data.opponent_id);
          setStatus("matched");
          setMsg("Matched! Redirecting…");
          stopPolling();
          setTimeout(() => goToMatch(data.match_id, data.opponent_id), 200);
        }
      } catch {
        // keep polling; optionally show transient error
      }
    }, 1500);
  };

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const leaveQueue = async () => {
    stopPolling();
    try {
      await fetch(`${API}/queue/leave/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId }),
      });
    } catch {}
    setStatus("idle");
    setMsg("Left queue.");
  };

  const goToMatch = (mId, oppId) => {
    // pass via router state or query params — here we use state
    navigate("/compete", { state: { matchId: mId, opponentId: oppId } });
  };

  return (
    <div className="mcq-wrapper">
      <header className="mcq">
        <span className="mcq-badge">MCQ Battle</span>
        <h1 className="mcq-subtitle">Step into the Ring</h1>
        <p className="mcq-paragraph">{msg}</p>

        {status === "queued" && (
          <button className="btn-primary full-btn" onClick={leaveQueue}>
            Leave Queue
          </button>
        )}

        {status === "error" && (
          <p className="mcq-paragraph" style={{ color: "red" }}>
            {msg}
          </p>
        )}

        <Link to="/" className="mcq-return">
          Return
        </Link>
      </header>
    </div>
  );
}
