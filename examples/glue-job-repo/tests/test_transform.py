import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jobs" / "orders_etl"))

from script import transform  # noqa: E402


def test_transform_drops_rows_without_order_id():
    assert transform([{"status": "NEW"}]) == []


def test_transform_normalizes_status():
    assert transform([{"order_id": "1", "status": "PAID"}]) == [
        {"order_id": "1", "status": "paid"}
    ]


def test_transform_defaults_missing_status():
    assert transform([{"order_id": "1"}]) == [{"order_id": "1", "status": "unknown"}]
