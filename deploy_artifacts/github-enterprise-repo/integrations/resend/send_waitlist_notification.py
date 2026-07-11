"""
Send a waitlist notification email through Resend.

This is a backend-side utility. The static landing page should submit to a
serverless function or backend route that calls this logic.
"""

from __future__ import annotations

import os
import sys
from html import escape

import resend


def send_waitlist_notification(email: str, company: str = "", source: str = "launch_site") -> object:
    api_key = os.environ.get("RESEND_API_KEY")
    sender = os.environ.get("RESEND_FROM")
    notify_to = os.environ.get("WAITLIST_NOTIFY_TO") or os.environ.get("RESEND_TO")

    missing = [
        name
        for name, value in {
            "RESEND_API_KEY": api_key,
            "RESEND_FROM": sender,
            "WAITLIST_NOTIFY_TO or RESEND_TO": notify_to,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing required environment variable(s): {', '.join(missing)}")

    resend.api_key = api_key

    safe_email = escape(email)
    safe_company = escape(company or "Not provided")
    safe_source = escape(source)

    params: resend.Emails.SendParams = {
        "from": sender,
        "to": [notify_to],
        "subject": "New LeadGen Virtual Hub pilot request",
        "html": f"""
            <h1>New pilot request</h1>
            <p><strong>Email:</strong> {safe_email}</p>
            <p><strong>Company:</strong> {safe_company}</p>
            <p><strong>Source:</strong> {safe_source}</p>
        """,
        "text": f"New pilot request\nEmail: {email}\nCompany: {company or 'Not provided'}\nSource: {source}",
    }

    return resend.Emails.send(params)


def main() -> int:
    email = os.environ.get("WAITLIST_EMAIL")
    company = os.environ.get("WAITLIST_COMPANY", "")
    source = os.environ.get("WAITLIST_SOURCE", "manual-test")

    if not email:
        print("Missing WAITLIST_EMAIL environment variable.", file=sys.stderr)
        return 1

    result = send_waitlist_notification(email=email, company=company, source=source)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

