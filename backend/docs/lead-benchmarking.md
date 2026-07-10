# Lead Benchmarking: Apollo vs Nexus (25 vs 25)

Use this workflow to benchmark 25 Apollo leads against 25 of your own leads.

## Input files

Provide Apollo JSON or CSV plus your CSV (any column order). The script auto-detects common aliases for:

- name
- company
- email
- phone
- title
- website
- linkedin

Example accepted header aliases include `full_name`, `company_name`, `email_address`, `phone_number`, `job_title`, and `linkedin_url`.

## Run benchmark

From repository root:

```powershell
python backend\scripts\benchmark_leads.py --apollo <path-to-apollo.csv> --nexus <path-to-your-leads.csv> --sample-size 25 --seed 42 --output-md backend\docs\lead-benchmark-report.md
```

## Output

The report is written to `backend/docs/lead-benchmark-report.md` and includes:

- per-source completeness metrics
- valid email rate
- duplicate/unique email counts
- unique email-domain count
- overlap counts between sources
- weighted quality score and winner

## Recommended process

1. Export Apollo leads to CSV, or use the Apollo JSON ingest payload directly.
2. Export your 25 leads to CSV.
3. Run the benchmark command above.
4. Commit/report the generated `backend/docs/lead-benchmark-report.md` if you want a saved audit artifact.

## Metric notes

- This is a data-quality benchmark, not conversion-performance benchmarking.
- Quality score weights are defined inside `backend/scripts/benchmark_leads.py` and can be tuned.


## Supported Apollo JSON

The script accepts a JSON object with a top-level `leads` array, like your `apollo_25_leads_ingest_payload.json`.
