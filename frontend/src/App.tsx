import { useState } from 'react'
import './App.css'

interface Lead {
  id: string
  company: string
  contact_name: string
  email: string | null
  phone: string | null
  website: string | null
  industry: string | null
  location: string | null
  score: number
}

const API_BASE = import.meta.env.VITE_API_URL ?? ''

function App() {
  const [companyName, setCompanyName] = useState('')
  const [industry, setIndustry] = useState('')
  const [location, setLocation] = useState('')
  const [limit, setLimit] = useState(10)
  const [leads, setLeads] = useState<Lead[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searched, setSearched] = useState(false)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!companyName.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/leads/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_name: companyName.trim(),
          industry: industry || undefined,
          location: location || undefined,
          limit,
        }),
      })
      if (!res.ok) throw new Error(`Server error: ${res.status}`)
      const data = await res.json()
      setLeads(data.leads)
      setSearched(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const scoreColor = (score: number) => {
    if (score >= 80) return '#22c55e'
    if (score >= 60) return '#f59e0b'
    return '#ef4444'
  }

  return (
    <div className="nexus-app">
      <header className="nexus-header">
        <h1>⚡ NEXUS Intelligence Platform</h1>
        <p>Data Intelligence • Autonomous OSINT • AI‑Driven Lead Generation</p>
      </header>

      <main className="nexus-main">
        <form className="search-form" onSubmit={handleSearch}>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="company">Target Company *</label>
              <input
                id="company"
                type="text"
                placeholder="e.g. Acme Corp"
                value={companyName}
                onChange={e => setCompanyName(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="industry">Industry</label>
              <input
                id="industry"
                type="text"
                placeholder="e.g. SaaS"
                value={industry}
                onChange={e => setIndustry(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label htmlFor="location">Location</label>
              <input
                id="location"
                type="text"
                placeholder="e.g. New York"
                value={location}
                onChange={e => setLocation(e.target.value)}
              />
            </div>
            <div className="form-group form-group--sm">
              <label htmlFor="limit">Limit</label>
              <input
                id="limit"
                type="number"
                min={1}
                max={100}
                value={limit}
                onChange={e => setLimit(Number(e.target.value))}
              />
            </div>
          </div>
          <button type="submit" className="btn-search" disabled={loading}>
            {loading ? 'Scanning…' : '🔍 Generate Leads'}
          </button>
        </form>

        {error && <div className="error-banner">⚠ {error}</div>}

        {searched && !loading && (
          <div className="results">
            <h2>{leads.length} leads found for <em>{companyName}</em></h2>
            {leads.length === 0 ? (
              <p>No leads found. Try a different search.</p>
            ) : (
              <div className="table-wrapper">
                <table className="leads-table">
                  <thead>
                    <tr>
                      <th>Contact</th>
                      <th>Email</th>
                      <th>Phone</th>
                      <th>Industry</th>
                      <th>Location</th>
                      <th>Website</th>
                      <th>Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leads.map(lead => (
                      <tr key={lead.id}>
                        <td>{lead.contact_name}</td>
                        <td>{lead.email ?? '—'}</td>
                        <td>{lead.phone ?? '—'}</td>
                        <td>{lead.industry ?? '—'}</td>
                        <td>{lead.location ?? '—'}</td>
                        <td>
                          {lead.website
                            ? <a href={lead.website} target="_blank" rel="noreferrer">🔗 link</a>
                            : '—'}
                        </td>
                        <td>
                          <span
                            className="score-badge"
                            style={{ backgroundColor: scoreColor(lead.score) }}
                          >
                            {lead.score}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

export default App
