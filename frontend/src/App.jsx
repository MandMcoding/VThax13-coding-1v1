import { Routes, Route, Link } from "react-router-dom";
import HomePage from "./components/home.jsx";
import CompetePage from "./compete/page.jsx";
import SignupPage from "./components/Signup.jsx";
import LoginPage from "./components/Login.jsx";
import logo from "./assets/logo.png";
import "./components/home.css";  // reuse navbar styles

export default function App() {
  return (
    <div className="app-container">
      {/* Global Navbar */}
      <nav className="navbar">
        <div className="navbar-left">
          <img src={logo} alt="CodeComp Logo" className="logo-img" />
        </div>
        <div className="navbar-links">
          <Link to="/#features">Features</Link>
          <Link to="/#pricing">Pricing</Link>
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
      </Routes>
    </div>
  );
}
