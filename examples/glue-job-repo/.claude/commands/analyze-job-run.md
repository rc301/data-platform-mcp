---
description: Investiga por que um Glue job run falhou e propõe uma correção.
argument-hint: <job-name> <run-id>
---

Analise o Glue job run: `$ARGUMENTS`

Siga a skill `analyze-job-run`. Em resumo:

1. Confirme acesso à AWS (`get_server_info`); se a credencial expirou, peça
   `aws sso login` e pare.
2. `diagnose_job_run` com o job e run_id acima.
   - Sucesso → reporte job, run_id, data/hora BRT, duração, workers e DPU.
   - Falha → case o `error_excerpt` com `reference/glue-errors.md`; use
     `recent_runs` para ver se é regressão.
3. Se for dado/schema, leia o script em `jobs/` para achar as tabelas origem e
   use `inspect_table` / `check_partitions` no `data_profile`.
4. Feche com diagnóstico resumido: o que falhou, causa provável + evidência, e
   uma correção para eu testar (não aplique sozinho).

Se `$ARGUMENTS` não tiver job e run_id, me pergunte quais são.
