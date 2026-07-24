"""AWS falso (Glue + CloudWatch Logs) para simular o toolkit sem credencial.

Implementa **apenas** os métodos boto3 que o codebase realmente chama, com dados
realistas — incluindo dois runs que falharam, um com o traceback no stream do
driver e outro só no stream do executor (`<run_id>_g-<hash>`), que é o caso que
valida a varredura de streams do item 3.

Nada aqui é empacotado: `simulation/` vive fora de `src/`, é só ferramenta de dev.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from dataplatform.config import AwsClientError, Session

ACCOUNT_ID = "123456789012"
REGION = "sa-east-1"
PROFILE = "fake-dev"

# ---------------------------------------------------------------- jobs / runs

FAILED_RUN = "jr_20260722_failed"
OOM_RUN = "jr_20260719_oom"
OK_RUN = "jr_20260721_ok"

_JOBS: list[dict[str, Any]] = [
    {
        "Name": "orders-etl",
        "Description": "Consolida pedidos por dia",
        "GlueVersion": "4.0",
        "WorkerType": "G.1X",
        "NumberOfWorkers": 10,
        "Role": "arn:aws:iam::123456789012:role/GlueETLRole",
        "Command": {"Name": "glueetl", "ScriptLocation": "s3://artifacts/orders_etl/script.py"},
        "DefaultArguments": {"--job-bookmark-option": "job-bookmark-enable"},
        "Timeout": 60,
        "CreatedOn": "2025-01-10T09:00:00Z",  # campo NÃO portável: some no get_job
    },
    {
        "Name": "clicks-ingest",
        "Description": "Ingestão de cliques",
        "GlueVersion": "4.0",
        "WorkerType": "G.2X",
        "NumberOfWorkers": 4,
        "Role": "arn:aws:iam::123456789012:role/GlueETLRole",
        "Command": {"Name": "glueetl", "ScriptLocation": "s3://artifacts/clicks/script.py"},
    },
    {
        "Name": "legacy-report",
        "Description": "Relatório legado (pythonshell)",
        "GlueVersion": "3.0",
        "MaxCapacity": 0.0625,
        "Role": "arn:aws:iam::123456789012:role/GlueShellRole",
        "Command": {"Name": "pythonshell", "ScriptLocation": "s3://artifacts/legacy/report.py"},
    },
]

_RUNS: dict[str, list[dict[str, Any]]] = {
    "orders-etl": [
        {
            "Id": FAILED_RUN,
            "JobRunState": "FAILED",
            "StartedOn": datetime(2026, 7, 22, 12, 0, tzinfo=UTC),
            "CompletedOn": datetime(2026, 7, 22, 12, 4, tzinfo=UTC),
            "ExecutionTime": 240,
            "WorkerType": "G.1X",
            "NumberOfWorkers": 10,
            "DPUSeconds": 2400,
            "ErrorMessage": "AnalysisException: cannot resolve 'customer_id'",
        },
        {
            "Id": OK_RUN,
            "JobRunState": "SUCCEEDED",
            "StartedOn": datetime(2026, 7, 21, 12, 0, tzinfo=UTC),
            "CompletedOn": datetime(2026, 7, 21, 12, 6, tzinfo=UTC),
            "ExecutionTime": 360,
            "WorkerType": "G.1X",
            "NumberOfWorkers": 10,
        },
        {
            "Id": OOM_RUN,
            "JobRunState": "FAILED",
            "StartedOn": datetime(2026, 7, 19, 12, 0, tzinfo=UTC),
            "CompletedOn": datetime(2026, 7, 19, 12, 30, tzinfo=UTC),
            "ExecutionTime": 1800,
            "WorkerType": "G.1X",
            "NumberOfWorkers": 10,
            "ErrorMessage": "Command failed with exit code 1",
        },
    ],
    "clicks-ingest": [
        {
            "Id": "jr_clicks_ok",
            "JobRunState": "SUCCEEDED",
            "StartedOn": datetime(2026, 7, 22, 3, 0, tzinfo=UTC),
            "ExecutionTime": 120,
        }
    ],
}

# ------------------------------------------------------------------- catálogo

_TABLES: dict[str, dict[str, Any]] = {
    "db_vendas.orders": {
        "Name": "orders",
        "StorageDescriptor": {
            "Location": "s3://lake/vendas/orders/",
            "Columns": [
                {"Name": "order_id", "Type": "bigint"},
                {"Name": "order_ts", "Type": "timestamp"},
                {"Name": "amount", "Type": "decimal(10,2)"},
            ],
        },
        "PartitionKeys": [{"Name": "dt", "Type": "string"}],
        "Parameters": {},
    },
    "db_vendas.orders_iceberg": {
        "Name": "orders_iceberg",
        "StorageDescriptor": {"Location": "s3://lake/vendas/orders_ice/", "Columns": []},
        "PartitionKeys": [],
        "Parameters": {"table_type": "ICEBERG"},
    },
}

_EXISTING_PARTITIONS = {"dt='2026-07-22'", "dt='2026-07-21'"}

# ----------------------------------------------------------------- log groups

ERROR_GROUP = "/aws-glue/jobs/sec-config-prod/vendas/etl-role/error"
ALL_LOGS_GROUP = "/aws-glue/jobs/logs-v2-sec-config-prod"

# Ruído típico antes do erro, para o extrator ter uma janela para recortar.
_NOISE = [f"INFO  Stage {i}/40 finished in {i * 3}s" for i in range(1, 26)]

_DRIVER_TRACEBACK = [
    *_NOISE,
    "INFO  Starting job stage 26/40",
    "Traceback (most recent call last):",
    '  File "/tmp/orders_etl/script.py", line 88, in <module>',
    "    df = df.select('order_id', 'customer_id', 'amount')",
    "py4j.protocol.Py4JJavaError: An error occurred while calling o142.select.",
    ": org.apache.spark.sql.AnalysisException: cannot resolve 'customer_id' "
    "given input columns: [order_id, order_ts, amount, dt]",
    "Caused by: org.apache.spark.sql.catalyst.analysis.UnresolvedException: "
    "cannot resolve 'customer_id'",
    "INFO  Shutting down executors",
]

_EXECUTOR_OOM = [
    *_NOISE,
    "INFO  Task 1042 running on executor g-9f2c1a",
    "ERROR Executor: Exception in task 1042.0 in stage 12.0",
    "java.lang.OutOfMemoryError: Java heap space",
    "  at org.apache.spark.sql.execution.SortExec.doExecute(SortExec.scala:102)",
    "Caused by: java.lang.OutOfMemoryError: Java heap space",
]

# Streams por (grupo, run_id). O driver é exatamente `<run_id>`; executores levam
# `_g-<hash>`; o `-progress-bar` é ruído puro que o toolkit descarta.
_STREAMS: dict[tuple[str, str], list[dict[str, Any]]] = {
    (ERROR_GROUP, FAILED_RUN): [
        {"logStreamName": f"{FAILED_RUN}-progress-bar", "lastEventTimestamp": 9999},
        {"logStreamName": f"{FAILED_RUN}_g-a1b2c3", "lastEventTimestamp": 500},
        {"logStreamName": FAILED_RUN, "lastEventTimestamp": 400},
    ],
    # Caso do item 3: o driver não tem o erro; só o executor tem.
    (ERROR_GROUP, OOM_RUN): [
        {"logStreamName": OOM_RUN, "lastEventTimestamp": 100},
        {"logStreamName": f"{OOM_RUN}_g-9f2c1a", "lastEventTimestamp": 800},
    ],
}

_EVENTS: dict[str, list[str]] = {
    FAILED_RUN: _DRIVER_TRACEBACK,
    f"{FAILED_RUN}_g-a1b2c3": [*_NOISE, "INFO  Executor finished cleanly"],
    f"{FAILED_RUN}-progress-bar": ["|=====>    | 55%"],
    OOM_RUN: [*_NOISE, "INFO  Driver waiting for executors"],
    f"{OOM_RUN}_g-9f2c1a": _EXECUTOR_OOM,
}


def _not_found(operation: str) -> AwsClientError:
    return AwsClientError(
        {"Error": {"Code": "ResourceNotFoundException", "Message": "group não existe"}},
        operation,
    )


class _Paginator:
    def __init__(self, pages: list[dict[str, Any]]) -> None:
        self._pages = pages

    def paginate(self) -> Any:
        return iter(self._pages)


class FakeGlue:
    """Só os métodos do Glue que o toolkit chama."""

    def get_paginator(self, operation: str) -> _Paginator:
        assert operation == "get_jobs"
        # Duas páginas, para exercitar a paginação de verdade.
        return _Paginator([{"Jobs": _JOBS[:2]}, {"Jobs": _JOBS[2:]}])

    def get_job(self, JobName: str) -> dict[str, Any]:  # noqa: N803 (assinatura boto3)
        for job in _JOBS:
            if job["Name"] == JobName:
                return {"Job": job}
        raise _not_found("GetJob")

    def get_job_runs(self, JobName: str, MaxResults: int) -> dict[str, Any]:  # noqa: N803
        return {"JobRuns": _RUNS.get(JobName, [])[:MaxResults]}

    def get_job_run(self, JobName: str, RunId: str) -> dict[str, Any]:  # noqa: N803
        for run in _RUNS.get(JobName, []):
            if run["Id"] == RunId:
                return {"JobRun": run}
        raise _not_found("GetJobRun")

    def get_table(self, DatabaseName: str, Name: str) -> dict[str, Any]:  # noqa: N803
        table = _TABLES.get(f"{DatabaseName}.{Name}")
        if table is None:
            raise _not_found("GetTable")
        return {"Table": table}

    def get_partitions(  # noqa: N803
        self, DatabaseName: str, TableName: str, Expression: str, MaxResults: int
    ) -> dict[str, Any]:
        if Expression.replace(" ", "") in _EXISTING_PARTITIONS:
            return {"Partitions": [{"Values": [Expression.split("=")[-1].strip("'")]}]}
        return {"Partitions": []}


class FakeLogs:
    """Só os métodos do CloudWatch Logs que o toolkit chama."""

    def describe_log_groups(
        self,
        logGroupNamePrefix: str,  # noqa: N803
        limit: int = 50,
        nextToken: str | None = None,  # noqa: N803
    ) -> dict[str, Any]:
        # Duas páginas, para exercitar o nextToken do descobridor.
        if nextToken is None:
            return {"logGroups": [{"logGroupName": ALL_LOGS_GROUP}], "nextToken": "pag2"}
        return {"logGroups": [{"logGroupName": ERROR_GROUP}]}

    def describe_log_streams(
        self, logGroupName: str, logStreamNamePrefix: str  # noqa: N803
    ) -> dict[str, Any]:
        streams = _STREAMS.get((logGroupName, logStreamNamePrefix))
        if streams is None:
            # Grupos que não existem nesta conta (os fallbacks genéricos).
            raise _not_found("DescribeLogStreams")
        return {"logStreams": streams}

    def get_log_events(
        self,
        logGroupName: str,  # noqa: N803
        logStreamName: str,  # noqa: N803
        startFromHead: bool = False,  # noqa: N803
        limit: int = 500,
    ) -> dict[str, Any]:
        lines = _EVENTS.get(logStreamName, [])
        return {"events": [{"message": line} for line in lines[-limit:]]}


class _FakeBoto:
    """Faz o papel do ``boto3.Session`` — só precisa de ``client`` e ``region_name``."""

    region_name = REGION

    def client(self, service: str) -> Any:
        if service == "glue":
            return FakeGlue()
        if service == "logs":
            return FakeLogs()
        raise ValueError(f"serviço não simulado: {service}")


def fake_session(profile: str | None = None, region: str | None = None) -> Session:
    """Uma ``Session`` real do toolkit, apontando para o AWS falso.

    Usa a dataclass verdadeira, então o caminho ``Session.client()`` do código de
    produção é exercitado de verdade — só o boto3 por baixo é falso.
    """
    return Session(
        boto=_FakeBoto(),  # type: ignore[arg-type]
        account_id=ACCOUNT_ID,
        profile=profile or PROFILE,
        region=region or REGION,
    )
