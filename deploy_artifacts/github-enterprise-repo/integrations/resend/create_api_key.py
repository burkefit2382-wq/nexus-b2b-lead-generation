"""
Create a named Resend API key from a trusted backend environment.

Do not put your Resend API key in frontend JavaScript or commit it to git.
Set RESEND_API_KEY in your shell or hosting provider first.
"""

from __future__ import annotations

import os
import sys

import resend


def main() -> int:
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print("Missing RESEND_API_KEY environment variable.", file=sys.stderr)
        return 1

    key_name = os.environ.get("RESEND_NEW_KEY_NAME", "Production")
    resend.api_key = api_key

    params: resend.ApiKeys.CreateParams = {
        "name": key_name,
    }

    created = resend.ApiKeys.create(params)
    print(created)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

