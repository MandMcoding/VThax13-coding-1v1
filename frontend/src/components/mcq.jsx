// src/pages/MCQPage.jsx
import './mcq.css';
import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export default function MCQPage() {
  // queue/match state
  const [status, setStatus] = useState('idle'); // idle | queued | matched | active | finished | error
  const [msg, setMsg] = useState('Waiting for a Match...');
  const [matchId, setMatchId] = useState(null);
  const [opponentId, setOpponentId] = useState(null);
  const [opponentUsername, setOpponentUsername] = useState(null);
  const [kind, setKind] = useState('mcq');

  // ready + countdown to start
  const [youReady, setYouReady] = useState(false);
  const [opponentReady, setOpponentReady] = useState(false);
  const [countdown, setCountdown] = useState(null); // seconds, null if not started

  // server-authoritative match clock (60s total once active)
  const [matchTimeLeft, setMatchTimeLeft] = useState(null); // seconds

  // question (when active)
  const [question, setQuestion] = useState(null);
  const [selected, setSelected] = useState(null);
  const [locked, setLocked] = useState(false);
  const [result, setResult] = useState(null); // {correct, elo_delta, new_elo}
  const [timeLeft, setTimeLeft] = useState(15); // per-question local timer

  // results (when finished)
  const [finalResults, setFinalResults] = useState(null); // payload from /results/

  const userId = Number(localStorage.getItem('user_id'));
  const statePollRef = useRef(null);     // polls /state
  const queuePollRef = useRef(null);     // polls /queue/check
  const fetchedQuestionRef = useRef(false);
  const finishedRef = useRef(false);
  const questionStartRef = useRef(null); // for elapsed_ms

  // helper: stop all timers
  const stopAllPolling = () => {
    if (statePollRef.current) {
      clearInterval(statePollRef.current);
      statePollRef.current = null;
    }
    if (queuePollRef.current) {
      clearInterval(queuePollRef.current);
      queuePollRef.current = null;
    }
  };

  // helper: finish and fetch results once
  const finishAndFetchResults = async (mid) => {
    if (finishedRef.current) return;
    finishedRef.current = true;
    stopAllPolling();
    try {
      await fetch(`${API_BASE}/api/match/${mid}/finish/`, { method: 'POST' });
    } catch {}
    try {
      const r = await fetch(`${API_BASE}/api/match/${mid}/results/`);
      const data = await r.json();
      setFinalResults(data);
    } catch {}
    setStatus('finished');
  };

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

    const startQueuePolling = () => {
      queuePollRef.current = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/api/queue/check/?user_id=${userId}`);
          const data = await res.json();
          if (data.status === 'matched') {
            if (queuePollRef.current) {
              clearInterval(queuePollRef.current);
              queuePollRef.current = null;
            }
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

    joinQueue();

    return () => {
      cancelled = true;
      stopAllPolling();
      // best-effort: leave queue if still queued
      fetch(`${API_BASE}/api/queue/leave/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
      }).catch(() => {});
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  // when matched/active, poll match state (ready flags + countdown + active/finished switch + time_left)
  useEffect(() => {
    if (!matchId) return;

    const pollOnce = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/match/${matchId}/state/?user_id=${userId}`);
        const s = await res.json();

        setYouReady(!!s.you_ready);
        setOpponentReady(!!s.opponent_ready);
        setMatchTimeLeft(typeof s.time_left_seconds === 'number' ? s.time_left_seconds : null);

        if (typeof s.countdown_seconds === 'number') {
          setCountdown(s.countdown_seconds);
        } else {
          setCountdown(null);
        }

        // handle lifecycle
        if (s.status === 'finished' || (typeof s.time_left_seconds === 'number' && s.time_left_seconds <= 0)) {
          await finishAndFetchResults(matchId); // clears polls and fetches results
          return;
        }

        if (s.status === 'active' || s.countdown_seconds === 0) {
          setStatus('active');
          // fetch question only once when first entering active
          if (!fetchedQuestionRef.current) {
            fetchedQuestionRef.current = true;
            fetch(`${API_BASE}/api/match/${matchId}/question/`)
              .then(r => r.json())
              .then(q => {
                setQuestion(q);
                questionStartRef.current = Date.now(); // mark question start
              })
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
    if (statePollRef.current) clearInterval(statePollRef.current);
    pollOnce(); // immediate
    statePollRef.current = setInterval(pollOnce, 800);

    return () => {
      if (statePollRef.current) {
        clearInterval(statePollRef.current);
        statePollRef.current = null;
      }
    };
  }, [matchId, userId]);

  // local 15s per-question timer (client UX), independent from 60s match clock
  useEffect(() => {
    if (status !== 'active' || !question) return;
    setTimeLeft(15);
    setLocked(false);
    setSelected(null);
    setResult(null);
    questionStartRef.current = Date.now();

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
      setYouReady(!newReady); // revert optimistic change on error
    }
  };

  // MCQ renderer once active
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
        const elapsedMs =
          typeof questionStartRef.current === 'number' ? (Date.now() - questionStartRef.current) : null;

        const res = await fetch(`${API_BASE}/api/match/${matchId}/submit/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: userId,
            question_id: question.id,
            answer_index: i,
            elapsed_ms: elapsedMs
          }),
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

        <div className="mcq-row">
          <div className="mcq-timer">Question: {timeLeft}s</div>
          {typeof matchTimeLeft === 'number' && (
            <div className="mcq-timer">Match: {matchTimeLeft}s</div>
          )}
        </div>

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

  const renderFinished = () => {
    return (
      <div className="mcq-finished">
        <h2 className="mcq-subtitle">Match finished</h2>
        {finalResults ? (
          <>
            <p className="mcq-paragraph">
              Final Score — {finalResults.p1.username}: {finalResults.p1.score} · {finalResults.p2.username}: {finalResults.p2.score}
            </p>
            <div className="mcq-results">
              <div className="mcq-results-col">
                <h3>@{finalResults.p1.username}</h3>
                <ul>
                  {finalResults.p1.answers.map((a, idx) => (
                    <li key={idx}>
                      Q{a.question_id} — {a.is_correct ? '✓' : '✗'} {typeof a.elapsed_ms === 'number' ? `(${a.elapsed_ms}ms)` : ''}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="mcq-results-col">
                <h3>@{finalResults.p2.username}</h3>
                <ul>
                  {finalResults.p2.answers.map((a, idx) => (
                    <li key={idx}>
                      Q{a.question_id} — {a.is_correct ? '✓' : '✗'} {typeof a.elapsed_ms === 'number' ? `(${a.elapsed_ms}ms)` : ''}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </>
        ) : (
          <p className="mcq-paragraph">Loading final results…</p>
        )}
      </div>
    );
  };

  return (
    <div className="mcq-wrapper">
      <header className="mcq">
        <span className="mcq-badge">MCQ Battle</span>
        <h1 className="mcq-subtitle">Step into the Ring</h1>

        {status !== 'active' && status !== 'finished' && (
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

        {status === 'finished' && renderFinished()}

        <div className="mcq-actions">
          <Link to="/compete" className="mcq-return">Return</Link>
        </div>
      </header>
    </div>
  );
}
