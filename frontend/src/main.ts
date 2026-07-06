import './style.css'

type Lead = {
  id: string
  name: string
  intent: string
  location: string
  email: string
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

void loadData()
