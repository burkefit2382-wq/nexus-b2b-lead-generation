CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS visitors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id TEXT,
  first_seen_at TIMESTAMP DEFAULT NOW(),
  last_seen_at TIMESTAMP DEFAULT NOW(),
  first_page_url TEXT,
  referrer TEXT,
  utm_source TEXT,
  utm_medium TEXT,
  utm_campaign TEXT,
  utm_content TEXT,
  utm_term TEXT,
  gclid TEXT,
  msclkid TEXT,
  fbclid TEXT
);

CREATE INDEX IF NOT EXISTS visitors_client_id_idx ON visitors(client_id);
CREATE INDEX IF NOT EXISTS visitors_last_seen_at_idx ON visitors(last_seen_at);

CREATE TABLE IF NOT EXISTS leads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  visitor_id UUID REFERENCES visitors(id),
  name TEXT,
  email TEXT,
  phone TEXT,
  service_type TEXT,
  city TEXT,
  state TEXT,
  status TEXT DEFAULT 'new',
  lead_score INTEGER DEFAULT 0,
  estimated_value NUMERIC,
  source TEXT,
  landing_page TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS leads_visitor_id_idx ON leads(visitor_id);
CREATE INDEX IF NOT EXISTS leads_created_at_idx ON leads(created_at);
CREATE INDEX IF NOT EXISTS leads_status_idx ON leads(status);

CREATE TABLE IF NOT EXISTS events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  visitor_id UUID REFERENCES visitors(id),
  lead_id UUID REFERENCES leads(id),
  event_name TEXT NOT NULL,
  page_url TEXT,
  event_data JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS events_visitor_id_idx ON events(visitor_id);
CREATE INDEX IF NOT EXISTS events_lead_id_idx ON events(lead_id);
CREATE INDEX IF NOT EXISTS events_event_name_idx ON events(event_name);
CREATE INDEX IF NOT EXISTS events_created_at_idx ON events(created_at);

CREATE TABLE IF NOT EXISTS weekly_summaries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  week_start DATE,
  week_end DATE,
  total_visitors INTEGER,
  total_leads INTEGER,
  qualified_leads INTEGER,
  conversion_rate NUMERIC,
  best_source TEXT,
  best_campaign TEXT,
  best_landing_page TEXT,
  action_items JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
