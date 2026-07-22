import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from server import LaunchHandler, STRIPE_CATALOG  # noqa: E402


def test_catalog_price_data_for_one_time_payment() -> None:
    handler = object.__new__(LaunchHandler)
    price_data = handler.catalog_price_data(
        "price_tb_leads_10_350",
        STRIPE_CATALOG["price_tb_leads_10_350"],
    )
    assert price_data["unit_amount"] == 35000
    assert "recurring" not in price_data
    assert price_data["product_data"]["metadata"]["nexus_price_id"] == "price_tb_leads_10_350"


def test_catalog_price_data_for_monthly_subscription() -> None:
    handler = object.__new__(LaunchHandler)
    price_data = handler.catalog_price_data(
        "price_dfy_997",
        STRIPE_CATALOG["price_dfy_997"],
    )
    assert price_data["unit_amount"] == 99700
    assert price_data["recurring"] == {"interval": "month"}
