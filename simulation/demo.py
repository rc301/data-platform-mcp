"""Exercita todas as tools contra o AWS falso e confere o resultado.

É demo **e** smoke test: imprime o que cada tool devolveria e falha (exit != 0)
se algum invariante quebrar. Rode com ``python simulation/demo.py``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Permite rodar como script solto (`python simulation/demo.py`) ou como módulo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dataplatform import glue  # noqa: E402
from simulation.fake_aws import (  # noqa: E402
    ACCOUNT_ID,
    FAILED_RUN,
    OK_RUN,
    OOM_RUN,
    fake_session,
)

_failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ✅ {label}")
    else:
        print(f"  ❌ {label} {detail}")
        _failures.append(label)


def show(title: str, payload: Any, limit: int = 700) -> None:
    print(f"\n── {title} " + "─" * max(0, 60 - len(title)))
    text = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    print(text[:limit] + ("\n  … (truncado)" if len(text) > limit else ""))


def main() -> int:
    session = fake_session()

    print("=" * 72)
    print("SIMULAÇÃO — toolkit rodando contra um AWS falso (nenhuma credencial)")
    print("=" * 72)

    # 1. identidade -----------------------------------------------------------
    show("get_server_info", {"aws_account": session.account_id, "aws_region": session.region})
    check("identidade resolvida", session.account_id == ACCOUNT_ID)

    # 2. listar jobs (exercita a paginação) -----------------------------------
    jobs = glue.list_jobs(session)
    show("list_glue_jobs", jobs)
    check("lista 3 jobs (2 páginas)", len(jobs) == 3, f"veio {len(jobs)}")

    filtered = glue.list_jobs(session, name_contains="orders")
    check("filtro por substring", [j["name"] for j in filtered] == ["orders-etl"])

    # 3. inspecionar job ------------------------------------------------------
    config = glue.get_job(session, "orders-etl")
    show("inspect_glue_job", config)
    check("mantém só campos portáveis", "CreatedOn" not in config)
    check("traz o Role", config.get("Role", "").endswith("GlueETLRole"))

    # 4. histórico de runs ----------------------------------------------------
    runs = glue.list_job_runs(session, "orders-etl")
    show("list_job_runs", runs)
    check("horário convertido para BRT", runs[0]["started_brt"].endswith("BRT"))
    check("09:00 BRT = 12:00 UTC", runs[0]["started_brt"].startswith("2026-07-22 09:00"))

    # 5. diagnóstico: falha com traceback no DRIVER ---------------------------
    diag = glue.diagnose_job_run(session, "orders-etl", FAILED_RUN)
    show("diagnose_job_run (falha — traceback no driver)", diag, limit=1400)
    check("classificado como falha", diag["outcome"] == "failure")
    excerpt = diag["error_excerpt"]
    check("achou marcador de erro", excerpt.get("found_error_markers") is True)
    check("excerto contém a causa raiz", "Caused by" in excerpt.get("excerpt", ""))
    check("escolheu o stream do driver", excerpt.get("log_stream") == FAILED_RUN)
    check("descartou o progress-bar", "progress-bar" not in excerpt.get("log_stream", ""))

    # 6. diagnóstico: erro só no stream do EXECUTOR (o caso do item 3) --------
    diag_oom = glue.diagnose_job_run(session, "orders-etl", OOM_RUN)
    show("diagnose_job_run (falha — OOM só no executor)", diag_oom.get("error_excerpt"), limit=900)
    oom = diag_oom["error_excerpt"]
    check("varreu além do driver até achar o erro", oom.get("found_error_markers") is True)
    check("achou o stream do executor <run>_g-<hash>", "_g-" in oom.get("log_stream", ""))
    check("excerto traz o OutOfMemoryError", "OutOfMemoryError" in oom.get("excerpt", ""))

    # 7. run que deu certo ----------------------------------------------------
    ok = glue.diagnose_job_run(session, "orders-etl", OK_RUN)
    check(
        "run bem-sucedido não busca log",
        ok["outcome"] == "success" and "error_excerpt" not in ok,
    )

    # 8. catálogo -------------------------------------------------------------
    table = glue.inspect_table(session, "db_vendas", "orders")
    show("inspect_table", table)
    check("detecta formato hive", table["table_format"] == "hive")
    check("lê as colunas", [c["name"] for c in table["columns"]][:1] == ["order_id"])
    check("lê a partition key", table["partition_keys"][0]["name"] == "dt")

    iceberg = glue.inspect_table(session, "db_vendas", "orders_iceberg")
    check("detecta Iceberg", iceberg["table_format"] == "iceberg")

    # 9. partições ------------------------------------------------------------
    present = glue.check_partitions(session, "db_vendas", "orders", "dt='2026-07-22'")
    show("check_partitions (existe)", present)
    check("partição existente encontrada", present["exists"] is True)

    missing = glue.check_partitions(session, "db_vendas", "orders", "dt='2026-07-30'")
    check("partição ausente reportada", missing["exists"] is False)

    refused = glue.check_partitions(session, "db_vendas", "orders_iceberg", "dt='2026-07-22'")
    show("check_partitions (Iceberg — recusa proposital)", refused)
    check("recusa Iceberg", refused["supported"] is False)

    # resumo ------------------------------------------------------------------
    print("\n" + "=" * 72)
    if _failures:
        print(f"FALHOU — {len(_failures)} verificação(ões): {', '.join(_failures)}")
        return 1
    print("TUDO OK — todas as tools responderam corretamente contra o AWS falso.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
