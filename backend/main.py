import os

import uvicorn

from app.main import app

__all__ = ["app"]


if __name__ == "__main__":
    host = os.environ.get("LAUNCH_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT") or os.environ.get("LAUNCH_PORT") or "10000")
    uvicorn.run(app, host=host, port=port)
