# Catálogo de erros de Glue

Referência de troubleshooting: assinatura no log → causa provável → o que
checar. Carregada sob demanda pela skill `analyze-job-run`. Complemente com
casos reais do seu ambiente.

## Dados / catálogo

| Assinatura no log | Causa provável | Próximo passo |
|---|---|---|
| `AnalysisException: Table or view not found` | Tabela não existe no catálogo / database errado | `inspect_table` |
| `Path does not exist: s3://...` | Partição/prefixo origem vazio ou ainda não escrito | `check_partitions` |
| `cannot resolve '...' given input columns` | Schema drift (coluna renomeada/removida) | `inspect_table`, comparar com o script |
| `HIVE_PARTITION_SCHEMA_MISMATCH` | Schema da partição diverge do da tabela | `inspect_table` |
| Leitura retorna 0 linhas, sem erro | Filtro de partição sem match | `check_partitions` com o predicado do job |

## Recursos / capacidade

| Assinatura no log | Causa provável | Próximo passo |
|---|---|---|
| `java.lang.OutOfMemoryError` / `Container killed` | Memória insuficiente / skew de dados | Ver workers e DPU no summary; comparar com `recent_runs` |
| `ExecutorLostFailure` | Executor perdido (OOM ou spot) | Aumentar workers ou worker type |
| `Job ... exceeded the timeout` | Timeout baixo ou volume cresceu | Ver duração vs `recent_runs`; ajustar Timeout |

## Permissão / configuração

| Assinatura no log | Causa provável | Próximo passo |
|---|---|---|
| `AccessDenied` / `not authorized to perform` | IAM/Lake Formation faltando na conta de dados | Validar acesso do `data_profile` à tabela |
| `EntityNotFoundException` | Job/database/tabela inexistente no ambiente | Conferir conta/region no `get_server_info` |
| `Py4JJavaError` genérico | Erro no Spark; a causa real está no `Caused by:` | Procurar `Caused by` no excerto |

## Iceberg

Se `inspect_table` retornar `table_format: iceberg`, `check_partitions` recusa
de propósito: partições Iceberg não estão no Glue Data Catalog. Verifique via
metadados Iceberg ou Athena `SELECT * FROM db."tabela$partitions"` — fora do
escopo automatizado por ora.
