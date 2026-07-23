# glue-job-repo (exemplo)

Repositório de exemplo mostrando como usar o `data-platform-mcp` com Claude
Code num repo de Glue jobs. **Referência** — copie a estrutura para o seu repo
real.

## Estrutura

```
.
├── CLAUDE.md                       # contexto e regras carregados pelo Claude
├── .mcp.json                       # registra o server MCP data-platform
├── .claude/
│   ├── agents/                     # job-validator, job-diagnoser (subagentes)
│   ├── commands/                   # /validar-job, /analyze-job-run
│   └── skills/                     # validar-job, analyze-job-run (+ reference/)
├── jobs/orders_etl/
│   ├── script.py                   # código do Glue job (transform testável)
│   └── job.json                    # config do job (placeholders, sem segredo)
└── tests/test_transform.py         # testa a regra pura, sem AWS
```

- **`.mcp.json`** = as *tools* (o que muda entre execuções).
- **`.claude/skills`** = o *playbook* e o conhecimento estático.
- **`.claude/agents`** = quem orquestra tools + skill de forma autônoma.

## Setup

Pré-requisito: `pip install "data-platform-mcp[mcp]"` (o binário
`data-platform-mcp` precisa estar no PATH).

Gere os arquivos de config neste repo com:

```bash
data-platform init
```

Depois exporte suas credenciais (nunca vão para o Git):

```bash
export AWS_PROFILE=seu-profile-dev
export DATAPLATFORM_SANDBOX_ACCOUNTS=111122223333
```

Abra o Claude Code no repo e peça: *"valida o orders_etl na sandbox"*.

## Testes

```bash
pytest tests/
```
