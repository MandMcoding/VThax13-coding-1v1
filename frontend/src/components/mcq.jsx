// src/pages/MCQPage.jsx
import './mcq.css';
import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export default function MCQPage() {
  const navigate = useNavigate();

  // queue/match state
  const [status, setStatus] = useState('idle'); // idle | queued | matched | active | error
  const [msg, setMsg] = useState('Waiting for a Match...');
  const [matchId, setMatchId] = useState(null);
  const [opponentId, setOpponentId] = useState(null);
  const [opponentUsername, setOpponentUsername] = useState(null);
  const [kind, setKind] = useState('mcq');

  // ready + countdown
  const [youReady, setYouReady] = useState(false);
  const [opponentReady, setOpponentReady] = useState(false);
  const [countdown, setCountdown] = useState(null); // seconds, null if not started

  // question (when active)
  const [question, setQuestion] = useState(null);
  const [selected, setSelected] = useState(null);
  const [locked, setLocked] = useState(false);
  const [result, setResult] = useState(null); // {correct, elo_delta, new_elo}
  const [timeLeft, setTimeLeft] = useState(15);

  const userId = Number(localStorage.getItem('user_id'));
  const pollRef = useRef(null);
  const fetchedQuestionRef = useRef(false);

  // join the queue on mount
  useEffect(() => {
    if (!userId) {
      setStatus('error');
      setMsg('No user id (login first).');
      return;
    }

    let cancelled = false;
    setStatus('queued');
    setMsg('Joining queue...');

    const joinQueue = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/queue/join/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: userId, kind: 'mcq' }),
        });
        const data = await res.json();
        if (cancelled) return;

        if (data.status === 'matched') {
          setKind(data.kind || 'mcq');
          setStatus('matched');
          setMatchId(data.match_id);
          setOpponentId(data.opponent_id);
          setOpponentUsername(data.opponent_username);
          setMsg(`Matched with @${data.opponent_username}. Hit Ready!`);
        } else {
          setMsg('In queue… searching for opponent.');
          startQueuePolling();
        }
      } catch {
        setStatus('error');
        setMsg('Server error while joining queue.');
      }
    };

    const startQueuePolling = () => {
      const id = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/api/queue/check/?user_id=${userId}`);
          const data = await res.json();
          if (data.status === 'matched') {
            clearInterval(id);
            setKind(data.kind || 'mcq');
            setStatus('matched');
            setMatchId(data.match_id);
            setOpponentId(data.opponent_id);
            setOpponentUsername(data.opponent_username);
            setMsg(`Matched with @${data.opponent_username}. Hit Ready!`);
          }
        } catch {}
      }, 1200);
    };

    joinQueue();

    return () => {
      cancelled = true;
      // best-effort: leave queue if still queued
      if (status === 'queued') {
        fetch(`${API_BASE}/api/queue/leave/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: userId }),
        }).catch(() => {});
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  // when matched, poll match state (ready flags + countdown + active switch)
  useEffect(() => {
    if (!matchId) return;

    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/match/${matchId}/state/?user_id=${userId}`);
        const s = await res.json();

        setYouReady(!!s.you_ready);
        setOpponentReady(!!s.opponent_ready);
        if (typeof s.countdown_seconds === 'number') {
          setCountdown(s.countdown_seconds);
        } else {
          setCountdown(null);
        }

        if (s.status === 'active' || s.countdown_seconds === 0) {
          setStatus('active');
          // fetch question only once
          if (!fetchedQuestionRef.current) {
            fetchedQuestionRef.current = true;
            fetch(`${API_BASE}/api/match/${matchId}/question/`)
              .then(r => r.json())
              .then(q => setQuestion(q))
              .catch(() => {});
          }
        } else {
          setStatus('matched');
        }
      } catch {
        // ignore transient errors
      }
    };

    // start/refresh polling
    if (pollRef.current) clearInterval(pollRef.current);
    poll(); // immediate
    pollRef.current = setInterval(poll, 800);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [matchId, userId]);

  // countdown timer per question when active
  useEffect(() => {
    if (status !== 'active' || !question) return;
    setTimeLeft(15);
    const id = setInterval(() => {
      setTimeLeft((t) => {
        if (t <= 1) {
          clearInterval(id);
          setLocked(true);
          return 0;
        }
        return t - 1;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [status, question]);

  const toggleReady = async () => {
    if (!matchId || !userId) return;
    const newReady = !youReady;
    setYouReady(newReady); // optimistic
    try {
      await fetch(`${API_BASE}/api/match/${matchId}/ready/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, ready: newReady }),
      });
      // server polling will reconcile authoritative state
    } catch {
      // revert optimistic change on error
      setYouReady(!newReady);
    }
  };

  // simple MCQ renderer once active
  const renderQuestion = () => {
    if (!question) {
      return <p className="mcq-paragraph">Loading question…</p>;
    }
    if (question.kind !== 'mcq') {
      return (
        <div className="mcq-question">
          <h2>{question.title}</h2>
          <p>{question.descriptor}</p>
          <p>(Non-MCQ question loaded. Implement coding UI.)</p>
        </div>
      );
    }
    const submit = async (i) => {
      if (locked) return;
      setSelected(i);
      setLocked(true);
      try {
        const res = await fetch(`${API_BASE}/api/match/${matchId}/submit/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: userId, question_id: question.id, answer_index: i }),
        });
        const data = await res.json();
        setResult(data);
      } catch {
        setResult({ correct: false, elo_delta: 0, new_elo: null });
      }
    };

    return (
      <div className="mcq-question">
        <h2 className="mcq-subtitle">{question.title}</h2>
        {question.descriptor && <p className="mcq-paragraph">{question.descriptor}</p>}
        <div className="mcq-timer">Time: {timeLeft}s</div>
        <ul className="mcq-list">
          {(question.choices || []).map((c, i) => (
            <li
              key={i}
              className={
                'mcq-choice' +
                (selected === i ? ' mcq-choice--selected' : '') +
                (locked ? ' mcq-choice--locked' : '')
              }
              onClick={() => submit(i)}
            >
              {c}
            </li>
          ))}
        </ul>
        {locked && result && (
          <p className="mcq-paragraph">
            {result.correct ? 'Correct! ' : 'Incorrect. '}
            {typeof result.elo_delta === 'number' && result.elo_delta > 0 && (
              <>ELO +{result.elo_delta}{result.new_elo ? ` (now ${result.new_elo})` : ''}</>
            )}
          </p>
        )}
      </div>
    );
  };

  return (
    <div className="mcq-wrapper">
      <header className="mcq">
        <span className="mcq-badge">MCQ Battle</span>
        <h1 className="mcq-subtitle">Step into the Ring</h1>

        {status !== 'active' && (
          <>
            <p className="mcq-paragraph">{msg}</p>

            {status === 'matched' && (
              <div className="mcq-lobby">
                <div className="mcq-row">
                  <strong>You:</strong> {youReady ? '✅ Ready' : '⏳ Not ready'}
                </div>
                <div className="mcq-row">
                  <strong>Opponent:</strong> {opponentUsername ? `@${opponentUsername}` : 'Opponent'} —{' '}
                  {opponentReady ? '✅ Ready' : '⏳ Not ready'}
                </div>

                {countdown !== null ? (
                  <div className="mcq-countdown">{countdown > 0 ? countdown : 'Go!'}</div>
                ) : (
                  <button className="mcq-ready-btn" onClick={toggleReady}>
                    {youReady ? 'Unready' : 'Ready'}
                  </button>
                )}
              </div>
            )}
          </>
        )}

        {status === 'active' && (
          <div className="mcq-active">
            <p className="mcq-paragraph">Match is active — good luck!</p>
            {renderQuestion()}
          </div>
        )}

        <div className="mcq-actions">
          <Link to="/compete" className="mcq-return">Return</Link>
        </div>
      </header>
    </div>
  );
}
