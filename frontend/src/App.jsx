
import { useState, useEffect } from 'react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

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

  // Fetch dashboard data
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

    // Automatically refresh every 10 seconds
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

      // Refresh dashboard after a successful manual scan
      setRefreshKey((key) => key + 1)
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  // Risk-level CSS class
  const riskColor = (level) => {
    const normalizedLevel = String(level || '').toUpperCase()

    if (normalizedLevel === 'HIGH') return 'high'
    if (normalizedLevel === 'MEDIUM') return 'medium'

    return 'low'
  }

  // Format date and time
  const formatDate = (date) => {
    if (!date) return 'Date unavailable'

    const parsedDate = new Date(date)

    if (Number.isNaN(parsedDate.getTime())) {
      return 'Date unavailable'
    }

    return parsedDate.toLocaleString()
  }

  // Convert confidence from decimal to percentage
  const formatConfidence = (confidence) => {
    if (confidence === null || confidence === undefined) {
      return 'N/A'
    }

    return `${(Number(confidence) * 100).toFixed(2)}%`
  }

  // Get Pull Request number from GitHub URL
  const getPRNumber = (url) => {
    if (!url) return null

    const match = url.match(/\/pull\/(\d+)/)

    return match ? match[1] : null
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

                {/* Recent scan activity */}
                <section className="activity-section">

                  <div className="activity-heading">
                    <div>
                      <h2>Recent Scan Activity</h2>
                      <p>
                        Latest GitHub push and Pull Request security scans
                      </p>
                    </div>

                    <span className="scan-count">
                      {recentScans.length} recent scans
                    </span>
                  </div>

                  {recentScans.length === 0 ? (
                    <p className="muted">
                      No scan history available yet.
                    </p>
                  ) : (
                    <div className="activity-table-wrap">
                      <table className="activity-table">
                        <thead>
                          <tr>
                            <th>Repository / Event</th>
                            <th>Secret Detection</th>
                            <th>PR Risk</th>
                            <th>ML Confidence</th>
                            <th>Files</th>
                            <th>Findings</th>
                            <th>Status</th>
                            <th>Date</th>
                            <th>Action</th>
                          </tr>
                        </thead>

                        <tbody>
                          {recentScans.map((scan) => {
                            const isPR = scan.event_type === 'pull_request'
                            const prNumber = getPRNumber(scan.pr_url)

                            return (
                              <tr key={scan.id}>

                                {/* Repository and event */}
                                <td>
                                  <div className="table-repository">
                                    <strong>
                                      {scan.repository || 'Unknown repository'}
                                    </strong>

                                    <span className="event-label">
                                      {isPR
                                        ? `Pull Request · ${scan.action || 'scan'}`
                                        : 'Push event'}
                                    </span>

                                    <small>
                                      {scan.branch || 'Branch unavailable'}
                                    </small>
                                  </div>
                                </td>

                                {/* Secret detection */}
                                <td>
                                  <span className={
                                    scan.has_secret
                                      ? 'table-status danger-text'
                                      : 'table-status safe-text'
                                  }>
                                    {scan.has_secret
                                      ? '● Secret detected'
                                      : '● No secret'}
                                  </span>

                                  <small className="table-subtext">
                                    ML: {scan.ml_prediction || 'N/A'}
                                  </small>

                                  <small className="table-subtext">
                                    Confidence: {formatConfidence(scan.secret_confidence)}
                                  </small>
                                </td>

                                {/* PR risk */}
                                <td>
                                  {scan.risk_level ? (
                                    <span className={`risk-badge ${riskColor(scan.risk_level)}`}>
                                      {String(scan.risk_level).toUpperCase()}
                                    </span>
                                  ) : (
                                    <span className="muted">N/A</span>
                                  )}
                                </td>

                                {/* PR risk confidence */}
                                <td>
                                  {scan.risk_confidence !== null &&
                                  scan.risk_confidence !== undefined
                                    ? formatConfidence(scan.risk_confidence)
                                    : 'N/A'}
                                </td>

                                {/* Files scanned */}
                                <td>
                                  {scan.files_scanned ?? 0}
                                </td>

                                {/* Rule and entropy findings */}
                                <td>
                                  <div className="finding-count">
                                    <span>Rules: {scan.rule_findings ?? 0}</span>
                                    <span>Entropy: {scan.entropy_findings ?? 0}</span>
                                  </div>
                                </td>

                                {/* Scan status */}
                                <td>
                                  <span className={
                                    scan.scan_status === 'completed'
                                      ? 'scan-status-completed'
                                      : 'scan-status-pending'
                                  }>
                                    {scan.scan_status || 'Unknown'}
                                  </span>
                                </td>

                                {/* Date */}
                                <td className="table-date">
                                  {formatDate(scan.created_at)}
                                </td>

                                {/* GitHub action */}
                                <td>
                                  {isPR && scan.pr_url ? (
                                    <a
                                      className="github-link"
                                      href={scan.pr_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                    >
                                      {prNumber ? `View PR #${prNumber}` : 'View PR'}
                                      {' ↗'}
                                    </a>
                                  ) : (
                                    <span className="muted">Push scan</span>
                                  )}
                                </td>

                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}

                  <p className="activity-auto-refresh">
                    Dashboard automatically refreshes every 10 seconds.
                  </p>

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
