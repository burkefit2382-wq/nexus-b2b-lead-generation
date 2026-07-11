# Resend Integration

This folder contains backend-side utilities for Resend email.

Do not expose `RESEND_API_KEY` in `launch_site/app.js`, HTML, or any browser bundle. The static launch site should submit waitlist requests to a backend route or serverless function, and that backend should call Resend.

Official docs:

- Resend Python SDK: https://resend.com/docs/send-with-python
- Resend API keys: https://resend.com/docs/dashboard/api-keys/introduction
- Resend domains: https://resend.com/docs/dashboard/domains/introduction

## Install

```powershell
python -m pip install -r integrations/resend/requirements.txt
```

## Set Environment Variables

PowerShell example:

```powershell
$env:RESEND_API_KEY = "re_xxxxxxxxx"
$env:RESEND_FROM = "LeadGen Virtual Hub <pilot@yourdomain.com>"
$env:WAITLIST_NOTIFY_TO = "you@yourdomain.com"
```

Use a verified Resend domain for production sending.

## Create A Named API Key

Your snippet is represented safely in `create_api_key.py`. It reads the existing key from the environment and creates a named key.

```powershell
$env:RESEND_API_KEY = "re_xxxxxxxxx"
$env:RESEND_NEW_KEY_NAME = "Production"
python integrations/resend/create_api_key.py
```

## Send A Test Waitlist Notification

```powershell
$env:RESEND_API_KEY = "re_xxxxxxxxx"
$env:RESEND_FROM = "LeadGen Virtual Hub <pilot@yourdomain.com>"
$env:WAITLIST_NOTIFY_TO = "you@yourdomain.com"
$env:WAITLIST_EMAIL = "tester@example.com"
$env:WAITLIST_COMPANY = "Example Co"
python integrations/resend/send_waitlist_notification.py
```

## Public Launch Requirement

Before public deployment, keep the `launch_site/app.js` waitlist form pointed at a backend endpoint such as:

```text
POST /api/waitlist
```

That endpoint should:

- Validate email input.
- Rate limit requests.
- Store the lead in your CRM/database/storefront workflow.
- Send an internal notification through Resend.
- Return a safe success/failure message.
