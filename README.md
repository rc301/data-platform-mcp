# data-platform-mcp

A small, developer-facing toolkit for working with AWS Glue data jobs, plus an
MCP server that exposes it to AI agents (e.g. Claude Code).

It covers one workflow end to end:

> **inspect an existing job → replicate it into a sandbox → validate it**

The MCP server is a **thin shell**. All logic lives in the library
(`dataplatform.glue`); the server only wires those functions to tools and
writes the docstrings the model reads. The `mcp` extra is **dev-only** and is
never imported by a Glue job at runtime.

## Design principles

- **Only expose what changes between runs.** Static knowledge (schemas,
  framework conventions) stays in docs, not in tools.
- **Developer credentials only.** Everything uses the ambient `AWS_PROFILE` —
  no service accounts.
- **Writes are sandbox-only.** Mutating operations are refused unless the
  target account is listed in `DATAPLATFORM_SANDBOX_ACCOUNTS` (fails closed).

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
export DATAPLATFORM_SANDBOX_ACCOUNTS=111122223333,444455556666
```

## Tools

| Tool | Kind | Purpose |
|------|------|---------|
| `get_server_info` | read | Library version + resolved AWS identity |
| `list_glue_jobs` | read | Discover job names |
| `inspect_glue_job` | read | Full portable config of one job |
| `replicate_job_to_sandbox` | write (guarded) | Copy a job into a sandbox account |
| `validate_sandbox_job` | read | Static validation of a replicated job |
| `run_sandbox_job` | write (guarded) | Start a short validation run |
| `get_sandbox_run_status` | read | Poll a validation run |
| `diagnose_job_run` | read | One-call diagnosis of a run (summary + history + error excerpt) |
| `inspect_table` | read (data acct) | Source table schema + Iceberg detection |
| `check_partitions` | read (data acct) | Whether a catalog partition exists (refuses Iceberg) |

The read tools split across accounts: run diagnostics use the dev's
`AWS_PROFILE`; `inspect_table` / `check_partitions` take a `data_profile` that
resolves to the (third) account holding the source tables. `diagnose_job_run` is
workflow-altitude by design — it bundles what you need to start diagnosing a
failure in a single high-signal call rather than several low-level reads.

## Scaffold a Glue job repo

Inside an existing Glue job repository, generate the Claude Code / MCP config
(idempotent — only creates what's missing, never overwrites):

```bash
data-platform init
```

This writes `CLAUDE.md`, `.mcp.json` and `.claude/{agents,skills,commands}/...`.
A full worked example lives in
[`examples/glue-job-repo`](examples/glue-job-repo).

Discover everything the toolkit exposes — CLI commands, live MCP tools, and the
scaffolded skill/agent/slash-command:

```bash
data-platform list
```

## Use with Claude Code

Add to your MCP config (`~/.claude/mcp.json` or project `.mcp.json`):

```json
{
  "mcpServers": {
    "data-platform": {
      "command": "data-platform-mcp",
      "env": {
        "AWS_PROFILE": "your-dev-profile",
        "DATAPLATFORM_SANDBOX_ACCOUNTS": "111122223333"
      }
    }
  }
}
```

Then in a session: *"list glue jobs matching orders, inspect the ETL one, and
replicate it to my sandbox profile."*

## Develop

```bash
pytest
ruff check .
mypy
```

## License

MIT
