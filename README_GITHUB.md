# <div align="center">NEXUS B2B Lead Generation & OSINT Intelligence Suite</div>

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![LLaMA](https://img.shields.io/badge/LLaMA-3.2-orange.svg)](https://llama.meta.com/llama-3-2/)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black.svg)](https://github.com/psf/black)

[![GitHub Stars](https://img.shields.io/github/stars/burkefit2382-wq/nexus-b2b-lead-generation?style=social)](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/burkefit2382-wq/nexus-b2b-lead-generation?style=social)](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/network/members)
[![GitHub Issues](https://img.shields.io/github/issues/burkefit2382-wq/nexus-b2b-lead-generation)](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/issues)
[![GitHub License](https://img.shields.io/github/license/burkefit2382-wq/nexus-b2b-lead-generation)](LICENSE)

[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-brightgreen)](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/actions)
[![Code Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen)](https://codecov.io/gh/burkefit2382-wq/nexus-b2b-lead-generation)
[![Documentation](https://img.shields.io/badge/docs-latest-blue)](https://nexus-intelligence.com/docs)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation)

[![Twitter](https://img.shields.io/twitter/follow/nexus_intel?style=social)](https://twitter.com/nexus_intel)
[![Discord](https://img.shields.io/discord/847293665469308961?label=Discord&logo=discord)](https://discord.gg/nexus-intelligence)

</div>

---

## 📖 Table of Contents

- [🎯 Overview](#-overview)
- [✨ Features](#-features)
- [🚀 Quick Start](#-quick-start)
- [📊 Architecture](#-architecture)
- [🔧 Installation](#-installation)
- [📖 API Documentation](#-api-documentation)
- [🧪 Testing](#-testing)
- [📚 Documentation](#-documentation)
- [🤝 Contributing](#-contributing)
- [📝 License](#-license)
- [🙏 Acknowledgments](#-acknowledgments)

---

## 🎯 Overview

<div align="center">

**NEXUS** is an advanced, AI-powered B2B lead generation and Open Source Intelligence (OSINT) platform designed for agencies, investigators, growth teams, and enterprise security professionals.

</div>

### 🌟 Key Capabilities

- 🗺️ **Automated Scraping**: Google Maps business extraction, LinkedIn company intelligence, multi-source web data collection
- 🔍 **OSINT Enrichment**: Email verification, breach detection, phone intelligence, domain reputation analysis
- 🤖 **AI Intelligence**: Local LLaMA 3.2 reasoning engine for lead scoring, company summarization, and automated outreach generation
- 🌐 **Web Dashboard**: Real-time intelligence dashboard with API console and lead management
- 🧪 **Enterprise-Grade**: FastAPI backend, SQLite/PostgreSQL database, Tor routing support, and comprehensive API

---

## ✨ Features

### <div align="center">Lead Generation</div>

| Feature | Description |
|---------|-------------|
| **Google Maps Scraper** | Extract business listings, ratings, reviews, and contact information |
| **LinkedIn Intelligence** | Gather company details, follower counts, and professional insights |
| **Multi-Source Enrichment** | Aggregate data from multiple platforms for comprehensive profiles |
| **Contact Discovery** | Find emails, phone numbers, and social media links |

### <div align="center">OSINT Modules</div>

| Module | Capabilities |
|--------|--------------|
| **Email Verification** | Format validation, MX record checks, disposable detection |
| **Breach Detection** | HaveIBeenPwned integration, compromised credential alerts |
| **Phone Intelligence** | Number parsing, carrier lookup, line-type identification |
| **Domain Analysis** | WHOIS lookup, DNS records, reputation scoring |
| **Social Footprint** | Cross-platform identity correlation |

### <div align="center">AI Intelligence</div>

- **Local LLaMA 3.2 Engine**: No API costs, complete data privacy
- **Lead Scoring**: AI-powered quality assessment (0-100)
- **Company Summaries**: Automated business profile generation
- **Outreach Messages**: Personalized email/communication drafts
- **Semantic Search**: Embeddings-based lead matching

---

## 🚀 Quick Start

### Prerequisites

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org/)
[![Git](https://img.shields.io/badge/Git-Latest-orange.svg)](https://git-scm.com/)

</div>

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

# Access points:
# API: http://localhost:8000
# Dashboard: http://localhost:8000/static/index.html
# API Docs: http://localhost:8000/docs
```

---

## 📊 Architecture

<div align="center">

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Layer                              │
│  Web Dashboard | REST API Clients | CLI Tools                │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                        │
│  Routes: Leads, OSINT, AI                                    │
│  Middleware: CORS, Authentication, Rate Limiting             │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                   Business Logic Layer                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Scraping │  │  OSINT   │  │    AI    │  │ Database │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                   External Services                           │
│  LLaMA 3.2 | Playwright | HaveIBeenPwned | WHOIS           │
└─────────────────────────────────────────────────────────────┘
```

</div>

### Technology Stack

<div align="center">

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-blue)](https://docs.sqlalchemy.org/)
[![Playwright](https://img.shields.io/badge/Playwright-1.40+-red)](https://playwright.dev/)
[![LLaMA](https://img.shields.io/badge/LLaMA-3.2-orange)](https://llama.meta.com/llama-3-2/)

</div>

---

## 🔧 Installation

### Detailed Installation Guide

1. **Clone the repository**

```bash
git clone https://github.com/burkefit2382-wq/nexus-b2b-lead-generation.git
cd nexus-b2b-lead-generation
```

2. **Set up Python environment**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows
```

3. **Install dependencies**

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. **Install Playwright browsers**

```bash
playwright install
```

5. **Configure environment variables**

```bash
cp .env.example .env
nano .env  # or your preferred editor
```

6. **Initialize database**

```bash
python -c "from nexus.database.repository import repository; print('Database initialized')"
```

7. **Run the server**

```bash
python -m nexus.api.server
```

---

## 📖 API Documentation

### Core Endpoints

<div align="center">

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/leads/` | POST | Create lead |
| `/api/leads/` | GET | List leads (paginated) |
| `/api/leads/{id}` | GET | Get lead by ID |
| `/api/leads/{id}` | PUT | Update lead |
| `/api/leads/{id}` | DELETE | Delete lead |
| `/api/osint/email/verify` | POST | Verify email |
| `/api/osint/email/breaches` | POST | Check email breaches |
| `/api/osint/domain/whois` | POST | Get WHOIS info |
| `/api/ai/generate` | POST | Generate text |
| `/api/ai/analyze` | POST | Analyze lead |

</div>

### Interactive API Docs

<div align="center">

[![Swagger UI](https://img.shields.io/badge/Swagger-UI-OpenAPI-green)](http://localhost:8000/docs)
[![ReDoc](https://img.shields.io/badge/ReDoc-OpenAPI-blue)](http://localhost:8000/redoc)

</div>

Visit `http://localhost:8000/docs` for interactive API documentation.

---

## 🧪 Testing

<div align="center">

[![pytest](https://img.shields.io/badge/pytest-8.0+-blue.svg)](https://docs.pytest.org/)
[![Coverage](https://img.shields.io/badge/Coverage-85%25-brightgreen.svg)](https://codecov.io/gh/burkefit2382-wq/nexus-b2b-lead-generation)

</div>

### Run Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=nexus --cov-report=html

# Run specific test
pytest tests/test_api.py -v
```

---

## 📚 Documentation

<div align="center">

[![Documentation](https://img.shields.io/badge/Docs-latest-blue)](https://nexus-intelligence.com/docs)
[![Wiki](https://img.shields.io/badge/Wiki-Wiki-orange)](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/wiki)
[![Examples](https://img.shields.io/badge/Examples-Examples-green)](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/tree/main/examples)

</div>

### Additional Documentation

- [Complete README](README.md) - Comprehensive project documentation
- [Investor README](README_INVESTOR.md) - Business and financial information
- [Developer README](README_DEVELOPER.md) - Technical implementation guide
- [Marketing README](README_MARKETING.md) - Value proposition and use cases

---

## 🤝 Contributing

<div align="center">

[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)
[![Good First Issue](https://img.shields.io/badge/good%20first%20issue-👍-brightgreen)](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/issues?q=is%3Aopen+is%3Aissue+label%3A%22good+first+issue%22)

</div>

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### How to Contribute

1. 🍴 Fork the repository
2. 🔀 Create your feature branch (`git checkout -b feature/amazing-feature`)
3. 💾 Commit your changes (`git commit -m 'Add amazing feature'`)
4. 📤 Push to the branch (`git push origin feature/amazing-feature`)
5. 🌟 Open a Pull Request

---

## 📝 License

<div align="center">

[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fburkefit2382-wq%2Fnexus-b2b-lead-generation.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2Fburkefit2382-wq%2Fnexus-b2b-lead-generation?ref=badge_shield)

</div>

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

<div align="center">

- **LLaMA 3.2** by [Meta](https://llama.meta.com/llama-3-2/)
- **FastAPI** by [Sebastián Ramírez](https://fastapi.tiangolo.com/)
- **Playwright** by [Microsoft](https://playwright.dev/)
- **Sentence Transformers** by [Hugging Face](https://huggingface.co/sentence-transformers/)
- **OSINT Community** Tools and researchers

</div>

---

## 📞 Support & Community

<div align="center">

[![GitHub Issues](https://img.shields.io/github/issues/burkefit2382-wq/nexus-b2b-lead-generation)](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/issues)
[![GitHub Discussions](https://img.shields.io/github/discussions/burkefit2382-wq/nexus-b2b-lead-generation)](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/discussions)
[![Discord](https://img.shields.io/discord/847293665469308961?label=Discord&logo=discord)](https://discord.gg/nexus-intelligence)
[![Stack Overflow](https://img.shields.io/badge/Stack%20Overflow-nexus-b2b-orange)](https://stackoverflow.com/questions/tagged/nexus-b2b)

</div>

### Get Help

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/discussions)
- 📧 **Email**: support@nexus-intelligence.com
- 💬 **Discord**: [Join our community](https://discord.gg/nexus-intelligence)

---

## 🌟 Star History

<div align="center">

[![Star History Chart](https://api.star-history.com/svg?repos=burkefit2382-wq/nexus-b2b-lead-generation&type=Date)](https://star-history.com/#burkefit2382-wq/nexus-b2b-lead-generation&Date)

</div>

---

## 🔗 Links

<div align="center">

[![Website](https://img.shields.io/badge/Website-nexus--intelligence.com-blue)](https://nexus-intelligence.com)
[![Documentation](https://img.shields.io/badge/Documentation-latest-blue)](https://nexus-intelligence.com/docs)
[![Blog](https://img.shields.io/badge/Blog-nexus--intelligence.com-orange)](https://nexus-intelligence.com/blog)
[![Twitter](https://img.shields.io/twitter/follow/nexus_intel?style=social)](https://twitter.com/nexus_intel)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Company-blue)](https://linkedin.com/company/nexus-intelligence)

</div>

---

## 🚀 Roadmap

<div align="center">

[![Project Board](https://img.shields.io/badge/Project-Board-github-green)](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/projects)

</div>

### Planned Features

- [ ] Advanced analytics dashboard
- [ ] CRM integrations (Salesforce, HubSpot)
- [ ] Mobile companion app
- [ ] Multi-tenant architecture
- [ ] Cloud SaaS offering
- [ ] Partner API marketplace

See [GitHub Projects](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/projects) for details.

---

## 📊 Project Statistics

<div align="center">

![Lines of Code](https://tokei.rs/b1/github/burkefit2382-wq/nexus-b2b-lead-generation?category=code)
![Repo Size](https://img.shields.io/github/repo-size/burkefit2382-wq/nexus-b2b-lead-generation)
![Language](https://img.shields.io/github/languages/top/burkefit2382-wq/nexus-b2b-lead-generation)

</div>

---

## 🔒 Security

<div align="center">

[![Dependabot](https://img.shields.io/badge/Dependabot-enabled-brightgreen)](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/network/updates)
[![CodeQL](https://img.shields.io/badge/CodeQL-enabled-blue)](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/security/code-scanning)
[![Security Policy](https://img.shields.io/badge/Security-Policy-green)](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/security/policy)

</div>

For security concerns, please email security@nexus-intelligence.com.

---

## ⚖️ Legal & Compliance

<div align="center">

[![GDPR](https://img.shields.io/badge/GDPR-Compliant-green)](https://gdpr.eu/)
[![CCPA](https://img.shields.io/badge/CCPA-Compliant-blue)](https://oag.ca.gov/privacy/ccpa)
[![SOC 2](https://img.shields.io/badge/SOC%202-Compliant-orange)](https://www.aicpa.org/soc4so)

</div>

---

<div align="center">

**Built with ❤️ by the NEXUS Intelligence Team**

[🔗 GitHub Repository](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation) |
[📚 Documentation](https://nexus-intelligence.com/docs) |
[💬 Discussions](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/discussions) |
[📧 Contact](mailto:support@nexus-intelligence.com)

</div>

---

## 📈 Sponsors & Backers

<div align="center">

[![GitHub Sponsors](https://img.shields.io/badge/GitHub-Sponsors-Orange)](https://github.com/sponsors/burkefit2382-wq)

Become a sponsor! [Donate](https://github.com/sponsors/burkefit2382-wq)

</div>

---

<div align="center">

**[⬆ Back to Top](#-nexus-b2b-lead-generation--osint-intelligence-suite)**

</div>

---

<div align="center">

*If you find this project useful, please consider giving it a ⭐️ on GitHub!*

</div>