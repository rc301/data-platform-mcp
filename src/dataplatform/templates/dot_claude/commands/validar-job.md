---
description: Valida uma alteração de Glue job replicando para a sandbox e rodando.
argument-hint: <nome-do-job>
---

Valide o Glue job `$ARGUMENTS` seguindo a skill `validar-job`.

Passos obrigatórios, nesta ordem:

1. `inspect_glue_job` para ver a config de produção.
2. `replicate_job_to_sandbox` para `$ARGUMENTS-sandbox` no profile de sandbox.
3. `validate_sandbox_job` (validação estática).
4. `run_sandbox_job` e acompanhe com `get_sandbox_run_status`.
5. Reporte: sucesso/falha, tempo de execução e, em falha, a causa provável.

Regras: escrita só em conta sandbox; não invente `run_id`; não faça busy-loop
no status; diagnostique a falha mas **não** aplique correção sem eu pedir.

Se `$ARGUMENTS` estiver vazio, primeiro rode `list_glue_jobs` e me pergunte
qual job validar.
