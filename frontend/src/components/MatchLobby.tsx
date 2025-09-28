// src/pages/MatchLobby.tsx
import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

export default function MatchLobby() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const matchId = Number(params.get("match_id"));
  const userId = Number(localStorage.getItem("user_id"));      // ensure you set this at login
  const [ready, setReady] = useState(false);
  const [state, setState] = useState<any>(null);
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    if (!matchId || !userId) return;
    const poll = async () => {
      try {
        const r = await fetch(`/api/match/state/?match_id=${matchId}&user_id=${userId}`);
        const json = await r.json();
        setState(json);

        if (json.status === "active" || (json.countdown_seconds !== null && json.countdown_seconds === 0)) {
          navigate(`/play?match_id=${matchId}&kind=${json.kind || "mcq"}&question_id=${json.question_id || ""}`);
        }
      } catch {}
    };

    // initial + interval
    poll();
    pollRef.current = window.setInterval(poll, 800);
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, [matchId, userId, navigate]);

  const toggleReady = async () => {
    if (!matchId || !userId) return;
    const newReady = !ready;
    setReady(newReady);
    await fetch("/api/match/ready/", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ match_id: matchId, user_id: userId, ready: newReady }),
    }).catch(() => {});
  };

  const youReady = state?.you_ready ?? ready; // server computes you_ready; fallback to local
  const oppReady = state?.opponent_ready ?? (state ? (state.p1_ready && state.p2_ready && !youReady) : false);
  const countdown = state?.countdown_seconds;

  return (
    <div className="lobby">
      <h1>Match Lobby</h1>
      <p>Match #{matchId}</p>
      <div className="players">
        <div>
          <strong>You:</strong> {youReady ? "✅ Ready" : "⏳ Not ready"}
        </div>
        <div>
          <strong>Opponent:</strong> {oppReady ? "✅ Ready" : "⏳ Not ready"}
        </div>
      </div>

      {countdown != null && (
        <div className="countdown" style={{ fontSize: 48, margin: "16px 0" }}>
          {countdown > 0 ? countdown : "Go!"}
        </div>
      )}

      {state?.status === "pending" && (
        <button onClick={toggleReady} className="btn">
          {youReady ? "Unready" : "Ready"}
        </button>
      )}

      {state?.status === "active" && <div>Starting…</div>}
    </div>
  );
}
