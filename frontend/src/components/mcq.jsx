import './mcq.css'
import { Routes, Route, Link } from "react-router-dom";

export default function MCQPage() {
    return (
        <div className="mcq-wrapper">
            <header className="mcq">
                <span className="mcq-badge">MCQ Battle</span>
                <h1 className="mcq-subtitle">
                    Step into the Ring
                </h1>
                <p1 className="mcq-paragraph">
                    Waiting for a Match...
                </p1>
                <Link to="/compete" className="mcq-return">
                    Return 
                </Link>
            </header>
        </div>
    )
}