import { Routes, Route } from "react-router-dom";
import HomePage from "./components/home.jsx";   // make sure file name matches
import CompetePage from "./compete/page.jsx";
import logo from "./assets/logo.png";           // put logo.png in src/assets/

function App() {
  return (
    <div className="app-container">
      {/* Page Routes */}
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/compete" element={<CompetePage />} />
      </Routes>
    </div>
  );
}

export default App;
