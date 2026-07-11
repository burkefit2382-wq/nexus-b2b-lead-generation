# Enterprise Validation Suite

The enterprise validation workflow runs `backend/scripts/enterprise_validation_suite.py` against the in-process FastAPI app.

## What it checks

- Load/performance success rate and latency for `/health` and `/api/health`
- Basic security assertions (input rejection and secret redaction)
- Availability probe stability

## Local usage

```bash
python backend/scripts/enterprise_validation_suite.py
```

Optional tuning:

```bash
python backend/scripts/enterprise_validation_suite.py --requests 100 --concurrency 10 --output-md /tmp/enterprise.md --output-json /tmp/enterprise.json
```

## CI

`.github/workflows/enterprise-validation.yml` runs the suite on pushes and pull requests targeting `main`, plus manual dispatch.
