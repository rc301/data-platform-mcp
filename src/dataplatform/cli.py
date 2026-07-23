"""``data-platform-mcp`` developer CLI (aliased as ``data-platform``).

One console command, installed with the package, with three subcommands:

* ``init``  — scaffolds the Claude Code / MCP config into a Glue job repo. It is
  deliberately *not* an MCP tool: the server talks to AWS and must stay thin;
  writing local project files is a one-off bootstrap that belongs in a plain CLI
  (like ``git init``), available the moment the package is installed — before
  the repo has any Claude config to expose a command from. It is idempotent and
  never overwrites: it only creates missing files, safe to re-run for new
  templates.
* ``list``  — prints everything the toolkit exposes (CLI, MCP tools, assets).
* ``serve`` — starts the stdio MCP server (what ``.mcp.json`` invokes).

Everything here is cross-platform (Windows and Linux): paths go through
``pathlib``/``importlib.resources`` and every file read/write pins
``encoding="utf-8"``, so it does not depend on the OS default code page.
"""

from __future__ import annotations

import argparse
import sys
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path

# (template path within the package, destination path in the target repo)
_FILES: tuple[tuple[str, str], ...] = (
    ("CLAUDE.md", "CLAUDE.md"),
    ("mcp.json", ".mcp.json"),
    ("dot_claude/agents/job-validator.md", ".claude/agents/job-validator.md"),
    ("dot_claude/skills/validar-job/SKILL.md", ".claude/skills/validar-job/SKILL.md"),
    ("dot_claude/commands/validar-job.md", ".claude/commands/validar-job.md"),
    ("dot_claude/agents/job-diagnoser.md", ".claude/agents/job-diagnoser.md"),
    (
        "dot_claude/skills/analyze-job-run/SKILL.md",
        ".claude/skills/analyze-job-run/SKILL.md",
    ),
    (
        "dot_claude/skills/analyze-job-run/reference/glue-errors.md",
        ".claude/skills/analyze-job-run/reference/glue-errors.md",
    ),
    ("dot_claude/commands/analyze-job-run.md", ".claude/commands/analyze-job-run.md"),
    (
        "dot_claude/skills/testes-unitarios/SKILL.md",
        ".claude/skills/testes-unitarios/SKILL.md",
    ),
    ("dot_claude/commands/testes-unitarios.md", ".claude/commands/testes-unitarios.md"),
    (
        "dot_claude/skills/code-review/SKILL.md",
        ".claude/skills/code-review/SKILL.md",
    ),
    (
        "dot_claude/skills/code-review/reference/rubric.md",
        ".claude/skills/code-review/reference/rubric.md",
    ),
    ("dot_claude/commands/code-review.md", ".claude/commands/code-review.md"),
)

# Static description of what this toolkit ("sdk") exposes, for `data-platform
# list`. CLI commands and scaffolded assets are declared here; MCP tools are
# introspected live from the server so the listing never drifts from reality.
_CLI_COMMANDS: tuple[tuple[str, str], ...] = (
    ("init", "Cria a config do Claude Code / MCP neste repo (idempotente)."),
    ("list", "Lista tudo que este toolkit expõe (comandos, tools, assets)."),
    ("serve", "Sobe o servidor MCP (stdio) — o que o .mcp.json chama."),
)

_SCAFFOLDED_ASSETS: tuple[tuple[str, str, str], ...] = (
    ("skill", "validar-job", "Playbook do fluxo inspecionar→replicar→validar."),
    ("skill", "analyze-job-run", "Playbook de diagnóstico de run falhado."),
    ("agent", "job-validator", "Subagente que valida um job de ponta a ponta."),
    ("agent", "job-diagnoser", "Subagente que investiga e diagnostica um run."),
    ("command", "/validar-job <job>", "Dispara o fluxo de validação manualmente."),
    ("command", "/analyze-job-run <job> <run>", "Dispara o diagnóstico de falha."),
    ("skill", "testes-unitarios", "Casca: roda a suíte de testes (troque pelo padrão da empresa)."),
    ("command", "/testes-unitarios [path]", "Roda os testes unitários do repo."),
    ("skill", "code-review", "Parecer de risco de um job antes de subir p/ produção."),
    ("command", "/code-review [job|base]", "Revisa a mudança de um job pré-produção."),
)


def _template_root() -> Traversable:
    return resources.files("dataplatform") / "templates"


def _read_template(rel: str) -> str:
    node = _template_root()
    for part in rel.split("/"):
        node = node / part
    return node.read_text(encoding="utf-8")


def init(target: Path, force: bool = False) -> int:
    root = _template_root()
    created: list[str] = []
    skipped: list[str] = []

    for src_rel, dest_rel in _FILES:
        dest = target / dest_rel
        if dest.exists() and not force:
            skipped.append(dest_rel)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(_read_template(src_rel), encoding="utf-8")
        created.append(dest_rel)

    for path in created:
        print(f"  criado   {path}")
    for path in skipped:
        print(f"  mantido  {path} (já existe; use --force para sobrescrever)")

    if not created:
        print("\nNada a criar — o repo já está configurado.")
    else:
        print(
            "\nPronto. Agora exporte AWS_PROFILE e DATAPLATFORM_SANDBOX_ACCOUNTS "
            "e abra o Claude Code neste repo."
        )
    _ = root  # keep the resource handle alive for the loop above
    return 0


def _mcp_tools() -> list[tuple[str, str]]:
    """Introspect the MCP server for its tool names + one-line summaries.

    Returns an empty list (with a hint printed by the caller) when the ``mcp``
    extra isn't installed, so the base install still runs ``list`` cleanly.
    """
    try:
        import asyncio

        from dataplatform.mcp.server import mcp
    except ImportError:
        return []

    async def _collect() -> list[tuple[str, str]]:
        tools = await mcp.list_tools()
        out: list[tuple[str, str]] = []
        for tool in tools:
            summary = (getattr(tool, "description", "") or "").strip().splitlines()
            out.append((tool.name, summary[0] if summary else ""))
        return sorted(out)

    return asyncio.run(_collect())


def serve() -> int:
    """Start the stdio MCP server. Requires the ``[mcp]`` extra."""
    try:
        from dataplatform.mcp.server import main as serve_main
    except ImportError:
        print(
            "O servidor MCP precisa do extra [mcp]. Instale com:\n"
            "  pip install 'data-platform-mcp[mcp]'",
            file=sys.stderr,
        )
        return 1
    serve_main()
    return 0


def list_all() -> int:
    print("data-platform-mcp — comandos de CLI:\n")
    for name, desc in _CLI_COMMANDS:
        print(f"  data-platform-mcp {name:6}  {desc}")

    print("\nTools do MCP (server 'data-platform'):\n")
    tools = _mcp_tools()
    if tools:
        for name, desc in tools:
            print(f"  {name:26} {desc}")
    else:
        print("  (instale o extra [mcp] para listar as tools: pip install '.[mcp]')")

    print("\nAssets criados por 'data-platform init' (usados no Claude Code):\n")
    for kind, name, desc in _SCAFFOLDED_ASSETS:
        print(f"  {kind:8} {name:20} {desc}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="data-platform")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser(
        "init", help="Cria a config do Claude Code / MCP neste repo (se faltar)."
    )
    p_init.add_argument(
        "path", nargs="?", default=".", help="Diretório do repo (padrão: atual)."
    )
    p_init.add_argument(
        "--force", action="store_true", help="Sobrescreve arquivos existentes."
    )

    sub.add_parser("list", help="Lista comandos de CLI, tools do MCP e assets do repo.")
    sub.add_parser("serve", help="Sobe o servidor MCP (stdio); usado pelo .mcp.json.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "init":
        return init(Path(args.path).resolve(), force=args.force)
    if args.command == "list":
        return list_all()
    if args.command == "serve":
        return serve()
    return 1


if __name__ == "__main__":
    sys.exit(main())
