// NEXUS Dashboard JavaScript

const API_BASE = '/api';

// Initialize dashboard
async function initDashboard() {
    console.log('Initializing NEXUS Dashboard...');
    await loadStats();
    await loadLeads();
    checkSystemStatus();
}

// Load statistics
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/leads/`);
        const leads = await response.json();

        document.getElementById('total-leads').textContent = leads.length;
        document.getElementById('high-quality').textContent = leads.filter(l => l.quality_score >= 70).length;
        document.getElementById('recent-scrape').textContent = leads.slice(-5).length;

        logToConsole(`Loaded ${leads.length} leads`);
    } catch (error) {
        logToConsole(`Error loading stats: ${error.message}`, 'error');
    }
}

// Load leads
async function loadLeads(minQuality = 0) {
    try {
        const response = await fetch(`${API_BASE}/leads/?min_quality=${minQuality}`);
        const leads = await response.json();

        const leadsList = document.getElementById('leads-list');
        leadsList.innerHTML = '';

        if (leads.length === 0) {
            leadsList.innerHTML = '<p class="loading">No leads found</p>';
            return;
        }

        leads.slice(0, 10).forEach(lead => {
            const qualityClass = lead.quality_score >= 70 ? 'quality-high' :
                               lead.quality_score >= 40 ? 'quality-medium' : 'quality-low';

            const leadItem = document.createElement('div');
            leadItem.className = 'lead-item';
            leadItem.innerHTML = `
                <div class="lead-name">${lead.company_name}</div>
                <div class="lead-details">
                    ${lead.website ? `🌐 ${lead.website}` : ''}
                    ${lead.email ? ` | ✉️ ${lead.email}` : ''}
                    ${lead.phone ? ` | 📞 ${lead.phone}` : ''}
                </div>
                <div style="margin-top: 8px;">
                    <span class="quality-badge ${qualityClass}">
                        Score: ${lead.quality_score.toFixed(1)}
                    </span>
                </div>
            `;
            leadItem.onclick = () => showLeadDetails(lead);
            leadsList.appendChild(leadItem);
        });

        logToConsole(`Loaded ${leads.length} leads`);
    } catch (error) {
        logToConsole(`Error loading leads: ${error.message}`, 'error');
    }
}

// Check system status
async function checkSystemStatus() {
    try {
        const response = await fetch('/health');
        const status = await response.json();
        document.getElementById('system-status').textContent = '✅ Online';
        document.getElementById('system-status').style.color = '#10b981';
        logToConsole('System status: Online');
    } catch (error) {
        document.getElementById('system-status').textContent = '❌ Offline';
        document.getElementById('system-status').style.color = '#ef4444';
        logToConsole('System status: Offline', 'error');
    }
}

// Scrape Google Maps
async function scrapeGoogleMaps() {
    const query = prompt('Enter search query (e.g., "restaurants new york"):');
    if (!query) return;

    logToConsole(`Starting Google Maps search for: ${query}`);
    // Implementation would call API endpoint
    alert('Google Maps scraping would be implemented here');
}

// Scrape LinkedIn
async function scrapeLinkedIn() {
    const companyUrl = prompt('Enter LinkedIn company URL:');
    if (!companyUrl) return;

    logToConsole(`Starting LinkedIn scrape for: ${companyUrl}`);
    // Implementation would call API endpoint
    alert('LinkedIn scraping would be implemented here');
}

// Run OSINT check
async function runOSINT() {
    const domain = prompt('Enter domain for OSINT check:');
    if (!domain) return;

    logToConsole(`Running OSINT check for: ${domain}`);
    try {
        const response = await fetch(`${API_BASE}/osint/domain/whois`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ domain })
        });
        const result = await response.json();
        logToConsole(`OSINT result: ${JSON.stringify(result, null, 2)}`);
    } catch (error) {
        logToConsole(`OSINT check failed: ${error.message}`, 'error');
    }
}

// Generate AI analysis
async function generateAI() {
    const leadId = prompt('Enter lead ID for AI analysis:');
    if (!leadId) return;

    logToConsole(`Running AI analysis for lead ${leadId}`);
    try {
        const response = await fetch(`${API_BASE}/ai/analyze`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ lead_id: parseInt(leadId) })
        });
        const result = await response.json();
        logToConsole(`AI Analysis: ${JSON.stringify(result, null, 2)}`);
    } catch (error) {
        logToConsole(`AI analysis failed: ${error.message}`, 'error');
    }
}

// Search leads
async function searchLeads() {
    const query = document.getElementById('search-input').value;
    if (!query) return;

    logToConsole(`Searching for: ${query}`);
    // Implementation would filter leads
    await loadLeads();
}

// Export leads
async function exportLeads() {
    try {
        const response = await fetch(`${API_BASE}/leads/`);
        const leads = await response.json();

        const csv = [
            ['Company', 'Website', 'Email', 'Phone', 'Quality Score'].join(','),
            ...leads.map(l => [
                `"${l.company_name}"`,
                `"${l.website || ''}"`,
                `"${l.email || ''}"`,
                `"${l.phone || ''}"`,
                l.quality_score
            ].join(','))
        ].join('\n');

        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'nexus_leads.csv';
        a.click();

        logToConsole(`Exported ${leads.length} leads to CSV`);
    } catch (error) {
        logToConsole(`Export failed: ${error.message}`, 'error');
    }
}

// Call custom API
async function callAPI() {
    const url = document.getElementById('api-url').value;
    if (!url) return;

    logToConsole(`Calling API: ${url}`);
    try {
        const response = await fetch(url);
        const result = await response.json();
        logToConsole(`Response: ${JSON.stringify(result, null, 2)}`);
    } catch (error) {
        logToConsole(`API call failed: ${error.message}`, 'error');
    }
}

// Show lead details
function showLeadDetails(lead) {
    const details = `
Company: ${lead.company_name}
Website: ${lead.website || 'N/A'}
Email: ${lead.email || 'N/A'}
Phone: ${lead.phone || 'N/A'}
Address: ${lead.address || 'N/A'}
Quality Score: ${lead.quality_score.toFixed(1)}
Source: ${lead.source || 'N/A'}
    `.trim();

    alert(details);
    logToConsole(`Viewing details for: ${lead.company_name}`);
}

// Log to console
function logToConsole(message, type = 'info') {
    const consoleOutput = document.getElementById('console-output');
    const timestamp = new Date().toLocaleTimeString();
    const prefix = type === 'error' ? '❌' : '✅';
    consoleOutput.value += `[${timestamp}] ${prefix} ${message}\n`;
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

// Initialize on load
window.onload = initDashboard;