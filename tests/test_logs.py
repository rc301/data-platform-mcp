from types import SimpleNamespace

from dataplatform.config import AwsClientError
from dataplatform.glue.logs import _extract, _ordered_streams, error_excerpt


def test_extract_returns_window_around_last_marker():
    lines = [f"line {i}" for i in range(30)] + ["Traceback (most recent call last)", "Boom"]
    excerpt, found = _extract(lines, max_lines=60)
    assert found is True
    assert "Traceback" in excerpt
    assert "Boom" in excerpt


def test_extract_falls_back_to_tail_without_markers():
    lines = [f"info {i}" for i in range(100)]
    excerpt, found = _extract(lines, max_lines=10)
    assert found is False
    assert excerpt.splitlines()[-1] == "info 99"
    assert len(excerpt.splitlines()) == 10


def test_ordered_streams_exact_then_driver_then_newest():
    with_driver = [
        {"logStreamName": "jr_1_g-old", "lastEventTimestamp": 10},
        {"logStreamName": "jr_1-driver"},
        {"logStreamName": "jr_1_g-new", "lastEventTimestamp": 99},
    ]
    assert _ordered_streams(with_driver, "jr_1")[0] == "jr_1-driver"

    # Company case: per-worker streams, no driver label → newest by last event.
    workers = [
        {"logStreamName": "jr_1_g-old", "lastEventTimestamp": 10},
        {"logStreamName": "jr_1_g-new", "lastEventTimestamp": 99},
    ]
    assert _ordered_streams(workers, "jr_1")[0] == "jr_1_g-new"


class _Logs:
    def describe_log_streams(self, logGroupName, logStreamNamePrefix):
        return {"logStreams": [{"logStreamName": "jr_1_g-db123"}]}

    def get_log_events(self, logGroupName, logStreamName, startFromHead, limit):
        return {"events": [{"message": "ok"}, {"message": "ValueError: bad"}]}


def test_error_excerpt_end_to_end():
    session = SimpleNamespace(client=lambda _s: _Logs())
    out = error_excerpt(session, "jr_1", "glueetl")
    assert out["available"] is True
    assert out["log_group"] == "/aws-glue/jobs/logs-v2"
    assert out["log_stream"] == "jr_1_g-db123"
    assert "ValueError" in out["excerpt"]


class _MultiWorkerLogs:
    """Per-worker error streams; only the older worker holds the traceback."""

    def describe_log_streams(self, logGroupName, logStreamNamePrefix):
        if logGroupName != "/aws-glue/jobs/logs-v2":
            return {"logStreams": []}
        return {
            "logStreams": [
                {"logStreamName": "jr_1_g-newnoise", "lastEventTimestamp": 200},
                {"logStreamName": "jr_1_g-oldboom", "lastEventTimestamp": 100},
            ]
        }

    def get_log_events(self, logGroupName, logStreamName, startFromHead, limit):
        if logStreamName == "jr_1_g-oldboom":
            return {"events": [{"message": "Caused by: java.lang.NullPointerException"}]}
        return {"events": [{"message": "progress 50%"}, {"message": "progress 100%"}]}


def test_error_excerpt_scans_workers_until_it_finds_the_error():
    session = SimpleNamespace(client=lambda _s: _MultiWorkerLogs())
    out = error_excerpt(session, "jr_1", "glueetl")
    assert out["log_stream"] == "jr_1_g-oldboom"  # newest was pure noise
    assert out["found_error_markers"] is True
    assert "NullPointerException" in out["excerpt"]


class _NoiseThenErrorGroup:
    """logs-v2 has only progress noise; the real error is in the error group."""

    def describe_log_streams(self, logGroupName, logStreamNamePrefix):
        if logGroupName == "/aws-glue/jobs/logs-v2":
            return {"logStreams": [{"logStreamName": "jr_1_g-noise", "lastEventTimestamp": 5}]}
        return {"logStreams": [{"logStreamName": "jr_1_g-boom", "lastEventTimestamp": 9}]}

    def get_log_events(self, logGroupName, logStreamName, startFromHead, limit):
        if logStreamName == "jr_1_g-boom":
            return {"events": [{"message": "Caused by: NullPointerException"}]}
        return {"events": [{"message": "progress 10%"}, {"message": "progress 100%"}]}


def test_error_excerpt_prefers_group_with_error_marker():
    session = SimpleNamespace(client=lambda _s: _NoiseThenErrorGroup())
    out = error_excerpt(session, "jr_1", "glueetl")
    assert out["log_group"] == "/aws-glue/jobs/error"  # skipped the noisy logs-v2
    assert out["found_error_markers"] is True
    assert "NullPointerException" in out["excerpt"]


class _NotFoundThenLegacy:
    def describe_log_streams(self, logGroupName, logStreamNamePrefix):
        if logGroupName == "/aws-glue/jobs/logs-v2":
            raise AwsClientError(
                {"Error": {"Code": "ResourceNotFoundException"}}, "DescribeLogStreams"
            )
        return {"logStreams": [{"logStreamName": "jr_1"}]}

    def get_log_events(self, logGroupName, logStreamName, startFromHead, limit):
        return {"events": [{"message": "Exception: boom"}]}


def test_error_excerpt_skips_missing_group():
    session = SimpleNamespace(client=lambda _s: _NotFoundThenLegacy())
    out = error_excerpt(session, "jr_1", "glueetl")
    assert out["available"] is True
    assert out["log_group"] == "/aws-glue/jobs/error"
