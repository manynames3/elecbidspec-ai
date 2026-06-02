from datetime import datetime, timedelta, timezone

from app.api.routes import _source_health
from app.models import IngestionJob


def _status_for(source: str, source_rows: list, latest_jobs: list[IngestionJob]) -> str:
    health = _source_health(source_rows, latest_jobs)
    return next(item["status"] for item in health if item["source"] == source)


def test_recent_complete_job_keeps_source_healthy_when_records_are_old():
    old_record_time = datetime.now(timezone.utc) - timedelta(days=3)
    recent_job = IngestionJob(
        adapter="txdot_bid_items",
        params={"source": "txdot_bid_items"},
        status="complete",
    )
    recent_job.updated_at = datetime.now(timezone.utc)

    status = _status_for(
        "txdot_bid_items",
        [("txdot_bid_items", "state_dot", 12, 3, old_record_time)],
        [recent_job],
    )

    assert status == "healthy"


def test_old_records_without_recent_complete_job_are_stale():
    old_record_time = datetime.now(timezone.utc) - timedelta(days=3)

    status = _status_for(
        "txdot_bid_items",
        [("txdot_bid_items", "state_dot", 12, 3, old_record_time)],
        [],
    )

    assert status == "stale"
