"""Minimal eval runner for the failure-diagnosis path.

Each case in ``cases/*.json`` records a CloudWatch error stream (anonymized) and
what a good excerpt must surface. We feed the recorded lines through the *real*
``error_excerpt`` code via a fake logs client, so this measures the extractor
that most affects diagnosis quality — no AWS, no model, deterministic.

Run: ``python evals/run_evals.py`` (exits non-zero if any case fails).

The model-judgment layer (does the agent name the right cause from the excerpt?)
needs real cases + a grader and is intentionally out of scope here — this pins
the deterministic foundation first.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dataplatform.glue.logs import error_excerpt  # noqa: E402

CASES_DIR = Path(__file__).parent / "cases"


def _fake_session(run_id: str, log_lines: list[str]) -> SimpleNamespace:
    """A session whose logs client replays the recorded stream."""

    class _Logs:
        def describe_log_groups(self, logGroupNamePrefix, limit, **kw):
            return {"logGroups": [{"logGroupName": "/aws-glue/jobs/error"}]}

        def describe_log_streams(self, logGroupName, logStreamNamePrefix):
            return {"logStreams": [{"logStreamName": run_id}]}

        def get_log_events(self, logGroupName, logStreamName, startFromHead, limit):
            return {"events": [{"message": line} for line in log_lines]}

    return SimpleNamespace(client=lambda _service: _Logs())


def _run_case(case: dict) -> list[str]:
    run_id = case.get("run_id", "jr_eval")
    session = _fake_session(run_id, case["log_lines"])
    result = error_excerpt(session, run_id, case.get("command_name", "glueetl"))

    failures: list[str] = []
    expect = case.get("expect", {})

    if "found_markers" in expect and result.get("found_error_markers") != expect["found_markers"]:
        failures.append(
            f"found_error_markers={result.get('found_error_markers')} "
            f"(esperado {expect['found_markers']})"
        )
    excerpt = result.get("excerpt", "")
    for needle in expect.get("excerpt_contains", []):
        if needle not in excerpt:
            failures.append(f"excerpt não contém: {needle!r}")
    for needle in expect.get("excerpt_excludes", []):
        if needle in excerpt:
            failures.append(f"excerpt não deveria conter: {needle!r}")
    return failures


def main() -> int:
    cases = sorted(CASES_DIR.glob("*.json"))
    if not cases:
        print("nenhum caso em evals/cases/ — adicione falhas reais anonimizadas.")
        return 0

    failed = 0
    for path in cases:
        case = json.loads(path.read_text(encoding="utf-8"))
        problems = _run_case(case)
        if problems:
            failed += 1
            print(f"FAIL  {path.name} — {case.get('name', '')}")
            for p in problems:
                print(f"        · {p}")
        else:
            print(f"PASS  {path.name} — {case.get('name', '')}")

    print(f"\n{len(cases) - failed}/{len(cases)} casos passaram.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
