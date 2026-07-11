# Nexus Scraper Workers

## Tampa Bay Lead Worker

`tampa_bay_lead_worker.py` collects buyer-safe public business/location records from OpenStreetMap Overpass for:

- Pinellas
- Hillsborough
- Pasco
- Hernando

It targets real estate offices and adjacent real estate buyer categories such as mortgage, insurance, and home services. It does not bypass logins, scrape private profiles, or collect hidden/private personal data.

Run once:

```powershell
python workers\tampa_bay_lead_worker.py
```

Run continuously:

```powershell
python workers\tampa_bay_lead_worker.py --loop --interval-minutes 360
```

Outputs:

- `data/scrapers/tampa_bay_real_estate_leads.jsonl`
- `data/scrapers/tampa_bay_real_estate_leads.csv`
- `data/scrapers/latest_summary.json`
- `data/scrapers/worker.log`

