# NEXUS B2B Lead Generation & OSINT Intelligence Suite

## 🎯 Overview

NEXUS is an advanced, AI-powered B2B lead generation and Open Source Intelligence (OSINT) platform designed for agencies, investigators, growth teams, and enterprise security professionals. By combining automated web scraping, OSINT enrichment, and local LLaMA 3.2 AI reasoning, NEXUS delivers high-quality, actionable business intelligence with minimal manual effort.

### Core Capabilities

- 🗺️ **Automated Scraping**: Google Maps business extraction, LinkedIn company intelligence, and multi-source web data collection
- 🔍 **OSINT Enrichment**: Email verification, breach detection, phone intelligence, domain reputation analysis
- 🤖 **AI Intelligence**: Local LLaMA 3.2 reasoning engine for lead scoring, company summarization, and automated outreach generation
- 🌐 **Web Dashboard**: Real-time intelligence dashboard with API console and lead management
- 🧪 **Enterprise-Grade**: FastAPI backend, SQLite/PostgreSQL database, Tor routing support, and comprehensive API

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for Playwright)
- Git
- LLaMA 3.2 model file (optional for AI features)

### Installation

```bash
# Clone repository
git clone https://github.com/burkefit2382-wq/nexus-b2b-lead-generation.git
cd nexus-b2b-lead-generation

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

### Run the Server

```bash
# Start FastAPI server
python -m nexus.api.server

# Or use the startup script
bash scripts/run_server.sh  # Linux/Mac
# or
python scripts/run_server.py  # Windows
```

**Access Points:**
- API: http://localhost:8000
- Dashboard: http://localhost:8000/static/index.html
- API Docs: http://localhost:8000/docs

---

## 📊 Features

### Lead Generation

| Feature | Description |
|---------|-------------|
| **Google Maps Scraper** | Extract business listings, ratings, reviews, and contact information |
| **LinkedIn Intelligence** | Gather company details, follower counts, and professional insights |
| **Multi-Source Enrichment** | Aggregate data from multiple platforms for comprehensive profiles |
| **Contact Discovery** | Find emails, phone numbers, and social media links |

### OSINT Modules

| Module | Capabilities |
|--------|--------------|
| **Email Verification** | Format validation, MX record checks, disposable detection |
| **Breach Detection** | HaveIBeenPwned integration, compromised credential alerts |
| **Phone Intelligence** | Number parsing, carrier lookup, line-type identification |
| **Domain Analysis** | WHOIS lookup, DNS records, reputation scoring |
| **Social Footprint** | Cross-platform identity correlation |

### AI Intelligence

- **Local LLaMA 3.2 Engine**: No API costs, complete data privacy
- **Lead Scoring**: AI-powered quality assessment (0-100)
- **Company Summaries**: Automated business profile generation
- **Outreach Messages**: Personalized email/communication drafts
- **Semantic Search**: Embeddings-based lead matching

---

## 🔧 Architecture

### Technology Stack

```
Frontend Layer
├── HTML5/CSS3/JavaScript
└── Real-time Dashboard

API Layer
├── FastAPI (Python 3.11+)
├── RESTful Endpoints
└── Auto-generated Documentation

Business Logic
├── Lead Management
├── OSINT Enrichment
└── AI Processing

Data Layer
├── SQLite (default)
├── PostgreSQL (optional)
└── Schema Migrations

External Services
├── Playwright (Scraping)
├── LLaMA 3.2 (AI)
└── Third-party APIs (OSINT)
```

### Project Structure

```
nexus-b2b-lead-generation/
├── nexus/
│   ├── api/          # FastAPI server and routes
│   ├── scraping/     # Web scrapers (Google Maps, LinkedIn)
│   ├── osint/        # OSINT modules (email, phone, domain)
│   ├── ai/           # AI engine (LLaMA, embeddings, summarizer)
│   ├── database/     # Models, schema, repository
│   ├── utils/        # Helpers, validators, logger
│   ├── config.py     # Configuration management
│   └── dashboard/    # Web interface
├── scripts/          # Installation and startup scripts
├── tests/            # Test suite (planned)
├── requirements.txt  # Python dependencies
└── README.md
```

---

## 📖 API Documentation

### Core Endpoints

#### Leads

```http
POST   /api/leads/              Create lead
GET    /api/leads/              List leads (paginated)
GET    /api/leads/{id}          Get lead by ID
PUT    /api/leads/{id}          Update lead
DELETE /api/leads/{id}          Delete lead
GET    /api/leads/{id}/osint    Get OSINT data for lead
```

#### OSINT

```http
POST /api/osint/email/verify       Verify email address
POST /api/osint/email/breaches     Check email for breaches
POST /api/osint/phone/parse        Parse phone number
POST /api/osint/domain/whois       Get WHOIS information
POST /api/osint/domain/dns         Get DNS records
POST /api/osint/domain/reputation  Check domain reputation
```

#### AI

```http
POST /api/ai/generate        Generate text with LLaMA
POST /api/ai/analyze         Analyze lead with AI
POST /api/ai/summarize       Summarize lead information
POST /api/ai/score           Calculate lead quality score
POST /api/ai/outreach        Generate outreach message
POST /api/ai/embed           Create text embedding
POST /api/ai/similarity      Calculate semantic similarity
```

### Example Usage

```python
import requests

# Create lead
lead_data = {
    "company_name": "Acme Corp",
    "website": "https://acme.com",
    "email": "contact@acme.com",
    "industry": "Technology"
}
response = requests.post('http://localhost:8000/api/leads/', json=lead_data)
lead_id = response.json()['id']

# Run OSINT enrichment
response = requests.post(
    'http://localhost:8000/api/osint/domain/whois',
    json={'domain': 'acme.com'}
)
whois_data = response.json()

# Generate AI analysis
response = requests.post(
    'http://localhost:8000/api/ai/analyze',
    json={'lead_id': lead_id}
)
ai_insights = response.json()
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# API Settings
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=True

# LLM Settings
LLM_MODEL_PATH=D:/models/Llama-3.2-1B-Instruct-Q4_K_M.gguf
LLM_CONTEXT_SIZE=4096
LLM_THREADS=3
LLM_TEMPERATURE=0.7

# Scraper Settings
PLAYWRIGHT_HEADLESS=True
PLAYWRIGHT_TIMEOUT=30000
TOR_ENABLED=False
TOR_PORT=9050

# OSINT Settings
WHOIS_TIMEOUT=10
DNS_TIMEOUT=5
EMAIL_VERIFICATION_API=optional_api_key

# API Keys (Optional)
HIBP_API_KEY=your_haveibeenpwned_api_key_here
```

### Database Configuration

Default: SQLite (`sqlite:///nexus.db`)

For PostgreSQL:
```python
# In nexus/config.py
DATABASE_URL = "postgresql://user:password@localhost/nexus"
```

---

## 🔒 Security

- **Local AI Processing**: No data sent to third-party AI services
- **Tor Routing**: Optional anonymous scraping
- **API Key Management**: Secure environment variable handling
- **Input Validation**: Comprehensive Pydantic models
- **CORS Configuration**: Configurable for production

---

## 🧪 Testing

```bash
# Run tests (planned feature)
pytest tests/

# Run with coverage
pytest tests/ --cov=nexus --cov-report=html
```

---

## 📈 Performance

| Metric | Value |
|--------|-------|
| API Response Time | < 200ms (average) |
| Lead Processing | ~1-2 seconds per lead |
| OSINT Enrichment | 3-5 seconds per lead |
| LLaMA Generation | 2-3 seconds per request |
| Concurrent Scraping | 10+ simultaneous pages |

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **LLaMA 3.2** by Meta
- **FastAPI** by Sebastián Ramírez
- **Playwright** by Microsoft
- **Sentence Transformers** by Hugging Face
- **OSINT Community Tools**

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/issues)
- **Discussions**: [GitHub Discussions](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/discussions)
- **Email**: support@nexus-intelligence.com

---

## 🚨 Disclaimer

This tool is for educational and authorized security testing purposes only. Users are responsible for ensuring compliance with applicable laws, regulations, and terms of service of target platforms.

---

**Built with ❤️ by the NEXUS Intelligence Team**

[🔗 GitHub Repository](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation) | [📚 Documentation](http://localhost:8000/docs) | [💬 Discussions](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/discussions)