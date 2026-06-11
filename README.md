# NEXUS B2B Lead Generation & OSINT Intelligence Suite

NEXUS is an advanced B2B lead generation and intelligence platform combining:
- Automated scraping (Google Maps, LinkedIn, Playwright)
- OSINT enrichment (emails, phones, domains, breaches)
- AI reasoning (LLaMA, embeddings, summarization)
- FastAPI backend
- Web dashboard for real-time intelligence

This system is designed for agencies, investigators, growth teams, and analysts who need high‑quality, enriched business leads with minimal manual work.

---

## 🚀 Features

### 🔍 Lead Generation
- Google Maps business extraction
- LinkedIn company intelligence
- Multi-source enrichment
- Contact discovery (emails, phones, domains)

### 🕵️ OSINT Modules
- Email verification & breach lookup
- Phone intelligence
- Domain WHOIS + DNS + reputation
- Social footprint analysis

### 🤖 AI Intelligence
- Local LLaMA reasoning engine
- Lead scoring
- Company summaries
- Automated outreach message generation

### 🧩 Architecture
- Python backend (FastAPI)
- Playwright scraping engine
- SQLite/PostgreSQL database
- Web dashboard (HTML/JS/CSS)
- Tor routing support

---

## 📦 Installation

### Prerequisites
- Python 3.11+
- Node.js 18+ (for Playwright)
- Git

### Setup

```bash
# Clone repository
git clone https://github.com/burkefit2382/nexus-b2b-lead-generation.git
cd nexus-b2b-lead-generation

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install

# Copy environment template
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python -m nexus.database.init_db
```

---

## ▶️ Run the Server

```bash
# Start FastAPI server
python -m nexus.api.server

# Or use the script
bash scripts/run_server.sh  # Linux/Mac
# or
scripts\run_server.bat  # Windows
```

Server will be available at:
- **API**: http://localhost:8000
- **Dashboard**: http://localhost:8000/dashboard
- **API Docs**: http://localhost:8000/docs

---

## 📁 Project Structure

```
nexus-b2b-lead-generation/
│
├── README.md
├── LICENSE
├── .gitignore
├── requirements.txt
├── nexus/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── utils/
│   │   ├── logger.py
│   │   ├── helpers.py
│   │   └── validators.py
│   ├── scraping/
│   │   ├── playwright_scraper.py
│   │   ├── google_maps_scraper.py
│   │   ├── linkedin_scraper.py
│   │   └── tor_router.py
│   ├── osint/
│   │   ├── email_lookup.py
│   │   ├── phone_lookup.py
│   │   ├── domain_intel.py
│   │   └── breach_check.py
│   ├── ai/
│   │   ├── llama_engine.py
│   │   ├── embeddings.py
│   │   └── summarizer.py
│   ├── database/
│   │   ├── models.py
│   │   ├── schema.sql
│   │   └── repository.py
│   ├── api/
│   │   ├── server.py
│   │   ├── routes_leads.py
│   │   ├── routes_osint.py
│   │   └── routes_ai.py
│   └── dashboard/
│       ├── index.html
│       ├── app.js
│       └── styles.css
│
└── scripts/
    ├── install.sh
    ├── run_server.sh
    └── update_models.py
```

---

## 📝 License

MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.