import './style.css'
import * as Sentry from '@sentry/browser'

// Initialise Sentry — fully optional: app works fine when DSN is absent.
const sentryDsn = import.meta.env.VITE_SENTRY_DSN as string | undefined
if (sentryDsn) {
  Sentry.init({
    dsn: sentryDsn,
    environment: (import.meta.env.VITE_SENTRY_ENVIRONMENT as string | undefined) ?? 'production',
    // Low default sample rate — override via VITE_SENTRY_TRACES_SAMPLE_RATE.
    tracesSampleRate: parseFloat((import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE as string | undefined) ?? '0.1'),
    // Do not send PII (user IPs, etc.) automatically.
    sendDefaultPii: false,
  })
}

type Lead = {
  id: string
  name: string
  intent: string
  location: string
  email: string
}

type MembershipStatus = {
  status: string
  email: string
  current_period_end: string | null
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

const app = document.querySelector<HTMLDivElement>('#app')

if (app) {
  app.innerHTML = `
    <main>
      <h1>NEXUS B2B Lead Generation</h1>
      <p class="subtitle">MVP test dashboard</p>
      <section>
        <h2>API Health</h2>
        <p id="health">Checking backend...</p>
      </section>
      <section>
        <h2>Live Leads</h2>
        <ul id="leads"></ul>
      </section>
      <section id="membership-section">
        <h2>Paid Membership</h2>
        <p>Unlock full lead generation features with a paid subscription.</p>
        <form id="membership-form">
          <label for="membership-email">Your email</label>
          <input id="membership-email" type="email" placeholder="you@example.com" required />
          <button type="submit" id="membership-btn">Upgrade to Pro</button>
        </form>
        <p id="membership-status"></p>
        <p id="membership-error" style="color:red;display:none;"></p>
      </section>
    </main>
  `
}

const setHealth = (message: string) => {
  const health = document.querySelector<HTMLParagraphElement>('#health')
  if (health) health.textContent = message
}

const setLeads = (leads: Lead[]) => {
  const leadList = document.querySelector<HTMLUListElement>('#leads')
  if (!leadList) return
  if (leads.length === 0) {
    leadList.innerHTML = '<li>No leads returned.</li>'
    return
  }
  leadList.innerHTML = leads
    .map((lead) => `<li><strong>${lead.name}</strong> - ${lead.intent || 'New lead'} in ${lead.location || 'Unknown'} (${lead.email})</li>`)
    .join('')
}

const loadData = async () => {
  try {
    const healthResponse = await fetch(`${apiBaseUrl}/health`)
    if (!healthResponse.ok) throw new Error('Healthcheck failed')
    const healthData = await healthResponse.json() as { status: string }
    setHealth(`Backend status: ${healthData.status}`)

    const leadsResponse = await fetch(`${apiBaseUrl}/leads/`)
    if (!leadsResponse.ok) throw new Error('Lead request failed')
    const leadsData = await leadsResponse.json() as Lead[]
    setLeads(leadsData.slice(0, 5))
  } catch (error) {
    setHealth('Backend unavailable. Start backend service to test full flow.')
    setLeads([])
    console.error(error)
  }
}

const checkMembershipStatus = async (email: string) => {
  const statusEl = document.querySelector<HTMLParagraphElement>('#membership-status')
  if (!statusEl) return
  try {
    const res = await fetch(`${apiBaseUrl}/api/membership/status?email=${encodeURIComponent(email)}`)
    if (res.ok) {
      const data = await res.json() as MembershipStatus
      const until = data.current_period_end
        ? ` (active until ${new Date(data.current_period_end).toLocaleDateString()})`
        : ''
      statusEl.textContent = `Membership status: ${data.status}${until}`
    } else if (res.status === 404) {
      statusEl.textContent = 'No membership found for this email.'
    }
  } catch {
    statusEl.textContent = ''
  }
}

const form = document.querySelector<HTMLFormElement>('#membership-form')
form?.addEventListener('submit', async (e) => {
  e.preventDefault()
  const emailInput = document.querySelector<HTMLInputElement>('#membership-email')
  const btn = document.querySelector<HTMLButtonElement>('#membership-btn')
  const errorEl = document.querySelector<HTMLParagraphElement>('#membership-error')
  const email = emailInput?.value.trim() ?? ''
  if (!email) return

  if (btn) btn.disabled = true
  if (errorEl) errorEl.style.display = 'none'

  try {
    const res = await fetch(`${apiBaseUrl}/api/membership/checkout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    })
    const data = await res.json() as { checkout_url?: string; detail?: string }
    if (!res.ok) {
      throw new Error(data.detail ?? 'Checkout failed.')
    }
    if (data.checkout_url) {
      window.location.href = data.checkout_url
    }
  } catch (err) {
    if (errorEl) {
      errorEl.textContent = err instanceof Error ? err.message : 'An error occurred.'
      errorEl.style.display = 'block'
    }
    if (btn) btn.disabled = false
  }
})

// Auto-check membership if email is in URL params (e.g., after redirect back).
const urlEmail = new URLSearchParams(window.location.search).get('email')
if (urlEmail) {
  const emailInput = document.querySelector<HTMLInputElement>('#membership-email')
  if (emailInput) emailInput.value = urlEmail
  void checkMembershipStatus(urlEmail)
}

void loadData()

