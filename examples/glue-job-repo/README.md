# glue-job-repo (exemplo)

Repositório de exemplo mostrando como um repo de Glue jobs se organiza para usar
o `data-platform-mcp` com Claude Code. Aqui ficam **só os arquivos próprios do
repo** (os jobs e seus testes). A configuração do Claude Code / MCP
(`CLAUDE.md`, `.mcp.json`, `.claude/…`) **não** é versionada aqui de propósito:
ela é gerada por `data-platform init`, cuja fonte única de verdade são os
templates do toolkit. Assim o exemplo nunca fica defasado em relação a eles.

## Estrutura

```
.
├── jobs/orders_etl/
│   ├── script.py                   # código do Glue job (transform testável)
│   └── job.json                    # config do job (placeholders, sem segredo)
└── tests/test_transform.py         # testa a regra pura, sem AWS
```

## Setup

Pré-requisito: `pip install "data-platform-mcp[mcp]"` (o binário
`data-platform-mcp` precisa estar no PATH).

Gere a config do Claude Code / MCP neste repo — isto cria `CLAUDE.md`,
`.mcp.json` e `.claude/{agents,skills,commands}/…`:

```bash
data-platform init
```

Veja o catálogo de comandos que passa a existir:

```bash
data-platform list
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
