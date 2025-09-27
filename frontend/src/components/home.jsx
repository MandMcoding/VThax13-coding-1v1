import "./home.css";

export default function HomePage() {
  return (
    <div className="home-wrapper">
      {/* Hero Section */}
      <header className="hero">
        <span className="hero-badge">🥊 1v1 Coding Battles</span>
        <h1 className="hero-title">
          Compete with <span className="highlight">coders</span> &<br />
          climb the <em>leaderboard</em>
        </h1>
        <p className="hero-subtitle">
          CodeComp makes coding practice exciting. Face off in fast-paced matches,
          sharpen your problem-solving, and rise through the ranks.
        </p>
        <div className="hero-buttons">
          <a href="/compete" className="btn-primary">Start Competing</a>
          <a href="/about" className="btn-secondary">Learn More</a>
        </div>
      </header>
    </div>
  );
}
