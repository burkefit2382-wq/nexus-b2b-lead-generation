# Contributing

## Development Rules

- Keep customer/private lead data out of commits.
- Keep secrets in environment variables or hosting secrets.
- Add evidence for launch/security changes in `trackers/TEST_EVIDENCE_LOG.md`.
- Update `DEPLOYMENT_STATUS.md` after deployment work.
- Run relevant checks before handoff.

## Checks

```powershell
python -m py_compile launch_site/server.py
cd nexus-saas
npm run type-check
npm run build
```

## Pull Request Expectations

- Explain user impact.
- List security/privacy impact.
- Include test evidence.
- Note deployment steps.
- Avoid unsupported compliance claims.

