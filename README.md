# NEXUS B2B Lead Generation

> Advanced AI-powered B2B lead generation platform combining real-time data acquisition, AI-driven reasoning, and structured OSINT reporting.

## 📋 Overview

At its core, NEXUS combines real-time data acquisition, AI-driven reasoning, and structured reporting to produce actionable insights for businesses, investigators, and digital operations. The platform integrates a FastAPI backend, a responsive dashboard, and a CPU-optimized LLaMA inference server, and 19 different OSINT tools.

### Key Features
- 🔍 **Real-time Data Acquisition** - Gather intelligence from multiple sources
- 🤖 **AI-Driven Reasoning** - LLaMA-based inference for intelligent analysis
- 📊 **Structured Reporting** - Generate actionable insights with formatted reports
- ⚡ **FastAPI Backend** - High-performance REST API
- 🎨 **Responsive Dashboard** - Interactive web interface for data visualization
- 🔐 **OSINT Integration** - 19 integrated OSINT tools for comprehensive intelligence

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      NEXUS Platform                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Dashboard    │  │  FastAPI     │  │  LLaMA       │    │
│  │   (Frontend)   │  │  Backend     │  │  Inference   │    │
│  └────────────────┘  └──────────────┘  └──────────────┘    │
│         │                   │                  │             │
│         └───────────────────┼──────────────────┘             │
│                             │                                │
│         ┌───────────────────▼────────────────┐               │
│         │   Data Processing & Analysis      │               │
│         └────────────────┬────────────────────┘              │
│                          │                                   │
│  ┌──────────────────────▼──────────────────────┐             │
│  │         OSINT Tool Integration (19)         │             │
│  │  • Web Scraping  • IP Lookup  • Domain     │             │
│  │  • Email Search  • Social Media • etc.     │             │
│  └──────────────────────────────────────────────┘            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+ (for dashboard)
- Docker & Docker Compose (optional)
- 8GB+ RAM (for LLaMA inference)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/burkefit2382-wq/nexus-b2b-lead-generation.git
cd nexus-b2b-lead-generation
```

2. **Set up backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Set up frontend**
```bash
cd frontend
npm install
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Run the application**
```bash
# Terminal 1: Backend
cd backend
python -m uvicorn main:app --reload

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: LLaMA Inference Server
python inference/llama_server.py
```

The platform will be available at `http://localhost:3000`

---

## 📖 Usage

### API Endpoints

#### Lead Generation
```bash
POST /api/leads/generate
{
  "company_name": "Acme Corp",
  "industry": "Technology",
  "country": "USA",
  "limit": 50
}
```

#### OSINT Lookup
```bash
POST /api/osint/lookup
{
  "target": "example@company.com",
  "tools": ["email_search", "domain_lookup", "ip_analysis"]
}
```

#### AI Analysis
```bash
POST /api/analysis/generate
{
  "data": "...",
  "analysis_type": "lead_scoring",
  "output_format": "json"
}
```

### Dashboard Features
- Real-time lead tracking
- OSINT result visualization
- AI-powered insights and recommendations
- Export reports (PDF, CSV, JSON)
- Search and filter capabilities

---

## 🔧 Configuration

Create a `.env` file in the root directory:

```env
# Backend
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
DEBUG=True

# Frontend
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000

# LLaMA Inference
LLAMA_MODEL_PATH=./models/llama-7b
LLAMA_GPU_ENABLED=True
LLAMA_MAX_TOKENS=512

# OSINT Tools
OSINT_TIMEOUT=30
OSINT_MAX_WORKERS=5

# Database
DATABASE_URL=sqlite:///./nexus.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/nexus.log
```

---

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_osint.py

# Run with verbose output
pytest -v
```

---

## 📁 Project Structure

```
nexus-b2b-lead-generation/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── leads.py
│   │   │   ├── osint.py
│   │   │   └── analysis.py
│   │   ├── models/
│   │   ├── services/
│   │   └── utils/
│   ├── inference/
│   │   └── llama_server.py
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── osint_tools/
│   ├── email_search.py
│   ├── domain_lookup.py
│   ├── ip_analysis.py
│   └── __init__.py
├── docker-compose.yml
├── Dockerfile
└── README.md
```

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the Apache License 2.0 - see [LICENSE](LICENSE) file for details.

---

## 🐛 Bug Reports & Feature Requests

- **Bug Reports**: [Create an Issue](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/issues/new?template=bug_report.md)
- **Feature Requests**: [Create an Issue](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/issues/new?template=feature_request.md)

---

## 📞 Support

- **Documentation**: [Wiki](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/wiki)
- **Discussions**: [Discussions](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/discussions)
- **Email**: burkefit2382@gmail.com

---

## 🎯 Roadmap

- [ ] Web scraping improvements
- [ ] Advanced ML models for lead scoring
- [ ] Multi-language support
- [ ] API rate limiting and auth
- [ ] Kubernetes deployment templates
- [ ] Webhook integrations

---

## 📊 Stats

![GitHub stars](https://img.shields.io/github/stars/burkefit2382-wq/nexus-b2b-lead-generation?style=flat)
![GitHub forks](https://img.shields.io/github/forks/burkefit2382-wq/nexus-b2b-lead-generation?style=flat)
![License](https://img.shields.io/github/license/burkefit2382-wq/nexus-b2b-lead-generation?style=flat)

---

**Made with ❤️ by [burkefit2382-wq](https://github.com/burkefit2382-wq)**
