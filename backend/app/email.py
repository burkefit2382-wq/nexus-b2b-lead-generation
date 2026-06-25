import os
import resend

from .models import Lead

SENDER = "NEXUS Intelligence <noreply@mail.nexus.sh>"


def _build_html(query: str, leads: list[Lead]) -> str:
    rows = "".join(
        f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #334155">{lead.contact_name}</td>
          <td style="padding:8px;border-bottom:1px solid #334155">{lead.email or '—'}</td>
          <td style="padding:8px;border-bottom:1px solid #334155">{lead.industry or '—'}</td>
          <td style="padding:8px;border-bottom:1px solid #334155">{lead.location or '—'}</td>
          <td style="padding:8px;border-bottom:1px solid #334155;text-align:center;
              color:{'#22c55e' if lead.score >= 80 else '#f59e0b' if lead.score >= 60 else '#ef4444'};
              font-weight:bold">{lead.score}</td>
        </tr>"""
        for lead in leads
    )
    return f"""
    <div style="font-family:sans-serif;background:#0f172a;color:#e2e8f0;padding:32px">
      <h1 style="color:#38bdf8">⚡ NEXUS Lead Digest</h1>
      <p>Found <strong>{len(leads)}</strong> leads for <em>{query}</em></p>
      <table style="width:100%;border-collapse:collapse;margin-top:16px">
        <thead>
          <tr style="background:#1e293b;color:#94a3b8;font-size:0.8rem;text-transform:uppercase">
            <th style="padding:8px;text-align:left">Contact</th>
            <th style="padding:8px;text-align:left">Email</th>
            <th style="padding:8px;text-align:left">Industry</th>
            <th style="padding:8px;text-align:left">Location</th>
            <th style="padding:8px;text-align:center">Score</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      <p style="margin-top:24px;color:#94a3b8;font-size:0.8rem">
        Sent by NEXUS Intelligence Platform · mail.nexus.sh
      </p>
    </div>"""


def send_lead_digest(to: str, query: str, leads: list[Lead]) -> str:
    """
    Send a lead digest email via Resend and return the message ID.

    Requires the RESEND_API_KEY environment variable to be set.
    """
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY environment variable is not set")

    resend.api_key = api_key

    params: resend.Emails.SendParams = {
        "from": SENDER,
        "to": [to],
        "subject": f"NEXUS Lead Digest — {query} ({len(leads)} leads)",
        "html": _build_html(query, leads),
    }
    response = resend.Emails.send(params)
    return response["id"]
