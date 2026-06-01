from app.services.search import parse_value_threshold


def test_parse_value_threshold_handles_minimum_mil_language():
    assert parse_value_threshold("public bids above minimum $5mil range") == 5_000_000
    assert parse_value_threshold("data center power at least $10M") == 10_000_000
