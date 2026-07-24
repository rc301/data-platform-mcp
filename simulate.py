"""UM comando para testar tudo localmente, sem nenhum acesso à AWS.

    python simulate.py

Roda, em ordem: lint (ruff) → tipos (mypy) → testes (pytest) → evals do
diagnóstico → simulação end-to-end das tools contra um AWS falso. Sai com código
!= 0 se algo falhar, então serve tanto para você quanto para a esteira.

ruff/mypy são pulados com aviso se o extra [dev] não estiver instalado; o resto
roda sempre.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


def _have(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def _run(label: str, args: list[str]) -> bool:
    # flush antes de ceder o stdout ao subprocesso, senão a ordem embaralha
    # quando a saída é redirecionada (buffer do pai vs. escrita direta do filho).
    print(f"\n{DIM}{'─' * 72}{RESET}")
    print(f"▶ {label}")
    print(f"{DIM}  $ {' '.join(args)}{RESET}\n", flush=True)
    return subprocess.run(args, cwd=ROOT, check=False).returncode == 0


def main() -> int:
    if not _have("dataplatform"):
        print(
            f"{RED}O pacote 'dataplatform' não está instalado neste Python.{RESET}\n"
            "Instale primeiro:\n\n    pip install -e \".[mcp,dev]\"\n"
        )
        return 1

    results: list[tuple[str, str]] = []

    # 1. lint ----------------------------------------------------------------
    if _have("ruff"):
        ok = _run("Lint (ruff)", [sys.executable, "-m", "ruff", "check", "."])
        results.append(("Lint (ruff)", "ok" if ok else "falhou"))
    else:
        results.append(("Lint (ruff)", "pulado — sem extra [dev]"))

    # 2. tipos ---------------------------------------------------------------
    if _have("mypy"):
        ok = _run("Tipos (mypy)", [sys.executable, "-m", "mypy"])
        results.append(("Tipos (mypy)", "ok" if ok else "falhou"))
    else:
        results.append(("Tipos (mypy)", "pulado — sem extra [dev]"))

    # 3. testes unitários ----------------------------------------------------
    if _have("pytest"):
        ok = _run("Testes unitários (pytest)", [sys.executable, "-m", "pytest", "-q"])
        results.append(("Testes (pytest)", "ok" if ok else "falhou"))
    else:
        results.append(("Testes (pytest)", "pulado — sem extra [dev]"))

    # 4. evals do diagnóstico ------------------------------------------------
    ok = _run("Evals do diagnóstico", [sys.executable, str(ROOT / "evals" / "run_evals.py")])
    results.append(("Evals", "ok" if ok else "falhou"))

    # 5. simulação end-to-end ------------------------------------------------
    ok = _run(
        "Simulação end-to-end (AWS falso)",
        [sys.executable, str(ROOT / "simulation" / "demo.py")],
    )
    results.append(("Simulação", "ok" if ok else "falhou"))

    # resumo -----------------------------------------------------------------
    print(f"\n{DIM}{'═' * 72}{RESET}")
    print("RESUMO\n")
    failed = 0
    for label, status in results:
        if status == "ok":
            mark, color = "✅", GREEN
        elif status.startswith("pulado"):
            mark, color = "⏭ ", YELLOW
        else:
            mark, color = "❌", RED
            failed += 1
        print(f"  {mark} {color}{label:<28}{RESET} {status}")

    print(f"\n{DIM}{'═' * 72}{RESET}")
    if failed:
        print(f"{RED}{failed} etapa(s) falharam.{RESET}")
        return 1
    print(f"{GREEN}Tudo verde — o toolkit funciona localmente, sem AWS.{RESET}")
    print(
        f"\n{DIM}Para testar no Claude Code sem AWS, veja simulation/README.md"
        f" (servidor MCP falso).{RESET}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
