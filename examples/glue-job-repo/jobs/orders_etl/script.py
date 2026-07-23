"""Exemplo mínimo de Glue job. A lógica de transformação fica isolada em
``transform`` para poder ser testada sem AWS (ver ../../tests)."""

import sys


def transform(rows: list[dict]) -> list[dict]:
    """Regra de negócio pura: normaliza status e descarta pedidos vazios."""
    out = []
    for row in rows:
        if not row.get("order_id"):
            continue
        out.append({**row, "status": (row.get("status") or "unknown").lower()})
    return out


def main() -> None:  # pragma: no cover - executado apenas dentro do Glue
    from awsglue.utils import getResolvedOptions  # type: ignore

    args = getResolvedOptions(sys.argv, ["JOB_NAME", "source_path", "target_path"])
    # ... leitura via Spark, transform(...), escrita. Omitido no exemplo.
    print(f"running {args['JOB_NAME']}")


if __name__ == "__main__":
    main()
