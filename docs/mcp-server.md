# Servidor MCP e referência de tools

O servidor MCP `data-platform` expõe a biblioteca a agentes de IA. Ele é uma
**casca fina**: cada tool importa e delega para uma função pública de
`dataplatform.glue.*`. Toda a lógica (chamadas AWS, guardas, formatação) mora na
lib; o `server.py` só liga funções a tools e escreve as docstrings que o modelo
lê. Isso mantém a mesma lógica reutilizável por code-execution no futuro (ver
[architecture.md](architecture.md)).

- **Transporte:** stdio. Sobe com `data-platform-mcp serve`.
- **Extra necessário:** `[mcp]` (`fastmcp`). Nunca é importado por um Glue job em
  runtime — é dev-only.
- **Nome do servidor:** `data-platform` (registrado no `.mcp.json`).

## Contas e credenciais

Todas as tools usam a **credencial do próprio desenvolvedor** (`AWS_PROFILE` /
cadeia padrão AWS). Não há service account. As tools do MCP são **somente-leitura**
e operam sobre dois papéis de conta:

- **Conta do job (dev):** profile ambiente. Leitura de jobs/runs e diagnóstico.
- **Conta de dados (terceira):** passada como `data_profile`. Leitura read-only
  de schema/partição de tabelas de origem.

As funções de **escrita** (guardadas, sandbox-only) continuam na biblioteca
(`glue.replicate_to_sandbox`, `start_validation_run`, …) mas **não** são expostas
como tools neste build — ver [security.md](security.md).

## Referência das tools

| Tool | Tipo | Conta | O que faz |
|---|---|---|---|
| `get_server_info` | read | dev | Versão do toolkit + identidade AWS resolvida. Chame 1× por sessão. |
| `list_glue_jobs` | read | dev | Lista jobs (filtro por substring). Para achar o nome exato. |
| `inspect_glue_job` | read | dev | Config portável completa de um job (command, args, role, worker). |
| `diagnose_job_run` | read | dev | Diagnóstico de 1 run num único call: resumo (BRT, DPU, workers) + histórico + excerto de erro (se falhou). |
| `list_job_runs` | read | dev | Histórico recente de runs (primitivo reutilizável). |
| `inspect_table` | read | dados | Schema + detecção de Iceberg de uma tabela de origem. |
| `check_partitions` | read | dados | Se uma partição do catálogo existe. Recusa Iceberg. |

### `diagnose_job_run` é uma tool de "altitude de workflow"

Ela empacota o que você precisa para começar a diagnosticar uma falha (resumo +
histórico + excerto de erro) num único call de alto sinal, em vez de vários reads
de baixo nível. Ainda assim, a lógica vive na lib (`glue.diagnose_job_run`), não
no server — é a exceção que confirma a regra do "casca fina". Detalhe da regra de
decisão em [architecture.md](architecture.md).

## Por que não há tool `code_review_job` ou `generate_docs`

Porque isso é **composição**, não capacidade nova. Um comando de review compõe
`inspect_glue_job` + `list_job_runs` + `inspect_table` etc.; a rubrica de review
é conhecimento estático que vive numa skill. Só vira tool nova o que **muda entre
execuções** e que **mais de um comando** usaria. Ver o mapa de reuso em
[architecture.md](architecture.md) e o guia de comandos em [commands.md](commands.md).
