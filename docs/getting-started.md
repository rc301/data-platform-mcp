# Getting started

Do zero até uma sessão do Claude Code funcionando num repositório de Glue jobs.

## Pré-requisitos

- **Python ≥ 3.11** (testado em 3.11, 3.12 e 3.13).
- **Credenciais AWS do próprio desenvolvedor** — um named profile por conta (ver
  [configuration.md](configuration.md)). Não há service account.
- **Claude Code** instalado, se for usar o servidor MCP.

Funciona igual em **Windows** e **Linux (RHEL 9)**: todos os caminhos passam por
`pathlib`/`importlib.resources` e toda leitura/escrita de arquivo fixa
`encoding="utf-8"`, então nada depende do code page padrão do sistema.

## 1. Instalar

```bash
# só a biblioteca (o que um ambiente de job usaria)
pip install .

# com o servidor MCP (máquina de dev)
pip install ".[mcp]"

# contribuidores (libs de dev: pytest, ruff, mypy)
pip install -e ".[mcp,dev]"
```

Isso instala o comando de console `data-platform-mcp` (e o alias curto
`data-platform`). Confirme que está no `PATH`:

```bash
data-platform-mcp list
```

> **Windows:** o pip cria `data-platform-mcp.exe` em `...\Scripts\`. Se o comando
> não for encontrado, garanta que a pasta `Scripts` do seu Python/venv está no
> `PATH`.

## 2. Configurar o ambiente

```bash
# Linux / macOS
export AWS_PROFILE=meu-profile-dev
export DATAPLATFORM_SANDBOX_ACCOUNTS=111122223333,444455556666
```

```powershell
# Windows (PowerShell)
$env:AWS_PROFILE = "meu-profile-dev"
$env:DATAPLATFORM_SANDBOX_ACCOUNTS = "111122223333,444455556666"
```

`DATAPLATFORM_SANDBOX_ACCOUNTS` é a **lista de contas onde escrita é permitida**.
Sem ela, toda operação de escrita é recusada (fail-closed). Detalhes em
[security.md](security.md). Região: se o profile não define uma, cai para
`sa-east-1` — ver [configuration.md](configuration.md).

## 3. Scaffold no repositório de jobs

Dentro de um repo de Glue jobs existente:

```bash
cd ~/meu-gluejob-repo/
data-platform-mcp init
```

`init` é **idempotente** e nunca sobrescreve: cria só o que falta, então é seguro
re-rodar para pegar templates novos (use `--force` para sobrescrever). Ele grava:

```
CLAUDE.md                     # contexto e regras do repo para o Claude Code
.mcp.json                     # registra o servidor MCP 'data-platform'
.claude/agents/               # subagentes (job-validator, job-diagnoser)
.claude/skills/               # playbooks (validar-job, analyze-job-run, ...)
.claude/commands/             # slash commands (/validar-job, ...)
```

Detalhes de cada comando da CLI em [cli.md](cli.md).

## 4. Abrir o Claude Code

Abra o Claude Code na raiz do repo. O `.mcp.json` gerado sobe o servidor MCP com
`data-platform-mcp serve`, e o `CLAUDE.md` carrega o contexto do repo. A partir
daí você usa o catálogo de comandos ([commands.md](commands.md)):

- `/validar-job <job>` — inspeciona → replica na sandbox → roda e valida.
- `/analyze-job-run <job> <run>` — diagnostica um run que falhou.
- `/code-review [job|base]` — parecer de risco antes de subir para produção.
- `/testes-unitarios [path]` — roda a suíte de testes puros do repo.

## Estrutura de um repo de jobs

```
meu-gluejob-repo/
├── jobs/
│   └── orders_etl/
│       ├── job.json        # config do job (role, worker, argumentos) — placeholders
│       └── script.py       # código que roda no Glue
├── tests/                  # testes de transformação pura, sem AWS
├── CLAUDE.md               # (gerado)
├── .mcp.json               # (gerado)
└── .claude/                # (gerado)
```

Um exemplo completo vive em
[`examples/glue-job-repo`](../examples/glue-job-repo).

## Solução de problemas

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `data-platform-mcp: command not found` | pasta de scripts fora do `PATH` | Ative o venv ou adicione `.../Scripts` (Win) / `.../bin` (Linux) ao `PATH`. |
| `O servidor MCP precisa do extra [mcp]` | instalou sem `[mcp]` | `pip install ".[mcp]"`. |
| Escrita recusada (`SandboxViolation`) | `DATAPLATFORM_SANDBOX_ACCOUNTS` vazio ou conta errada | Configure a variável com a conta sandbox correta ([security.md](security.md)). |
| Clients Glue/Logs sem região | profile sem região | Defina `AWS_REGION` ou confie no fallback `sa-east-1` ([configuration.md](configuration.md)). |
