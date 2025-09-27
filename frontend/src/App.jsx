<<<<<<< HEAD
import { Routes, Route } from "react-router-dom";
import HomePage from "./components/home.jsx";   // make sure file name matches
import CompetePage from "./compete/page.jsx";
import logo from "./assets/logo.png";           // put logo.png in src/assets/
=======
import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import { Routes, Route, Link } from 'react-router-dom'
import CompetePage from './compete/page.jsx'
>>>>>>> c20f42f4766516aa074b1a0904f8cfa4269154da

function App() {
  return (
<<<<<<< HEAD
    <div className="app-container">
      {/* Page Routes */}
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/compete" element={<CompetePage />} />
      </Routes>
    </div>
  );
=======
    <>
      <div>
        <nav>
          <Link to="/compete">Compete</Link>
        </nav>

        <Routes>
          <Route path="/compete" element={<CompetePage />} />
        </Routes>
      </div>
      <div>
        <a href="https://vite.dev" target="_blank">
          <img src={viteLogo} className="logo" alt="Vite logo" />
        </a>
        <a href="https://react.dev" target="_blank">
          <img src={reactLogo} className="logo react" alt="React logo" />
        </a>
      </div>
      <h1>Vite + React</h1>
      <div className="card">
        <button onClick={() => setCount((count) => count + 1)}>
          count is {count}
        </button>
        <p>
          Edit <code>src/App.jsx</code> and save to test HMR
        </p>
      </div>
      <p className="read-the-docs">
        Click on the Vite and React logos to learn more
      </p>
    </>
  )
>>>>>>> c20f42f4766516aa074b1a0904f8cfa4269154da
}

export default App;
