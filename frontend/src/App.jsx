
import { useState, useEffect } from 'react'
import './App.css'

const API_URL =  import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

function App() {
  // Navigation
  const [activePage, setActivePage] = useState('overview')

  // Dashboard data
  const [dashboardStats, setDashboardStats] = useState(null)
  const [recentScans, setRecentScans] = useState([])
  const [dashboardLoading, setDashboardLoading] = useState(true)
  const [dashboardError, setDashboardError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  // PR Scanner data
  const [prUrl, setPrUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  // Fetch real dashboard data from SQLite-backed APIs
  useEffect(() => {
    if (activePage !== 'overview') return

    let isActive = true

    const fetchDashboard = async () => {
      try {
        const [statsResponse, scansResponse] = await Promise.all([
          fetch(`${API_URL}/api/dashboard/stats`),
          fetch(`${API_URL}/api/dashboard/scans?limit=10`),
        ])

        if (!statsResponse.ok || !scansResponse.ok) {
          throw new Error('Unable to load dashboard data.')
        }

        const stats = await statsResponse.json()
        const scans = await scansResponse.json()

        if (isActive) {
          setDashboardStats(stats)
          setRecentScans(scans.scans || [])
          setDashboardError('')
        }
      } catch (err) {
        if (isActive) {
          setDashboardError(err.message)
        }
      } finally {
        if (isActive) {
          setDashboardLoading(false)
        }
      }
    }

    setDashboardLoading(true)
    fetchDashboard()

    // Refresh dashboard every 10 seconds
    const interval = setInterval(fetchDashboard, 10000)

    return () => {
      isActive = false
      clearInterval(interval)
    }
  }, [activePage, refreshKey])

  // Manual Pull Request scan
  const handleScan = async (e) => {
    e.preventDefault()

    setLoading(true)
    setResult(null)
    setError('')

    try {
      const response = await fetch(`${API_URL}/api/scan/pr`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ pr_url: prUrl }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to scan Pull Request.')
      }

      setResult(data)
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const riskColor = (level) => {
    if (level === 'HIGH') return 'high'
    if (level === 'MEDIUM') return 'medium'
    return 'low'
  }

  const formatDate = (date) => {
    if (!date) return 'Date unavailable'

    return new Date(date).toLocaleString()
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">G</div>
          <span>GitGuard <strong>AI</strong></span>
        </div>

        <div className="system-status">
          <span className="status-dot"></span>
          Security Scanner
        </div>
      </header>

      <main className="dashboard">

        {/* Navigation */}
        <nav className="dashboard-nav">
          <button
            className={activePage === 'overview' ? 'nav-button active' : 'nav-button'}
            onClick={() => setActivePage('overview')}
          >
            Overview
          </button>

          <button
            className={activePage === 'scanner' ? 'nav-button active' : 'nav-button'}
            onClick={() => setActivePage('scanner')}
          >
            PR Scanner
          </button>
        </nav>

        {/* OVERVIEW PAGE */}
        {activePage === 'overview' && (
          <section className="overview-page">

            <div className="overview-heading">
              <div>
                <div className="eyebrow">GITHUB SECURITY MONITOR</div>
                <h1>Security Overview</h1>
                <p>Monitor your GitHub repositories and security scans.</p>
              </div>

              <button
                className="refresh-button"
                onClick={() => setRefreshKey((key) => key + 1)}
              >
                ↻ Refresh
              </button>
            </div>

            {dashboardLoading && !dashboardStats && (
              <div className="dashboard-message">
                Loading dashboard data...
              </div>
            )}

            {dashboardError && (
              <div className="error-message">
                {dashboardError}
              </div>
            )}

            {dashboardStats && (
              <>
                {/* Statistics */}
                <div className="stats-grid">

                  <div className="stat-card">
                    <span className="stat-label">Total Scans</span>
                    <h2>{dashboardStats.total_scans}</h2>
                    <p>All recorded security scans</p>
                  </div>

                  <div className="stat-card">
                    <span className="stat-label">Secrets Detected</span>
                    <h2 className="danger-text">
                      {dashboardStats.secrets_detected}
                    </h2>
                    <p>Scans with potential secrets</p>
                  </div>

                  <div className="stat-card">
                    <span className="stat-label">Risky Pull Requests</span>
                    <h2 className="warning-text">
                      {dashboardStats.risky_prs}
                    </h2>
                    <p>Medium or high-risk PR scans</p>
                  </div>

                  <div className="stat-card">
                    <span className="stat-label">Safe Scans</span>
                    <h2 className="safe-text">
                      {dashboardStats.safe_scans}
                    </h2>
                    <p>Scans without detected secrets</p>
                  </div>

                </div>

                {/* Event summary */}
                <div className="event-summary">
                  <div className="event-card">
                    <span>Push Events</span>
                    <strong>{dashboardStats.push_scans}</strong>
                  </div>

                  <div className="event-card">
                    <span>Pull Request Events</span>
                    <strong>{dashboardStats.pr_scans}</strong>
                  </div>
                </div>

                {/* Recent activity */}
                <section className="activity-section">
                  <div className="activity-heading">
                    <div>
                      <h2>Recent Scan Activity</h2>
                      <p>Latest GitHub push and Pull Request scans</p>
                    </div>
                  </div>

                  {recentScans.length === 0 ? (
                    <p className="muted">
                      No scan history available yet.
                    </p>
                  ) : (
                    <div className="activity-list">
                      {recentScans.map((scan) => (
                        <div className="activity-item" key={scan.id}>

                          <div className="activity-main">
                            <strong>
                              {scan.repository || 'Unknown repository'}
                            </strong>

                            <span>
                              {scan.event_type === 'pull_request'
                                ? `Pull Request · ${scan.action || 'scan'}`
                                : 'Push event'}
                            </span>

                            <small>
                              {scan.branch || 'Branch unavailable'}
                              {' · '}
                              {formatDate(scan.created_at)}
                            </small>
                          </div>

                          <div className="activity-status">
                            <span className={
                              scan.has_secret ? 'danger-text' : 'safe-text'
                            }>
                              {scan.has_secret ? 'Secret detected' : 'No secret'}
                            </span>

                            {scan.risk_level && (
                              <span className={riskColor(scan.risk_level)}>
                                {scan.risk_level} risk
                              </span>
                            )}
                          </div>

                        </div>
                      ))}
                    </div>
                  )}
                </section>
              </>
            )}
          </section>
        )}

        {/* PR SCANNER PAGE */}
        {activePage === 'scanner' && (
          <>
            <section className="hero-section">
              <div className="eyebrow">AI-POWERED CODE SECURITY</div>
              <h1>Secure your code<br />before it ships.</h1>
              <p>
                Scan GitHub Pull Requests for exposed secrets and
                potential security risks using machine learning.
              </p>
            </section>

            <section className="scan-card">
              <div className="section-heading">
                <div>
                  <h2>Pull Request Scanner</h2>
                  <p>Enter a public GitHub Pull Request URL to begin.</p>
                </div>
                <span className="scan-icon">⌕</span>
              </div>

              <form onSubmit={handleScan}>
                <label htmlFor="pr-url">GitHub Pull Request URL</label>

                <div className="input-row">
                  <input
                    id="pr-url"
                    type="url"
                    placeholder="https://github.com/owner/repository/pull/1"
                    value={prUrl}
                    onChange={(e) => setPrUrl(e.target.value)}
                    required
                  />

                  <button type="submit" disabled={loading}>
                    {loading ? 'Scanning...' : 'Scan Pull Request →'}
                  </button>
                </div>
              </form>

              {loading && (
                <div className="loading-message">
                  <span className="loader"></span>
                  Analyzing changed files and checking for security risks...
                </div>
              )}

              {error && <div className="error-message">{error}</div>}
            </section>

            {result && (
              <section className="results-section">
                <div className="results-heading">
                  <div>
                    <div className="eyebrow">SCAN COMPLETED</div>
                    <h2>Security Scan Results</h2>
                  </div>
                  <span className="completed-badge">✓ Completed</span>
                </div>

                <div className="summary-grid">
                  <div className="result-card">
                    <span className="card-label">Secret Detection</span>
                    <h3 className={result.has_secret ? 'danger-text' : 'safe-text'}>
                      {result.has_secret ? 'Secret Found' : 'No Secret Found'}
                    </h3>
                    <p>
                      {result.secret_scan.rule_matches.length} rule match(es)
                    </p>
                  </div>

                  <div className="result-card">
                    <span className="card-label">PR Risk Level</span>
                    <h3 className={riskColor(result.pr_risk.risk_level)}>
                      {result.pr_risk.risk_level}
                    </h3>
                    <p>Machine learning prediction</p>
                  </div>

                  <div className="result-card">
                    <span className="card-label">Files Scanned</span>
                    <h3>{result.files_scanned}</h3>
                    <p>{result.files_skipped} file(s) skipped</p>
                  </div>

                  <div className="result-card">
                    <span className="card-label">PR Model Confidence</span>
                    <h3>
                      {(result.pr_risk.confidence * 100).toFixed(2)}%
                    </h3>
                    <p>Prediction confidence</p>
                  </div>
                </div>

                <div className="details-grid">
                  <div className="detail-card">
                    <h3>Secret Detection Details</h3>
                    <p className="muted">
                      ML prediction: {result.secret_scan.ml_prediction}
                    </p>
                    <p className="muted">
                      ML confidence: {(result.secret_scan.confidence * 100).toFixed(2)}%
                    </p>

                    <h4>Regex Findings</h4>

                    {result.secret_scan.rule_matches.length > 0 ? (
                      result.secret_scan.rule_matches.map((match, index) => (
                        <div className="finding" key={index}>
                          <strong>{match.secret_type}</strong>
                          <span>{match.matched_value}</span>
                          <small>Line {match.line_number}</small>
                        </div>
                      ))
                    ) : (
                      <p className="muted">No regex findings.</p>
                    )}

                    <h4>Entropy Findings</h4>

                    {result.secret_scan.entropy_flags.length > 0 ? (
                      result.secret_scan.entropy_flags.map((flag, index) => (
                        <div className="finding" key={index}>
                          <span>{JSON.stringify(flag)}</span>
                        </div>
                      ))
                    ) : (
                      <p className="muted">No high-entropy findings.</p>
                    )}
                  </div>

                  <div className="detail-card">
                    <h3>PR Risk Features</h3>
                    <p className="muted">
                      Features used by the Random Forest model
                    </p>

                    {Object.entries(result.pr_risk.features).map(([key, value]) => (
                      <div className="feature-row" key={key}>
                        <span>{key.replaceAll('_', ' ')}</span>
                        <strong>{value}</strong>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="scanned-url">
                  <strong>Scanned Pull Request:</strong>
                  <a href={result.pr_url} target="_blank" rel="noreferrer">
                    {result.pr_url}
                  </a>
                </div>
              </section>
            )}
          </>
        )}

        <footer>
          <span>GitGuard AI</span>
          <span>AI-powered Pull Request Security Analysis</span>
        </footer>
      </main>
    </div>
  )
}

export default App
