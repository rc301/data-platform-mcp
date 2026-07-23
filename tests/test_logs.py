from types import SimpleNamespace

import pytest

from dataplatform.config import AwsClientError
from dataplatform.glue.logs import (
    _discover_log_groups,
    _extract,
    _ordered_streams,
    error_excerpt,
)


@pytest.fixture(autouse=True)
def _no_group_override(monkeypatch):
    # Discovery-based tests must not see an explicit-list override from the shell.
    monkeypatch.delenv("DATAPLATFORM_GLUE_LOG_GROUPS", raising=False)


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


def test_ordered_streams_driver_first_drops_progress_bar():
    streams = [
        {"logStreamName": "jr_1-progress-bar", "lastEventTimestamp": 999},
        {"logStreamName": "jr_1_g-exec", "lastEventTimestamp": 50},
        {"logStreamName": "jr_1", "lastEventTimestamp": 10},
    ]
    ordered = _ordered_streams(streams, "jr_1")
    assert ordered[0] == "jr_1"  # driver (exact run_id) first
    assert "jr_1-progress-bar" not in ordered  # noise dropped


def test_ordered_streams_newest_worker_when_no_driver():
    workers = [
        {"logStreamName": "jr_1_g-old", "lastEventTimestamp": 10},
        {"logStreamName": "jr_1_g-new", "lastEventTimestamp": 99},
    ]
    assert _ordered_streams(workers, "jr_1")[0] == "jr_1_g-new"


def test_discover_uses_env_override(monkeypatch):
    monkeypatch.setenv(
        "DATAPLATFORM_GLUE_LOG_GROUPS", "/g/x/error, /aws-glue/jobs/logs-v2-x"
    )
    groups = _discover_log_groups(logs=None, command_name="glueetl")
    assert groups == ["/g/x/error", "/aws-glue/jobs/logs-v2-x"]


class _LogsBase:
    """Standard account: the default error + continuous groups exist under root."""

    LOG_GROUPS = ["/aws-glue/jobs/error", "/aws-glue/jobs/logs-v2"]

    def describe_log_groups(self, logGroupNamePrefix, limit, **kw):
        return {"logGroups": [{"logGroupName": n} for n in self.LOG_GROUPS]}


class _Logs(_LogsBase):
    def describe_log_streams(self, logGroupName, logStreamNamePrefix):
        return {"logStreams": [{"logStreamName": "jr_1_g-db123"}]}

    def get_log_events(self, logGroupName, logStreamName, startFromHead, limit):
        return {"events": [{"message": "ok"}, {"message": "ValueError: bad"}]}


def test_error_excerpt_end_to_end():
    session = SimpleNamespace(client=lambda _s: _Logs())
    out = error_excerpt(session, "jr_1", "glueetl")
    assert out["available"] is True
    assert out["log_group"] == "/aws-glue/jobs/error"  # first error-bearing group
    assert out["log_stream"] == "jr_1_g-db123"
    assert "ValueError" in out["excerpt"]


class _MultiWorkerLogs(_LogsBase):
    """Per-worker error streams; only the older worker holds the traceback."""

    LOG_GROUPS = ["/aws-glue/jobs/logs-v2"]

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


class _NoiseThenErrorGroup(_LogsBase):
    """The /error group has only progress noise; the traceback is in logs-v2."""

    def describe_log_streams(self, logGroupName, logStreamNamePrefix):
        return {"logStreams": [{"logStreamName": "jr_1"}]}

    def get_log_events(self, logGroupName, logStreamName, startFromHead, limit):
        if logGroupName == "/aws-glue/jobs/logs-v2":
            return {"events": [{"message": "Caused by: NullPointerException"}]}
        return {"events": [{"message": "progress 10%"}, {"message": "progress 100%"}]}


def test_error_excerpt_prefers_group_with_error_marker():
    session = SimpleNamespace(client=lambda _s: _NoiseThenErrorGroup())
    out = error_excerpt(session, "jr_1", "glueetl")
    assert out["log_group"] == "/aws-glue/jobs/logs-v2"  # skipped the noisy /error
    assert out["found_error_markers"] is True
    assert "NullPointerException" in out["excerpt"]


class _EmptyDiscoveryNotFound(_LogsBase):
    """Discovery finds nothing; the defaulted /error group 404s, logs-v2 has it."""

    def describe_log_groups(self, logGroupNamePrefix, limit, **kw):
        return {"logGroups": []}

    def describe_log_streams(self, logGroupName, logStreamNamePrefix):
        if logGroupName.endswith("/error"):
            raise AwsClientError(
                {"Error": {"Code": "ResourceNotFoundException"}}, "DescribeLogStreams"
            )
        return {"logStreams": [{"logStreamName": "jr_1"}]}

    def get_log_events(self, logGroupName, logStreamName, startFromHead, limit):
        return {"events": [{"message": "Exception: boom"}]}


def test_error_excerpt_skips_missing_group():
    session = SimpleNamespace(client=lambda _s: _EmptyDiscoveryNotFound())
    out = error_excerpt(session, "jr_1", "glueetl")
    assert out["available"] is True
    assert out["log_group"] == "/aws-glue/jobs/logs-v2"


class _NestedPathLogs(_LogsBase):
    """Real shape: nested `/error` group + flat `logs-v2-<sec>` All-Logs group."""

    ERROR_GROUP = "/aws-glue/jobs/authorized-sec-config/analytics/products-role/error"
    ALL_LOGS = "/aws-glue/jobs/logs-v2-authorized-sec-config"

    OUTPUT_GROUP = "/aws-glue/jobs/authorized-sec-config/analytics/products-role/output"

    def describe_log_groups(self, logGroupNamePrefix, limit, **kw):
        return {
            "logGroups": [
                {"logGroupName": self.OUTPUT_GROUP},
                {"logGroupName": self.ERROR_GROUP},
                {"logGroupName": self.ALL_LOGS},
            ]
        }

    def describe_log_streams(self, logGroupName, logStreamNamePrefix):
        if logGroupName == self.ERROR_GROUP:
            return {"logStreams": [{"logStreamName": "jr_1"}]}
        return {"logStreams": []}

    def get_log_events(self, logGroupName, logStreamName, startFromHead, limit):
        return {"events": [{"message": "Caused by: RuntimeError"}]}


def test_discovers_error_and_all_logs_groups():
    groups = _discover_log_groups(_NestedPathLogs(), "glueetl")
    assert groups[0] == _NestedPathLogs.ERROR_GROUP  # /error first
    assert _NestedPathLogs.ALL_LOGS in groups  # flat logs-v2-<sec> discovered
    assert all(not g.endswith("/output") for g in groups)  # stdout excluded


def test_error_excerpt_discovers_nested_group():
    session = SimpleNamespace(client=lambda _s: _NestedPathLogs())
    out = error_excerpt(session, "jr_1", "glueetl")
    assert out["log_group"] == _NestedPathLogs.ERROR_GROUP
    assert "RuntimeError" in out["excerpt"]
