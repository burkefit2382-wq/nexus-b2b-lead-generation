# GitHub Enterprise Setup

Use this checklist after pushing the workspace to GitHub or GitHub Enterprise.

## Repository Settings

Enable:

- Require pull request before merging.
- Require approvals from CODEOWNERS.
- Require status checks:
  - `Launch site smoke tests`
  - `Nexus Devvit build`
  - `CodeQL JavaScript/TypeScript`
  - `Python dependency audit`
- Require deployment approval for the `production` environment.
- Require branches to be up to date before merge.
- Require conversation resolution before merge.
- Block force pushes.
- Block deletions.
- Enable secret scanning.
- Enable push protection.
- Enable Dependabot alerts and security updates.

## Required Secrets

Set these as GitHub Actions or hosting environment secrets only:

| Secret | Purpose |
| --- | --- |
| `RESEND_API_KEY` | Send waitlist notification emails |
| `RESEND_FROM` | Verified sender address |
| `WAITLIST_NOTIFY_TO` | Internal notification recipient |
| `LLAMA_CHAT_ENDPOINT` | Hosted Llama/Ollama-compatible chat endpoint |
| `LLAMA_CHAT_MODEL` | Model name, such as `llama3` |
| `STOREFRONT_API_KEY` | Future storefront sync |
| `RENDER_DEPLOY_HOOK` | Optional Render deploy hook |
| `RAILWAY_TOKEN` | Optional Railway deploy token |

## Environments

Create environments:

- `development`
- `staging`
- `production`

Require manual approval for production deployments.

## Release Artifacts

The `Package Deploy Artifacts` workflow creates:

- `leadgen-virtual-hub-launch-site.zip`
- `nexus-saas-devvit-build.zip`

The `Production Deploy` workflow validates the launch site and triggers
`RENDER_DEPLOY_HOOK` when that secret is configured.

## Public Launch Gates

Do not publicly launch until:

- Privacy policy and terms are reviewed.
- Resend domain is verified.
- Production waitlist storage is configured.
- Storefront buyer workflow is approved.
- Security findings are reviewed.
- Devvit public review status is confirmed.
- CODEOWNERS is updated if `@burkefit2382` is not the final GitHub owner.
