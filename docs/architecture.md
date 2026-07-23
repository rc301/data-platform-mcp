# Arquitetura: tools compartilhadas, comandos que compõem

Esta solução não é "um MCP para diagnosticar job". É uma **plataforma** sobre a
qual o engenheiro de dados executa vários comandos distintos no repositório de
Glue jobs. O princípio central:

> **Tools são a camada de capacidade compartilhada. Comandos e skills são
> composição.** Uma tool não pertence a um comando — ela existe para qualquer
> comando/skill usar quando precisar.

## As quatro camadas

| Camada | O que é | Onde vive | Muda entre execuções? |
|---|---|---|---|
| **Tools (MCP)** | Primitivos reutilizáveis sobre a plataforma (Glue, catálogo, CloudWatch) | `dataplatform/glue/*` + `mcp/server.py` | Sim — é o critério para virar tool |
| **Skills** | Playbooks + conhecimento estático (padrões, rubricas, catálogos de erro) | `.claude/skills/*` | Não — conhecimento fixo |
| **Comandos** | Entradas manuais do engenheiro (`/x`) | `.claude/commands/*` | — |
| **Subagentes** | Execução isolada para não poluir o contexto | `.claude/agents/*` | — |

Regra de ouro: **conhecimento estático nunca vira tool** (vai em skill); **só o
que muda entre execuções vira tool**; **comandos não têm lógica própria** — eles
acionam uma skill que compõe tools.

## Mapa de reuso (tools × comandos)

Mostra que os primitivos (tools somente-leitura do MCP) servem a vários comandos
— inclusive os que ainda não foram implementados (marcados _planejado_):

| Tool | analyze-job-run | code-review | gerar-docs _(plan.)_ |
|---|:-:|:-:|:-:|
| `get_server_info` | ✔ | ✔ | ✔ |
| `list_glue_jobs` | ✔ | ✔ | ✔ |
| `inspect_glue_job` | | ✔ | ✔ |
| `list_job_runs` | ✔ | ✔ | ✔ |
| `diagnose_job_run` | ✔ | ✔ | |
| `inspect_table` | ✔ | ✔ | ✔ |
| `check_partitions` | ✔ | ✔ | |

Nenhum comando ganha uma tool `code_review_job` ou `generate_docs`: esses são
**skills** que compõem os primitivos acima. A rubrica de review e o padrão de
doc são **conhecimento estático** → arquivos de referência da skill.

> O toolkit é somente-leitura: não há operações de escrita (nem como tools do
> MCP, nem na biblioteca).

## Como adicionar um comando novo

1. **Escreva a skill** em `.claude/skills/<nome>/SKILL.md` — a estratégia + o
   conhecimento estático (rubrica, padrão de doc, passos de migração) em
   `reference/`. A skill compõe as tools existentes.
2. **Adicione o slash command** em `.claude/commands/<nome>.md` apontando para a
   skill (com `$ARGUMENTS`).
3. **(Opcional) um subagente** se o trabalho for barulhento e valer isolar.
4. **Registre no scaffolder** (`dataplatform/cli.py`, `_FILES` e
   `_SCAFFOLDED_ASSETS`) para o `data-platform init` distribuir.
5. **Só crie uma tool nova** se aparecer uma **capacidade nova reutilizável**
   (uma interação com AWS que muda entre runs e que mais de um comando usaria).
   Caso contrário, componha as que já existem. Não crie tool especulativa para
   um único comando.

## Quando promover algo a tool (regra de decisão)

```
É conhecimento fixo (schema, rubrica, convenção)?  → skill/reference, não tool.
Muda entre execuções E ≥1 comando usaria?          → tool primitiva.
É a composição de vários primitivos p/ um fluxo?   → skill (ou, no futuro,
                                                      code-execution).
É a mesma composição em um caminho muito quente?   → pode virar 1 tool de
                                                      workflow (ex.:
                                                      diagnose_job_run), com a
                                                      lógica na lib, não no server.
```

## Futuro: code-execution como substrato de composição

Compor muitos primitivos via chamadas de tool discretas custa contexto (uma
definição + um resultado por round-trip). O destino é **code-execution sobre
MCP**: o agente escreve código que encadeia os primitivos e devolve só o
destilado, mantendo dados intermediários fora da janela. Está fora do MVP, mas
os primitivos já são funções de lib puras (`dataplatform.glue.*`) — prontas para
serem chamadas por código, não só por tool. Por isso a lógica mora na lib e o
`server.py` é casca fina: a mesma lib serve tools hoje e code-execution amanhã.
