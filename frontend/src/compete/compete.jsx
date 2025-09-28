import "./compete.css";
import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";

export default function CompetePage() {
  const [username, setUsername] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem("token");
    const user = localStorage.getItem("username");

    if (!token || !user) {
      navigate("/login"); // Redirect if not logged in
    } else {
      setUsername(user);
    }
  }, []);

  return (
    <div className="compete-wrapper">
      <header className="compete-hero">
        {/* 👋 Personalized greeting */}
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
    </div>
  );
}
