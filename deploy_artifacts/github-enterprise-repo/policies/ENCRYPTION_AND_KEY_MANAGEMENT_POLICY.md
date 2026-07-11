# Encryption And Key Management Policy

Status: Draft  
Owner: Security owner and engineering owner  
Applies to: Application traffic, databases, object storage, backups, logs, queues, secrets, and integration credentials

## Purpose

Sensitive data must be protected in transit and at rest using managed, reviewable encryption controls.

## Requirements

- HTTPS/TLS must be enforced for customer-facing traffic.
- Secure cookies must be enabled for authenticated browser sessions.
- Database storage must be encrypted at rest.
- Object storage and uploaded files must be encrypted at rest.
- Backups must be encrypted.
- Secrets must be stored in a secret manager or equivalent protected configuration, not in source code.
- API keys must be hashed or otherwise protected where feasible.
- Key rotation procedures must exist for application secrets and integration credentials.
- Production and staging secrets must be separate.

## Launch Blockers

- Plain HTTP for authenticated traffic.
- Hardcoded production secrets.
- Unencrypted production databases or backups.
- Shared or unrotatable API keys.
- Production secrets reused in staging or local development.

## Required Evidence

- TLS scan.
- Storage encryption configuration.
- Backup encryption configuration.
- Secret scan report.
- Key/API token rotation procedure.
- Secure cookie/session configuration.

