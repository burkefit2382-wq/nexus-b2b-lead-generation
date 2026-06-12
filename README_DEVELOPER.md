# NEXUS Developer Documentation

> **Complete technical guide for developers integrating with and extending NEXUS**

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture](#architecture)
3. [API Reference](#api-reference)
4. [Database Schema](#database-schema)
5. [Extending NEXUS](#extending-nexus)
6. [Testing](#testing)
7. [Deployment](#deployment)
8. [Troubleshooting](#troubleshooting)
9. [Contributing](#contributing)

---

## Quick Start

### Prerequisites

```bash
# Check Python version
python --version  # Must be 3.11+

# Check Node.js
node --version    # Must be 18+

# Check Git
git --version
```

### Installation

```bash
# Clone repository
git clone https://github.com/burkefit2382-wq/nexus-b2b-lead-generation.git
cd nexus-b2b-lead-generation

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

### Run Development Server

```bash
# With auto-reload
uvicorn nexus.api.server:app --reload --host 0.0.0.0 --port 8000

# With multiple workers
uvicorn nexus.api.server:app --workers 4 --host 0.0.0.0 --port 8000

# With SSL
uvicorn nexus.api.server:app --ssl-keyfile key.pem --ssl-certfile cert.pem --host 0.0.0.0 --port 8443
```

---

## Architecture

### System Overview

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

### Module Structure

```
nexus/
├── api/                  # FastAPI application
│   ├── server.py         # Main application
│   ├── routes_leads.py   # Lead CRUD endpoints
│   ├── routes_osint.py   # OSINT endpoints
│   └── routes_ai.py      # AI endpoints
├── scraping/             # Scraping modules
│   ├── playwright_scraper.py
│   ├── google_maps_scraper.py
│   ├── linkedin_scraper.py
│   └── tor_router.py
├── osint/                # OSINT modules
│   ├── email_lookup.py
│   ├── phone_lookup.py
│   ├── domain_intel.py
│   └── breach_check.py
├── ai/                   # AI modules
│   ├── llama_engine.py
│   ├── embeddings.py
│   └── summarizer.py
├── database/             # Database layer
│   ├── models.py
│   ├── schema.sql
│   └── repository.py
├── utils/                # Utilities
│   ├── logger.py
│   ├── helpers.py
│   └── validators.py
├── dashboard/            # Web interface
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── config.py             # Configuration
└── main.py              # Entry point
```

---

## API Reference

### Base URL

```
Development: http://localhost:8000
Production: https://api.nexus-intelligence.com
```

### Authentication

```python
# API Key authentication (future feature)
headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json"
}
```

### Response Format

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Lead Endpoints

#### Create Lead

```http
POST /api/leads/
Content-Type: application/json

{
  "company_name": "Acme Corp",
  "website": "https://acme.com",
  "email": "contact@acme.com",
  "phone": "+1-555-123-4567",
  "address": "123 Main St, New York, NY 10001",
  "industry": "Technology",
  "employee_count": "100-500",
  "revenue": "$10M-$50M",
  "source": "google_maps"
}
```

#### Get Leads (Paginated)

```http
GET /api/leads/?skip=0&limit=100&min_quality=70
```

#### Get Lead by ID

```http
GET /api/leads/1
```

#### Update Lead

```http
PUT /api/leads/1
Content-Type: application/json

{
  "company_name": "Acme Corporation",
  "quality_score": 85.5
}
```

#### Delete Lead

```http
DELETE /api/leads/1
```

### OSINT Endpoints

#### Verify Email

```http
POST /api/osint/email/verify
Content-Type: application/json

{
  "email": "contact@acme.com"
}

Response:
{
  "email": "contact@acme.com",
  "valid": true,
  "disposable": false,
  "deliverable": true,
  "source": "email_lookup"
}
```

#### Check Email Breaches

```http
POST /api/osint/email/breaches
Content-Type: application/json

{
  "email": "contact@acme.com"
}

Response:
{
  "email": "contact@acme.com",
  "breached": false,
  "breaches_count": 0,
  "breaches": [],
  "source": "haveibeenpwned"
}
```

#### Get WHOIS Information

```http
POST /api/osint/domain/whois
Content-Type: application/json

{
  "domain": "acme.com"
}

Response:
{
  "domain": "acme.com",
  "registered": true,
  "registrar": "GoDaddy.com, LLC",
  "created_date": "2010-01-01",
  "expiration_date": "2025-01-01",
  "name_servers": ["ns1.acme.com", "ns2.acme.com"],
  "source": "whois"
}
```

### AI Endpoints

#### Generate Text

```http
POST /api/ai/generate
Content-Type: application/json

{
  "prompt": "Write a sales email for a SaaS company",
  "max_tokens": 512
}

Response:
{
  "text": "Generated text here...",
  "source": "llama_engine"
}
```

#### Analyze Lead

```http
POST /api/ai/analyze
Content-Type: application/json

{
  "company_name": "Acme Corp",
  "industry": "Technology",
  "website": "https://acme.com"
}

Response:
{
  "analysis": "Acme Corp appears to be a technology company...",
  "insights": ["Insight 1", "Insight 2"],
  "score": 85.0,
  "source": "llama_engine"
}
```

#### Calculate Lead Score

```http
POST /api/ai/score
Content-Type: application/json

{
  "lead_data": { ... },
  "osint_data": { ... }
}

Response:
{
  "quality_score": 82.5,
  "source": "summarizer"
}
```

---

## Database Schema

### Tables

#### `leads`

```sql
CREATE TABLE leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name VARCHAR(255) NOT NULL,
    website VARCHAR(512),
    phone VARCHAR(50),
    email VARCHAR(255),
    address VARCHAR(512),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100) DEFAULT 'US',
    industry VARCHAR(100),
    employee_count VARCHAR(50),
    revenue VARCHAR(50),
    rating FLOAT,
    reviews_count INTEGER,
    description TEXT,
    source VARCHAR(100),
    quality_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Indexes
CREATE INDEX idx_leads_company ON leads(company_name);
CREATE INDEX idx_leads_quality ON leads(quality_score);
CREATE INDEX idx_leads_source ON leads(source);
```

#### `osint_data`

```sql
CREATE TABLE osint_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    data_type VARCHAR(50) NOT NULL,
    result_json TEXT NOT NULL,
    confidence FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);

-- Indexes
CREATE INDEX idx_osint_lead ON osint_data(lead_id);
CREATE INDEX idx_osint_type ON osint_data(data_type);
```

#### `ai_summaries`

```sql
CREATE TABLE ai_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    summary TEXT,
    insights_json TEXT,
    score FLOAT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);

-- Indexes
CREATE INDEX idx_ai_lead ON ai_summaries(lead_id);
```

#### `scrape_tasks`

```sql
CREATE TABLE scrape_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type VARCHAR(50) NOT NULL,
    query VARCHAR(512),
    status VARCHAR(50) DEFAULT 'pending',
    results_count INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Indexes
CREATE INDEX idx_tasks_status ON scrape_tasks(status);
```

### Relationships

```
leads (1) ----< (N) osint_data
leads (1) ----< (N) ai_summaries
```

---

## Extending NEXUS

### Adding a New Scraper

1. Create new scraper module in `nexus/scraping/`

```python
# nexus/scraping/custom_scraper.py
from nexus.scraping.playwright_scraper import PlaywrightScraper
from nexus.utils.logger import logger

class CustomScraper:
    """Custom scraper implementation"""

    def __init__(self):
        self.base_scraper = PlaywrightScraper()

    async def scrape_custom_data(self, url: str) -> dict:
        """Scrape custom data from URL"""
        try:
            html = await self.base_scraper.scrape_page(url)
            # Extract data
            return {"data": "extracted_data"}
        except Exception as e:
            logger.error(f"Custom scrape failed: {e}")
            return {}
```

2. Add API endpoint in `nexus/api/routes_scraping.py`

```python
from fastapi import APIRouter
from nexus.scraping.custom_scraper import CustomScraper

router = APIRouter(prefix="/scraping", tags=["Scraping"])

@router.post("/custom")
async def scrape_custom(url: str):
    """Scrape custom data"""
    scraper = CustomScraper()
    result = await scraper.scrape_custom_data(url)
    return result
```

3. Register router in `nexus/api/server.py`

```python
from nexus.api import routes_scraping

app.include_router(routes_scraping.router, prefix="/api/scraping", tags=["Scraping"])
```

### Adding a New OSINT Module

1. Create new OSINT module in `nexus/osint/`

```python
# nexus/osint/custom_lookup.py
from nexus.utils.logger import logger

class CustomLookup:
    """Custom OSINT lookup"""

    async def lookup(self, identifier: str) -> dict:
        """Perform custom lookup"""
        try:
            # Implement lookup logic
            return {"result": "data"}
        except Exception as e:
            logger.error(f"Custom lookup failed: {e}")
            return {}
```

2. Add API endpoint in `nexus/api/routes_osint.py`

```python
from nexus.osint.custom_lookup import CustomLookup

@router.post("/custom/lookup")
async def custom_lookup(identifier: str):
    """Perform custom OSINT lookup"""
    lookup = CustomLookup()
    result = await lookup.lookup(identifier)
    return result
```

### Adding Custom AI Analysis

1. Extend AI modules in `nexus/ai/`

```python
# nexus/ai/custom_analyzer.py
from nexus.ai.llama_engine import LlamaEngine

class CustomAnalyzer:
    """Custom AI analyzer"""

    def __init__(self, llm: LlamaEngine):
        self.llm = llm

    def analyze_custom(self, data: dict) -> dict:
        """Perform custom analysis"""
        prompt = f"""
        Analyze this data:
        {data}

        Provide:
        1. Key findings
        2. Recommendations
        """

        response = self.llm.generate_text(prompt)
        return {"analysis": response}
```

2. Add API endpoint in `nexus/api/routes_ai.py`

```python
from nexus.ai.custom_analyzer import CustomAnalyzer

@router.post("/custom/analyze")
async def custom_analyze(data: dict):
    """Perform custom AI analysis"""
    analyzer = CustomAnalyzer(llama_engine)
    result = analyzer.analyze_custom(data)
    return result
```

---

## Testing

### Unit Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=nexus --cov-report=html

# Run specific test file
pytest tests/test_api.py -v

# Run specific test
pytest tests/test_api.py::test_create_lead -v
```

### Integration Tests

```bash
# Run integration tests
pytest tests/integration/

# Run with test database
pytest tests/ --env test
```

### Test Coverage

```bash
# Generate coverage report
pytest tests/ --cov=nexus --cov-report=html --cov-report=term

# Open coverage report
open htmlcov/index.html  # Mac
start htmlcov/index.html  # Windows
```

### Writing Tests

```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from nexus.api.server import app

client = TestClient(app)

def test_create_lead():
    """Test lead creation"""
    response = client.post(
        "/api/leads/",
        json={
            "company_name": "Test Company",
            "website": "https://test.com",
            "email": "test@test.com"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["company_name"] == "Test Company"

def test_get_leads():
    """Test lead retrieval"""
    response = client.get("/api/leads/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

---

## Deployment

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "nexus.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build image
docker build -t nexus-intelligence .

# Run container
docker run -p 8000:8000 nexus-intelligence
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  nexus-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/nexus
    depends_on:
      - db
    volumes:
      - ./logs:/app/logs

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=nexus
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f nexus-api

# Stop services
docker-compose down
```

### Kubernetes Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nexus-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nexus-api
  template:
    metadata:
      labels:
        app: nexus-api
    spec:
      containers:
      - name: nexus-api
        image: nexus-intelligence:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: nexus-secrets
              key: database-url

---
apiVersion: v1
kind: Service
metadata:
  name: nexus-api
spec:
  selector:
    app: nexus-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

```bash
# Deploy to Kubernetes
kubectl apply -f k8s/

# Check deployment
kubectl get pods -l app=nexus-api

# View logs
kubectl logs -l app=nexus-api -f
```

---

## Troubleshooting

### Common Issues

#### LLaMA Model Not Loading

**Error**: `OSError: [WinError 0xc000001d]`

**Solution**:
```bash
# Reinstall with CPU-compatible wheel
pip uninstall llama-cpp-python -y
pip install llama-cpp-python --force-reinstall --no-cache-dir \
  --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```

#### Database Connection Failed

**Error**: `sqlalchemy.exc.OperationalError: unable to open database file`

**Solution**:
```bash
# Ensure database directory exists
mkdir -p logs

# Check DATABASE_URL in .env
DATABASE_URL=sqlite:///nexus.db
```

#### Playwright Browser Not Found

**Error**: `Executable doesn't exist at ...chromium`

**Solution**:
```bash
# Install Playwright browsers
playwright install

# Install specific browser
playwright install chromium
```

#### Port Already in Use

**Error**: `OSError: [Errno 48] Address already in use`

**Solution**:
```bash
# Find process using port 8000
netstat -ano | findstr :8000  # Windows
lsof -i :8000  # Linux/Mac

# Kill process
taskkill /PID <PID> /F  # Windows
kill -9 <PID>  # Linux/Mac

# Or use different port
uvicorn nexus.api.server:app --port 8001
```

---

## Contributing

### Development Workflow

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/nexus-b2b-lead-generation.git
   cd nexus-b2b-lead-generation
   ```

2. **Create Feature Branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **Make Changes**
   - Write code
   - Add tests
   - Update documentation

4. **Run Tests**
   ```bash
   pytest tests/ --cov=nexus
   ```

5. **Commit Changes**
   ```bash
   git add .
   git commit -m "Add amazing feature"
   ```

6. **Push to Fork**
   ```bash
   git push origin feature/amazing-feature
   ```

7. **Create Pull Request**
   - Go to https://github.com/burkefit2382-wq/nexus-b2b-lead-generation
   - Click "Compare & pull request"
   - Describe your changes
   - Submit

### Code Style

- Follow PEP 8
- Use type hints
- Add docstrings to functions
- Keep functions under 50 lines
- Write unit tests for new features

### Pull Request Checklist

- [ ] Code follows project style
- [ ] Tests pass locally
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] No merge conflicts

---

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Playwright Documentation](https://playwright.dev/)
- [LLaMA.cpp Documentation](https://github.com/abetlen/llama-cpp-python)

---

**Need help?**
- [GitHub Issues](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/issues)
- [GitHub Discussions](https://github.com/burkefit2382-wq/nexus-b2b-lead-generation/discussions)
- [Email: dev@nexus-intelligence.com](mailto:dev@nexus-intelligence.com)