import "./compete.css";
import { Link } from "react-router-dom";

export default function CompetePage() {
  return (
    <div className="compete-wrapper">
      <header className="compete-hero">
        <h1 className="compete-title">Choose Your Battle Mode</h1>
        <p className="compete-subtitle">
          Pick a category and challenge opponents in real-time battles.
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
