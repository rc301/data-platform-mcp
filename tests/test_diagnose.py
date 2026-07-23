from datetime import datetime, timezone
from types import SimpleNamespace

from dataplatform.glue import diagnose
from dataplatform.glue.diagnose import diagnose_job_run
from dataplatform.timeutil import fmt_brt


class _Glue:
    def __init__(self, state, command="glueetl"):
        self._state = state
        self._command = command

    def get_job(self, JobName):
        return {"Job": {"Command": {"Name": self._command}}}

    def get_job_run(self, JobName, RunId):
        return {
            "JobRun": {
                "JobRunState": self._state,
                "StartedOn": datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc),
                "CompletedOn": datetime(2026, 7, 22, 12, 5, tzinfo=timezone.utc),
                "ExecutionTime": 300,
                "WorkerType": "G.1X",
                "NumberOfWorkers": 2,
                "ErrorMessage": "boom",
            }
        }

    def get_job_runs(self, JobName, MaxResults):
        return {"JobRuns": [{"Id": "jr_1", "JobRunState": self._state, "ExecutionTime": 300}]}


def _session(glue, monkeypatch):
    # error_excerpt is exercised in test_logs; stub it here to isolate diagnose.
    monkeypatch.setattr(diagnose, "error_excerpt", lambda *a, **k: {"available": False})
    return SimpleNamespace(client=lambda _s: glue)


def test_fmt_brt_converts_utc_to_minus_three():
    dt = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)
    assert fmt_brt(dt) == "2026-07-22 09:00:00 BRT"


def test_success_run_has_no_error_excerpt(monkeypatch):
    result = diagnose_job_run(_session(_Glue("SUCCEEDED"), monkeypatch), "j", "jr_1")
    assert result["outcome"] == "success"
    assert "error_excerpt" not in result
    assert result["summary"]["duration_seconds"] == 300


def test_failed_run_includes_error_excerpt(monkeypatch):
    result = diagnose_job_run(_session(_Glue("FAILED"), monkeypatch), "j", "jr_1")
    assert result["outcome"] == "failure"
    assert result["error_message"] == "boom"
    assert "error_excerpt" in result
    assert result["recent_runs"][0]["is_current"] is True
