from types import SimpleNamespace

from dataplatform.glue.logs import _extract, _pick_stream, error_excerpt


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


def test_pick_stream_prefers_exact_then_driver():
    streams = [{"logStreamName": "jr_1-executor-1"}, {"logStreamName": "jr_1-driver"}]
    assert _pick_stream(streams, "jr_1") == "jr_1-driver"


class _Logs:
    def describe_log_streams(self, logGroupName, logStreamNamePrefix):
        return {"logStreams": [{"logStreamName": "jr_1-driver"}]}

    def get_log_events(self, logGroupName, logStreamName, startFromHead, limit):
        return {"events": [{"message": "ok"}, {"message": "ValueError: bad"}]}


def test_error_excerpt_end_to_end():
    session = SimpleNamespace(client=lambda _s: _Logs())
    out = error_excerpt(session, "jr_1", "glueetl")
    assert out["available"] is True
    assert out["log_group"] == "/aws-glue/jobs/error"
    assert "ValueError" in out["excerpt"]
