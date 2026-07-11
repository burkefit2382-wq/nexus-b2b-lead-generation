# Lead Benchmarking

`backend/scripts/benchmark_leads.py` compares sampled Apollo and Nexus lead datasets using simple completeness/quality heuristics.

## Supported inputs

- CSV
- JSON (array of leads or `{ "leads": [...] }`)

## Example

```bash
python backend/scripts/benchmark_leads.py --apollo data/apollo.csv --nexus data/nexus.json
```

The script writes a markdown summary to `backend/docs/lead-benchmark-report.md` by default.
