"""CloudWatch log extraction for Glue job runs.

The goal is a *bounded, high-signal* excerpt — never the raw stream. Fatal
errors sit near the end of the error stream, so we tail it and return a window
around the last error marker (or the tail itself if no marker is found). This
keeps large logs out of the agent's context; the model interprets the excerpt.
"""

from __future__ import annotations

from typing import Any

from dataplatform.config import AwsClientError, Session

# Error log group depends on the job type (Command.Name).
# TODO(empresa) item 3 — log group: estes são os grupos "legado". Se a empresa
# usa continuous logging (padrão atual), os logs vão em /aws-glue/jobs/logs-v2
# com estrutura de stream diferente. Valide grupo + naming contra um run real
# falhado antes de confiar no excerto (ver também _pick_stream).
_ERROR_LOG_GROUP = {
    "glueetl": "/aws-glue/jobs/error",
    "gluestreaming": "/aws-glue/jobs/error",
    "pythonshell": "/aws-glue/python-jobs/error",
}
_DEFAULT_ERROR_LOG_GROUP = "/aws-glue/jobs/error"

# Markers that usually bracket the real cause. Order-independent; matched as
# substrings against each event line.
_ERROR_MARKERS = ("Traceback", "Caused by", "Exception", "ERROR", "Error")

_CONTEXT_BEFORE = 15


def error_excerpt(
    session: Session,
    run_id: str,
    command_name: str,
    *,
    max_lines: int = 60,
    tail_events: int = 500,
) -> dict[str, Any]:
    """Return a bounded excerpt from the run's CloudWatch error log."""

    log_group = _ERROR_LOG_GROUP.get(command_name, _DEFAULT_ERROR_LOG_GROUP)
    logs = session.client("logs")

    try:
        streams = logs.describe_log_streams(
            logGroupName=log_group, logStreamNamePrefix=run_id
        ).get("logStreams", [])
    except AwsClientError as exc:
        return {
            "log_group": log_group,
            "available": False,
            "note": f"não foi possível ler o log: {exc.response['Error']['Code']}",
        }

    if not streams:
        return {"log_group": log_group, "available": False, "note": "sem log stream para o run"}

    stream_name = _pick_stream(streams, run_id)
    events = logs.get_log_events(
        logGroupName=log_group,
        logStreamName=stream_name,
        startFromHead=False,
        limit=tail_events,
    ).get("events", [])

    lines = [str(e.get("message", "")).rstrip("\n") for e in events]
    excerpt, found = _extract(lines, max_lines)
    return {
        "log_group": log_group,
        "log_stream": stream_name,
        "available": True,
        "found_error_markers": found,
        "excerpt": excerpt,
    }


def _pick_stream(streams: list[dict[str, Any]], run_id: str) -> str:
    # TODO(empresa) item 3 — naming de stream: com continuous logging o stream é
    # <run_id>_<attempt> e há streams -driver / executor separados. Ajuste a
    # heurística abaixo depois de olhar os streams reais do grupo logs-v2.
    names = [s["logStreamName"] for s in streams]
    for name in names:
        if name == run_id:
            return name
    for name in names:
        if "driver" in name:
            return name
    return names[0]


def _extract(lines: list[str], max_lines: int) -> tuple[str, bool]:
    if not lines:
        return "", False
    for i in range(len(lines) - 1, -1, -1):
        if any(marker in lines[i] for marker in _ERROR_MARKERS):
            start = max(0, i - _CONTEXT_BEFORE)
            return "\n".join(lines[start : start + max_lines]), True
    return "\n".join(lines[-max_lines:]), False
