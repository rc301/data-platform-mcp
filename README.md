# data-platform-mcp

A small, developer-facing toolkit for working with AWS Glue data jobs, plus an
MCP server that exposes it to AI agents (e.g. Claude Code).

It gives an agent a **read-only** window onto AWS Glue: inspect job configs,
diagnose failed runs, and check source tables — the substrate for commands like
failure diagnosis and pre-production code review.

The MCP server is a **thin shell**. All logic lives in the library
(`dataplatform.glue`); the server only wires those functions to tools and
writes the docstrings the model reads. The `mcp` extra is **dev-only** and is
never imported by a Glue job at runtime.

## Design principles

- **Only expose what changes between runs.** Static knowledge (schemas,
  framework conventions) stays in docs, not in tools.
- **Developer credentials only.** Everything uses the ambient `AWS_PROFILE` —
  no service accounts.
- **Read-only.** The toolkit never mutates AWS — there are no write operations,
  in the tools or the library.

## Install

```bash
# library only (what a job environment would use)
pip install .

# with the MCP server (dev machines)
pip install ".[mcp]"

# contributors
pip install -e ".[mcp,dev]"
```

## Configure

```bash
export AWS_PROFILE=your-dev-profile
```

## Tools

| Tool | Kind | Purpose |
|------|------|---------|
| `get_server_info` | read | Library version + resolved AWS identity |
| `list_glue_jobs` | read | Discover job names |
| `inspect_glue_job` | read | Full portable config of one job |
| `list_job_runs` | read | Recent run history (reusable primitive) |
| `diagnose_job_run` | read | One-call diagnosis of a run (summary + history + error excerpt) |
| `inspect_table` | read (data acct) | Source table schema + Iceberg detection |
| `check_partitions` | read (data acct) | Whether a catalog partition exists (refuses Iceberg) |

The read tools split across accounts: run diagnostics use the dev's
`AWS_PROFILE`; `inspect_table` / `check_partitions` take a `data_profile` that
resolves to the (third) account holding the source tables. `diagnose_job_run` is
workflow-altitude by design — it bundles what you need to start diagnosing a
failure in a single high-signal call rather than several low-level reads.

The tools are a **shared capability layer**: commands and skills compose them,
so a new command (code-review, doc generation, template migration…) is usually a
new skill + slash command over the *existing* tools, not a new tool. See
[`docs/architecture.md`](docs/architecture.md) for the reuse map and the recipe
for adding commands.

## Scaffold a Glue job repo

Inside an existing Glue job repository, generate the Claude Code / MCP config
(idempotent — only creates what's missing, never overwrites):

```bash
data-platform-mcp init
```

This writes `CLAUDE.md`, `.mcp.json` and `.claude/{agents,skills,commands}/...`.
A full worked example lives in
[`examples/glue-job-repo`](examples/glue-job-repo).

Discover everything the toolkit exposes — CLI commands, live MCP tools, and the
scaffolded skill/agent/slash-command:

```bash
data-platform-mcp list
```

> The command is named after the package. `data-platform` is a shorter alias
> for the exact same dispatcher, so `data-platform init` also works.

## Use with Claude Code

Add to your MCP config (`~/.claude/mcp.json` or project `.mcp.json`):

```json
{
  "mcpServers": {
    "data-platform": {
      "command": "data-platform-mcp",
      "args": ["serve"],
      "env": {
        "AWS_PROFILE": "your-dev-profile"
      }
    }
  }
}
```

Then in a session: *"list glue jobs matching orders, inspect the ETL one, and
diagnose its last failed run."*

## Documentation

Full docs live in [`docs/`](docs/) — start at the
[documentation index](docs/README.md):

- [getting-started](docs/getting-started.md) — install → configure → `init` → first session
- [cli](docs/cli.md) — the `data-platform-mcp` command (`init` / `list` / `serve`)
- [configuration](docs/configuration.md) — env vars, profiles, region
- [mcp-server](docs/mcp-server.md) — the thin-shell server + full tool reference
- [commands](docs/commands.md) — the command catalog and how to add one
- [architecture](docs/architecture.md) — the four layers + tool/command reuse map
- [security](docs/security.md) — the read-only guarantee and secrets hygiene
- [company-adaptation](docs/company-adaptation.md) — the `TODO(empresa)` checklist

## Test locally, without AWS

Everything can be exercised offline against a fake AWS (Glue + CloudWatch) — no
credentials, no network, no account. One command:

```bash
python simulate.py
```

It runs lint → types → tests → diagnosis evals → an end-to-end simulation of
every tool, and exits non-zero if anything fails. You can also point Claude Code
at a fake MCP server to run `/analyze-job-run` fully offline — see
[`simulation/README.md`](simulation/README.md).

## Develop

```bash
pytest
ruff check .
mypy
```

## License

MIT
