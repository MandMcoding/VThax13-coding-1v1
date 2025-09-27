import "./home.css";
import logo from "../assets/logo.png"; // your logo here

export default function HomePage() {
  return (
    <div className="home-wrapper">
      {/* Navbar */}
      <nav className="navbar">
        <div className="navbar-left">
          <img src={logo} alt="CodeComp Logo" className="logo-img" />
        </div>
        <div className="navbar-links">
          <a href="#features">Features</a>
          <a href="#pricing">Pricing</a>
          <a href="#faq">FAQ</a>
          <a href="/login" className="nav-link">Log In</a>
          <a href="/signup" className="btn-signup">Sign Up</a>
        </div>
      </nav>

      {/* Hero Section */}
      <header className="hero">
        <span className="hero-badge">🚀 1v1 Coding Battles</span>
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
