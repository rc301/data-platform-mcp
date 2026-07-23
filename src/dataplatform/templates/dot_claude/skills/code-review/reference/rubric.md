# Rubrica de code review — Glue jobs

Conhecimento estático carregado sob demanda pela skill `code-review`. É o "o que
olhar" — complemente com os padrões da sua empresa. Severidades: **bloqueador**
(não sobe), **atenção** (sobe com ressalva), **nit** (opcional).

## Script (`jobs/<nome>/script.py`)

| Olhe por | Severidade | Por quê |
|---|---|---|
| Lógica de transformação em função pura, testável sem AWS | atenção | Sem isso não há teste unitário confiável |
| Credencial/ARN/ID de conta hardcoded | bloqueador | Segredo em git; use argumentos/env |
| Caminho S3 ou nome de tabela fixo por ambiente | bloqueador | Quebra entre sandbox e produção; parametrize |
| Escrita sem partição/modo definido (overwrite vs append) | atenção | Risco de sobrescrever dado |
| `collect()` / `toPandas()` em volume grande | atenção | Estoura memória do driver |
| Falha silenciosa (except amplo, log ausente) | atenção | Dificulta o `analyze-job-run` depois |

## Config (`job.json`)

| Olhe por | Severidade | Por quê |
|---|---|---|
| Placeholders (`<ACCOUNT_ID>`, role, bucket) não resolvidos | bloqueador | Job não sobe / sobe apontando errado |
| Worker/DPU muito acima do histórico do job | atenção | Custo; confronte com `list_job_runs` |
| `Timeout` incompatível com a duração típica | atenção | Timeout curto derruba run bom; longo mascara travada |
| `--job-bookmark-option` coerente com a intenção | atenção | Reprocessa ou pula dado sem querer |
| `Connections` que só existem em produção | atenção | `validar-job` na sandbox vai falhar sem override |
| Mudança de `GlueVersion` | bloqueador | Pode quebrar API do Spark; exige validar-job |

## Dados / origem (se o diff tocar entrada)

- Schema do script bate com `inspect_table`? Coluna renomeada/removida = risco de
  `cannot resolve`.
- Tabela é Iceberg? `check_partitions` não vale; confirme partição por outro meio.
- A partição que o job espera existe? (`check_partitions` no `data_profile`.)

## Cruzando com produção

- O job vinha **estável** (`list_job_runs`)? Mudança em job frágil pede mais rigor.
- A mudança foi **exercitada** na sandbox (`validar-job`) antes deste review? Se
  não, o checklist "antes de subir" deve exigir.
