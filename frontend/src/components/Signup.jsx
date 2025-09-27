import "./auth.css";

export default function SignupPage() {
  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <h1 className="auth-title">Create Your Account</h1>
        <form className="auth-form">
          <input type="text" placeholder="Username" className="auth-input" />
          <input type="email" placeholder="Email" className="auth-input" />
          <input type="password" placeholder="Password" className="auth-input" />
          <button type="submit" className="btn-primary full-btn">Sign Up</button>
        </form>
        <p className="auth-switch">
          Already have an account? <a href="/login">Log in</a>
        </p>
      </div>
    </div>
  );
}
