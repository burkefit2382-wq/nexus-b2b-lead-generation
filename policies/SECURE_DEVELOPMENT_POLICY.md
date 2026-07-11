# Secure Development Policy

Status: Draft  
Owner: Engineering owner and security owner  
Applies to: Product code, infrastructure code, dependencies, release process, AI prompts/workflows, and integrations

## Purpose

Security checks must be part of normal development, not a one-time pre-launch scramble.

## Requirements

- Code changes must be reviewed before production release.
- Dependency vulnerability scans must run before launch and on a recurring schedule.
- Secret scans must run before launch and on a recurring schedule.
- Static analysis should run for supported languages.
- Security-sensitive changes require explicit review.
- Releases must include a rollback plan.
- Critical and high vulnerabilities must be fixed before launch unless formally risk-accepted.
- AI enrichment logic must be tested for unsafe data leakage, prompt exposure, and destructive output handling.
- OSINT integrations must be documented with source, allowed use, and rate-limit behavior.

## Launch Blockers

- No repeatable build/deploy process.
- No vulnerability scan evidence.
- Hardcoded secrets.
- No review for auth, RBAC, tenant isolation, billing, or data deletion changes.
- No rollback path.

## Required Evidence

- Build instructions.
- Release checklist.
- Dependency scan.
- Secret scan.
- SAST report if supported.
- Code review or change approval record.
- Rollback procedure.

