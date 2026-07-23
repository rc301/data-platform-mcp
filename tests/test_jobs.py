from types import SimpleNamespace

from dataplatform.glue.jobs import get_job, list_jobs


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


def _session(glue):
    return SimpleNamespace(client=lambda _s: glue)


def test_list_jobs_filters_by_substring():
    glue = _Glue([{"Name": "orders-etl"}, {"Name": "clicks-etl"}])
    names = [j["name"] for j in list_jobs(_session(glue), name_contains="orders")]
    assert names == ["orders-etl"]


def test_get_job_keeps_only_portable_fields():
    glue = _Glue(
        [{"Name": "orders-etl", "Role": "r", "CreatedOn": "x", "Command": {"Name": "glueetl"}}]
    )
    config = get_job(_session(glue), "orders-etl")
    assert "CreatedOn" not in config
    assert config["Role"] == "r"
