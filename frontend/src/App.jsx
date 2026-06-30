import React, { useState, useEffect, useRef } from "react";
import "./App.css";

const LOADING_MESSAGES = [
  "Bug Finder Agent scanning...",
  "Security Agent checking...",
  "Optimization Agent reviewing...",
  "Learner Profiler analyzing...",
  "Synthesizing customized feedback..."
];

const DEFAULT_CODE_PYTHON = `def hello():
    print("hello")
    hello()`;

const DEFAULT_CODE_JS = `function hello() {
    console.log("hello");
    hello();
}`;

function App() {
  const [userId, setUserId] = useState("ali");
  const [language, setLanguage] = useState("python");
  const [code, setCode] = useState(DEFAULT_CODE_PYTHON);
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState(LOADING_MESSAGES[0]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [isMockMode, setIsMockMode] = useState(false);

  const loadingIntervalRef = useRef(null);

  // Fetch App Mode (Live Gemini vs Mock Mode) on load
  useEffect(() => {
    const fetchMode = async () => {
      const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
      try {
        const response = await fetch(`${apiUrl}/mode`);
        if (response.ok) {
          const data = await response.json();
          setIsMockMode(data.use_mock);
        }
      } catch (err) {
        console.error("Failed to fetch mode endpoint", err);
      }
    };
    fetchMode();
  }, []);

  // Update default code when language changes
  const handleLanguageChange = (e) => {
    const selectedLang = e.target.value;
    setLanguage(selectedLang);
    if (selectedLang === "python") {
      setCode(DEFAULT_CODE_PYTHON);
    } else {
      setCode(DEFAULT_CODE_JS);
    }
  };

  // Cycling loading message effect
  useEffect(() => {
    if (loading) {
      let index = 0;
      setLoadingMessage(LOADING_MESSAGES[0]);
      loadingIntervalRef.current = setInterval(() => {
        index = (index + 1) % LOADING_MESSAGES.length;
        setLoadingMessage(LOADING_MESSAGES[index]);
      }, 1000);
    } else {
      if (loadingIntervalRef.current) {
        clearInterval(loadingIntervalRef.current);
      }
    }
    return () => {
      if (loadingIntervalRef.current) {
        clearInterval(loadingIntervalRef.current);
      }
    };
  }, [loading]);

  const handleAnalyze = async (e) => {
    e.preventDefault();
    if (!userId.trim()) {
      setError("User ID is required for demo profiling.");
      return;
    }
    if (!code.trim()) {
      setError("Please paste or write some code to analyze.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

    try {
      const response = await fetch(`${apiUrl}/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          user_id: userId,
          session_id: sessionId,
          code: code,
          language: language
        })
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(errText || "Failed to communicate with analysis server.");
      }

      const data = await response.json();
      setResult(data);
      if (data.session_id) {
        setSessionId(data.session_id);
      }
    } catch (err) {
      console.error(err);
      setError(err.message || "An unexpected error occurred during code analysis.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Mode Status Banner */}
      <div className={`mode-banner ${isMockMode ? "mock" : "live"}`}>
        {isMockMode ? (
          <span>🟡 Running in Mock Mode (Simulating responses, no Gemini cost)</span>
        ) : (
          <span>🟢 Running in Live Gemini Mode</span>
        )}
      </div>

      <header className="app-header">
        <div className="header-badge">CS MENTOR CO-PILOT</div>
        <h1>AI Code Mentor Agent</h1>
        <p className="app-tagline">
          An agentic multi-agent review system analyzing logic, security, and performance.
        </p>
      </header>

      <main className="app-content">
        <section className="input-section card">
          <h2>🔧 Review Panel</h2>
          <form onSubmit={handleAnalyze}>
            <div className="form-group">
              <label htmlFor="user-id">User ID (identifies your profile & memory)</label>
              <input
                id="user-id"
                type="text"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="e.g. ali, test_user_1"
                required
              />
              <span className="input-helper">Deterministic UUID mapping ensures session memory works.</span>
            </div>

            <div className="form-group">
              <label htmlFor="language">Programming Language</label>
              <select
                id="language"
                value={language}
                onChange={handleLanguageChange}
              >
                <option value="python">Python</option>
                <option value="javascript">JavaScript</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="code-input">Paste Code Snippet</label>
              <textarea
                id="code-input"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                rows={8}
                placeholder="Paste code here..."
                required
              />
            </div>

            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? "Analyzing Pipeline..." : "Analyze Code"}
            </button>
          </form>
        </section>

        {loading && (
          <section className="loading-state card">
            <div className="spinner"></div>
            <p className="loading-text">{loadingMessage}</p>
            <div className="progress-bar-container">
              <div className="progress-bar-shimmer"></div>
            </div>
          </section>
        )}

        {error && (
          <section className="error-state card">
            <h3>⚠️ Request Error</h3>
            <p>{error}</p>
          </section>
        )}

        {result && (
          <section className="results-section">
            <div className="results-grid">
              
              {/* Mentor's Final Explanation (Prominent Main Card) */}
              <div className="result-card mentor-card card full-width">
                <div className="card-header">
                  <span className="card-icon">🧑‍🏫</span>
                  <h3>Mentor's Tailored Feedback</h3>
                </div>
                <div className="card-body">
                  {result.synthesizer_error ? (
                    <div className="section-inline-error">
                      <span>⚠️ {result.synthesizer_error.message}</span>
                    </div>
                  ) : (
                    <>
                      <p className="explanation-text">{result.final_explanation}</p>
                      {result.skill_level_used && (
                        <div className="tailor-badge">
                          Adapted for: <strong>{result.skill_level_used.toUpperCase()}</strong>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>

              {/* Recurring Mistakes Card (Highly visual, only shows if non-empty) */}
              {result.flagged_recurring && result.flagged_recurring.length > 0 && (
                <div className="result-card recurring-card card full-width warning-highlight">
                  <div className="card-header">
                    <span className="card-icon">🔁</span>
                    <h3>Recurring Mistake Alert</h3>
                  </div>
                  <div className="card-body">
                    <p className="warning-text">
                      We noticed a pattern! You've run into these specific issues multiple times:
                    </p>
                    <ul className="mistake-list">
                      {result.flagged_recurring.map((mistake, idx) => (
                        <li key={idx} className="mistake-item">
                          <code>{mistake.replace(/_/g, " ")}</code>
                        </li>
                      ))}
                    </ul>
                    <p className="warning-tip">
                      Focus on base case checks and call termination conditions to resolve this pattern.
                    </p>
                  </div>
                </div>
              )}

              {/* Skill Profile Card */}
              <div className="result-card skill-card card">
                <div className="card-header">
                  <span className="card-icon">🎯</span>
                  <h3>Skill Level Detected</h3>
                </div>
                <div className="card-body">
                  {result.profiler_error ? (
                    <div className="section-inline-error">
                      <span>⚠️ {result.profiler_error.message}</span>
                    </div>
                  ) : (
                    <>
                      <div className={`skill-badge ${result.skill_level}`}>
                        {result.skill_level ? result.skill_level.toUpperCase() : "UNKNOWN"}
                      </div>
                      <p className="reasoning-text">{result.skill_reasoning}</p>
                    </>
                  )}
                </div>
              </div>

              {/* Bugs Found Card */}
              <div className="result-card bugs-card card">
                <div className="card-header">
                  <span className="card-icon">🐛</span>
                  <h3>Bugs Found</h3>
                </div>
                <div className="card-body">
                  {result.bugs_error ? (
                    <div className="section-inline-error">
                      <span>⚠️ {result.bugs_error.message}</span>
                    </div>
                  ) : (!result.bugs || result.bugs.length === 0) ? (
                    <p className="no-issues">No logic bugs identified.</p>
                  ) : (
                    <ul className="issues-list">
                      {result.bugs.map((bug, idx) => (
                        <li key={idx} className="issue-item">
                          <div className="issue-meta">
                            <span className={`severity-badge ${bug.severity}`}>
                              {bug.severity ? bug.severity.toUpperCase() : "BUG"}
                            </span>
                            {bug.line && <span className="line-number">Line {bug.line}</span>}
                          </div>
                          <p className="issue-desc">{bug.issue}</p>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>

              {/* Security Issues Card */}
              <div className="result-card security-card card">
                <div className="card-header">
                  <span className="card-icon">🔒</span>
                  <h3>Security Audit</h3>
                </div>
                <div className="card-body">
                  {result.security_error ? (
                    <div className="section-inline-error">
                      <span>⚠️ {result.security_error.message}</span>
                    </div>
                  ) : (!result.security_issues || result.security_issues.length === 0) ? (
                    <p className="no-issues">No security vulnerabilities found.</p>
                  ) : (
                    <ul className="issues-list">
                      {result.security_issues.map((sec, idx) => (
                        <li key={idx} className="issue-item">
                          <div className="issue-meta">
                            <span className={`severity-badge ${sec.risk_level}`}>
                              {sec.risk_level ? sec.risk_level.toUpperCase() : "RISK"}
                            </span>
                          </div>
                          <p className="issue-desc"><strong>Issue:</strong> {sec.issue}</p>
                          <p className="issue-recommendation"><strong>Fix:</strong> {sec.recommendation}</p>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>

              {/* Optimization Suggestions Card */}
              <div className="result-card optimization-card card">
                <div className="card-header">
                  <span className="card-icon">⚡</span>
                  <h3>Optimizations</h3>
                </div>
                <div className="card-body">
                  {result.optimizations_error ? (
                    <div className="section-inline-error">
                      <span>⚠️ {result.optimizations_error.message}</span>
                    </div>
                  ) : (!result.optimizations || result.optimizations.length === 0) ? (
                    <p className="no-issues">Code conforms to standard best practices.</p>
                  ) : (
                    <ul className="issues-list">
                      {result.optimizations.map((opt, idx) => (
                        <li key={idx} className="issue-item">
                          <p className="issue-desc">👉 {opt.suggestion}</p>
                          <p className="issue-recommendation"><strong>Why:</strong> {opt.reason}</p>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>

            </div>
          </section>
        )}
      </main>

      <footer className="app-footer-bar">
        <p>AI Code Mentor Agent © 2026. Built with FastAPI, Supabase, and Google Gemini.</p>
      </footer>
    </div>
  );
}

export default App;
