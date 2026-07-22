"""Render compatibility entrypoint.

The Render service root is already the ``backend`` directory, but an older
dashboard start command imports ``backend.app.main:app``. This shim keeps that
command working while the real FastAPI app lives at ``app.main``.
"""

from app.main import app

__all__ = ["app"]

