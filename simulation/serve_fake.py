"""Sobe o servidor MCP **real** ligado ao AWS falso.

É o servidor de produção (mesmas tools, mesmas docstrings, mesma lógica) — só a
resolução de sessão é trocada, então nenhuma chamada sai para a AWS e nenhuma
credencial é necessária.

Use no Claude Code apontando um `.mcp.json` para este arquivo:

    {
      "mcpServers": {
        "data-platform": {
          "command": "python",
          "args": ["<caminho-absoluto>/simulation/serve_fake.py"]
        }
      }
    }

Aí `/analyze-job-run orders-etl jr_20260722_failed` roda de ponta a ponta offline.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Permite rodar como script solto (`python simulation/serve_fake.py`).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulation.fake_aws import fake_session  # noqa: E402


def main() -> None:
    try:
        from dataplatform.mcp import server
    except ImportError:
        print(
            "O servidor MCP precisa do extra [mcp]:\n  pip install -e '.[mcp,dev]'",
            file=sys.stderr,
        )
        raise SystemExit(1) from None

    # Troca o único ponto que fala com a AWS. As tools ficam intactas.
    server.resolve_session = fake_session  # type: ignore[assignment]

    print("MCP 'data-platform' em modo SIMULAÇÃO (AWS falso).", file=sys.stderr)
    server.mcp.run()


if __name__ == "__main__":
    main()
