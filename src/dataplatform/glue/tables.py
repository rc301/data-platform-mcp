"""Catalog inspection for source tables (runs in the data account)."""

from __future__ import annotations

from typing import Any

from dataplatform.config import Session


def inspect_table(session: Session, database: str, table: str) -> dict[str, Any]:
    """Return schema + format of a catalog table, detecting Iceberg."""

    # TODO(empresa) item 9 — Lake Formation: sob LF, get_table pode devolver
    # colunas filtradas por permissão. Um "schema drift" aparente pode ser
    # efeito de permissão do data_profile, não do schema real. Registre isso no
    # diagnóstico da skill.
    tbl = session.client("glue").get_table(DatabaseName=database, Name=table)["Table"]
    params = tbl.get("Parameters", {}) or {}
    is_iceberg = params.get("table_type", "").upper() == "ICEBERG" or "metadata_location" in params
    storage = tbl.get("StorageDescriptor", {}) or {}
    return {
        "database": database,
        "table": table,
        "table_format": "iceberg" if is_iceberg else "hive",
        "location": storage.get("Location"),
        "columns": [
            {"name": c["Name"], "type": c["Type"]} for c in storage.get("Columns", [])
        ],
        "partition_keys": [
            {"name": c["Name"], "type": c["Type"]} for c in tbl.get("PartitionKeys", [])
        ],
    }


def check_partitions(
    session: Session, database: str, table: str, expression: str
) -> dict[str, Any]:
    """Check whether partitions matching ``expression`` exist in the catalog.

    Refuses Iceberg tables: their partitions are not in the Glue Data Catalog,
    so ``get_partitions`` would return misleading empties. The caller should
    inspect Iceberg metadata / Athena ``$partitions`` instead.
    """

    info = inspect_table(session, database, table)
    if info["table_format"] == "iceberg":
        return {
            "database": database,
            "table": table,
            "supported": False,
            "reason": (
                "tabela Iceberg: partições não vivem no Glue Data Catalog; "
                "verifique via metadados Iceberg ou Athena \"tb$partitions\""
            ),
        }

    # TODO(empresa) item 7 — paginação: MaxResults=100 sem paginar. Para checar
    # EXISTÊNCIA (exists) basta a 1ª página; mas matched_count satura em 100 e
    # engana em tabelas grandes. Se for reportar contagem, pagine ou rotule ">=100".
    resp = session.client("glue").get_partitions(
        DatabaseName=database, TableName=table, Expression=expression, MaxResults=100
    )
    parts = resp.get("Partitions", [])
    return {
        "database": database,
        "table": table,
        "supported": True,
        "expression": expression,
        "exists": bool(parts),
        "matched_count": len(parts),
        "sample_values": [p.get("Values") for p in parts[:25]],
    }
