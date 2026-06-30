# Contributing

## Development Flow

1. Create a branch from `main`.
2. Keep changes focused and small.
3. Run local quality checks.
4. Open a pull request using the template.

## Checks

```powershell
python -m py_compile server.py main.py
python -m pytest
```

## Code Standards

- Keep secrets out of frontend code.
- Keep checkout catalog changes synchronized between UI and `STRIPE_CATALOG`.
- Prefer safe, explicit API errors over leaking stack traces.
- Do not add scraping behavior that bypasses access controls, logins, or rate limits.

