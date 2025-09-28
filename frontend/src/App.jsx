import { Routes, Route, Link, useNavigate, useLocation } from "react-router-dom";
import { useState, useEffect } from "react";

import HomePage from "./components/home.jsx";
import CompetePage from "./compete/compete.jsx";
import SignupPage from "./components/Signup.jsx";
import LoginPage from "./components/Login.jsx";
import MCQPage from "./components/mcq.jsx";
import ModelViewer from "./components/ModelViewer.jsx";

import logo from "./assets/logo.png";
import "./components/home.css"; // reuse navbar styles

export default function App() {
  const [username, setUsername] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const storedUser = localStorage.getItem("username");
    if (storedUser) setUsername(storedUser);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("username");
    localStorage.removeItem("token");
    setUsername(null);
    navigate("/login");
  };

  // hide navbar only on landing page
  const hideNavbar = location.pathname === "/";

  return (
    <div className="app-container">
      {!hideNavbar && (
        <nav className="navbar">
          <div className="navbar-left">
            <Link to="/">
              <img src={logo} alt="CodeComp Logo" className="logo-img" />
            </Link>
          </div>
          <div className="navbar-links">
            <Link to="/compete">Game Modes</Link>
            <Link to="/#faq">FAQ</Link>

            {username ? (
              <>
                <span style={{ marginRight: "10px" }}>👋 Hello, {username}</span>
                <button onClick={handleLogout} className="btn-signup">
                  Log Out
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="nav-link">Log In</Link>
                <Link to="/signup" className="btn-signup">Sign Up</Link>
              </>
            )}
          </div>
        </nav>
      )}

      {/* Page Routes */}
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/compete" element={<CompetePage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/compete/mcq" element={<MCQPage />} />
        <Route path="/viewer" element={<ModelViewer />} />
      </Routes>
    </div>
  );
}
