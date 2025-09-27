import { Routes, Route, Link } from "react-router-dom";
import HomePage from "./components/home.jsx";
import CompetePage from "./compete/compete.jsx";
import SignupPage from "./components/Signup.jsx";
import LoginPage from "./components/Login.jsx";
import MCQPage from "./components/mcq.jsx";
import logo from "./assets/logo.png";
import "./components/home.css"; // reuse navbar styles

export default function App() {
  return (
    <div className="app-container">
      {/* Global Navbar */}
      <nav className="navbar">
        <div className="navbar-left">
          <Link to="/">
            <img src={logo} alt="CodeComp Logo" className="logo-img" />
          </Link>
        </div>
        <div className="navbar-links">
          <Link to="/compete">Game Modes</Link>
          <Link to="/#faq">FAQ</Link>
          <Link to="/login" className="nav-link">Log In</Link>
          <Link to="/signup" className="btn-signup">Sign Up</Link>
        </div>
      </nav>

      {/* Page Routes */}
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/compete" element={<CompetePage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/compete/mcq" element={<MCQPage />} />
      </Routes>
    </div>
  );
}
