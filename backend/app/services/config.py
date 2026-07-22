import os
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[2]
TRACKING_ALLOWED_ORIGIN = os.environ.get("TRACKING_ALLOWED_ORIGIN", "*")
NEXUS_DATA_DIR = Path(os.environ.get("NEXUS_DATA_DIR", APP_ROOT / "data"))

R2_ACCESS_KEY = os.environ.get("R2_ACCESS_KEY", "").strip()
R2_SECRET_KEY = os.environ.get("R2_SECRET_KEY", "").strip()
R2_BUCKET = os.environ.get("R2_BUCKET", "").strip()
R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL", "").strip()

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
JWT_SECRET = os.environ.get("JWT_SECRET", "").strip()


def database_url() -> str:
    return os.environ.get("DATABASE_URL", "").strip()


def tracking_allowed_origins() -> list[str]:
    raw_value = os.environ.get("TRACKING_ALLOWED_ORIGIN", "*")
    origins = [origin.strip() for origin in raw_value.split(",") if origin.strip()]
    return origins or ["*"]


def r2_configured() -> bool:
    return bool(
        os.environ.get("R2_ACCESS_KEY", "").strip()
        and os.environ.get("R2_SECRET_KEY", "").strip()
        and os.environ.get("R2_BUCKET", "").strip()
    )


def resend_configured() -> bool:
    return bool(os.environ.get("RESEND_API_KEY", "").strip())


def jwt_configured() -> bool:
    return bool(os.environ.get("JWT_SECRET", "").strip())


DATABASE_URL = database_url()

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
STRIPE_API_VERSION = os.environ.get("STRIPE_API_VERSION", "2024-06-20").strip()
PRICE_ID = os.environ.get("PRICE_ID", "").strip()
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:4173").strip()


def stripe_secret_key() -> str:
    return os.environ.get("STRIPE_SECRET_KEY", "").strip()


def stripe_webhook_secret() -> str:
    return os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()


def price_id() -> str:
    return os.environ.get("PRICE_ID", "").strip()


def public_base_url() -> str:
    return os.environ.get("PUBLIC_BASE_URL", "http://localhost:4173").strip()


def stripe_configured() -> bool:
    return bool(stripe_secret_key() and stripe_webhook_secret() and price_id())
