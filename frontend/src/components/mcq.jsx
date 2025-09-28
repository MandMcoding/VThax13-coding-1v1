import './mcq.css';
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export default function MCQPage() {
    const [status, setStatus] = useState('idle'); // idle | queued | matched
    const [opponentUsername, setOpponentUsername] = useState(null);
    const [msg, setMsg] = useState('Waiting for a Match...');
    const [matchId, setMatchId] = useState(null);
    const [opponentId, setOpponentId] = useState(null);

    // Get userId from localStorage (set at login)
    const userId = Number(localStorage.getItem('user_id'));

    useEffect(() => {
        if (!userId) {
            setMsg('No user id (login first).');
            setStatus('error');
            return;
        }
        setStatus('queued');
        setMsg('Joining queue...');
        let cancelled = false;

        async function joinQueue() {
            try {
                const res = await fetch(`${API_BASE}/api/queue/join/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: userId }),
                });
                const data = await res.json();
                if (cancelled) return;
                if (data.status === 'matched') {
                    setStatus('matched');
                    setMatchId(data.match_id);
                    setOpponentId(data.opponent_id);
                    setOpponentUsername(data.opponent_username);
                    setMsg(`Matched with @${data.opponent_username}`);
                } else {
                    setMsg('In queue… searching for opponent.');
                    pollForMatch();
                }
            } catch (e) {
                setStatus('error');
                setMsg('Server error while joining queue.');
            }
        }

        async function pollForMatch() {
            const poll = setInterval(async () => {
                try {
                    const res = await fetch(`${API_BASE}/api/queue/check/?user_id=${userId}`);
                    const data = await res.json();
                    if (data.status === 'matched') {
                        clearInterval(poll);
                        setStatus('matched');
                        setMatchId(data.match_id);
                        setOpponentId(data.opponent_id);
                        setOpponentUsername(data.opponent_username);
                        setMsg(`Matched with @${data.opponent_username}`);
                    }
                } catch {}
            }, 1500);
        }

        joinQueue();
        return () => {
            cancelled = true;
        };
    }, [userId]);

    return (
        <div className="mcq-wrapper">
            <header className="mcq">
                <span className="mcq-badge">MCQ Battle</span>
                <h1 className="mcq-subtitle">Step into the Ring</h1>
                <p className="mcq-paragraph">
                    {msg}
                </p>
                <Link to="/compete" className="mcq-return">
                    Return
                </Link>
            </header>
        </div>
    );
}
