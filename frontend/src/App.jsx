import { Routes, Route, Link } from "react-router-dom";
import HomePage from "./components/home.jsx";
import CompetePage from "./compete/page.jsx";

export default function App() {
  return (
    <div className="app-container">
      {/* Routes */}
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/compete" element={<CompetePage />} />
      </Routes>
    </div>
  );
}
