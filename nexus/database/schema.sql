-- NEXUS Database Schema

-- Leads table
CREATE TABLE IF NOT EXISTS leads (
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

-- OSINT data table
CREATE TABLE IF NOT EXISTS osint_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    data_type VARCHAR(50) NOT NULL,
    result_json TEXT NOT NULL,
    confidence FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);

-- AI summaries table
CREATE TABLE IF NOT EXISTS ai_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    summary TEXT,
    insights_json TEXT,
    score FLOAT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);

-- Scrape tasks table
CREATE TABLE IF NOT EXISTS scrape_tasks (
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
CREATE INDEX IF NOT EXISTS idx_leads_company ON leads(company_name);
CREATE INDEX IF NOT EXISTS idx_leads_quality ON leads(quality_score);
CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source);
CREATE INDEX IF NOT EXISTS idx_osint_lead ON osint_data(lead_id);
CREATE INDEX IF NOT EXISTS idx_osint_type ON osint_data(data_type);
CREATE INDEX IF NOT EXISTS idx_ai_lead ON ai_summaries(lead_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON scrape_tasks(status);