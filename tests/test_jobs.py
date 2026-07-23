from types import SimpleNamespace

from datetime import datetime, timezone

from dataplatform.glue.jobs import get_job, list_job_runs, list_jobs


class _Paginator:
    def __init__(self, pages):
        self._pages = pages

    def paginate(self):
        return iter(self._pages)


class _Glue:
    def __init__(self, jobs):
        self._jobs = jobs

    def get_paginator(self, _op):
        return _Paginator([{"Jobs": self._jobs}])

    def get_job(self, JobName):
        job = next(j for j in self._jobs if j["Name"] == JobName)
        return {"Job": job}

    def get_job_runs(self, JobName, MaxResults):
        return {
            "JobRuns": [
                {
                    "Id": "jr_1",
                    "JobRunState": "SUCCEEDED",
                    "StartedOn": datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc),
                    "ExecutionTime": 120,
                }
            ]
        }


def _session(glue):
    return SimpleNamespace(client=lambda _s: glue)


def test_list_jobs_filters_by_substring():
    glue = _Glue([{"Name": "orders-etl"}, {"Name": "clicks-etl"}])
    names = [j["name"] for j in list_jobs(_session(glue), name_contains="orders")]
    assert names == ["orders-etl"]


def test_list_job_runs_formats_start_in_brt():
    glue = _Glue([{"Name": "orders-etl"}])
    runs = list_job_runs(_session(glue), "orders-etl")
    assert runs[0]["run_id"] == "jr_1"
    assert runs[0]["started_brt"] == "2026-07-22 09:00:00 BRT"


def test_get_job_keeps_only_portable_fields():
    glue = _Glue(
        [{"Name": "orders-etl", "Role": "r", "CreatedOn": "x", "Command": {"Name": "glueetl"}}]
    )
    config = get_job(_session(glue), "orders-etl")
    assert "CreatedOn" not in config
    assert config["Role"] == "r"
