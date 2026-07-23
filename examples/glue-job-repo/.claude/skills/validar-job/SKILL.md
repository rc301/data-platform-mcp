---
name: validar-job
description: >-
  Replica um Glue job de produção para a conta sandbox e valida a alteração
  rodando na sandbox. Use ao mexer no script ou na config de um job em
  jobs/<nome>/ e precisar confirmar que ainda roda antes de abrir PR.
---

# Validar uma alteração de Glue job

Playbook para exercitar uma mudança com segurança. As **ferramentas** vêm do
MCP `data-platform`; este documento é o **conhecimento estático** de como
encadeá-las (o que, por definição, não vira tool).

## Quando usar

- Alterou `jobs/<nome>/script.py` ou `job.json` e quer validar antes do PR.
- Precisa reproduzir na sandbox um comportamento visto em produção.

## Quando NÃO usar

- Só leu código, não alterou nada → não há o que validar.
- Quer rodar em produção → **proibido**; este fluxo é sandbox-only.

## Passos

1. **Descobrir/inspecionar.** `list_glue_jobs` para achar o nome exato, depois
   `inspect_glue_job` para ver a config de produção que será replicada.
2. **Replicar para sandbox.** `replicate_job_to_sandbox` com o `sandbox_profile`
   do dev. Convenção: `target_job_name = "<nome>-sandbox"`. Use
   `role_override` / `script_location_override` se a sandbox usa role ou bucket
   próprios.
3. **Validar estaticamente.** `validate_sandbox_job` — confirma campos
   obrigatórios e script location antes de gastar um run.
4. **Rodar.** `run_sandbox_job` e guarde o `run_id`.
5. **Acompanhar.** `get_sandbox_run_status` até sair de `RUNNING`. Se
   `FAILED`, use `get_run_logs` (quando disponível) para diagnosticar.
6. **Reportar** ao dev: sucesso/falha, tempo de execução e, em falha, a causa
   provável tirada do log — sem aplicar correção sem pedir.

## Regras

- Escrita só em conta sandbox; nunca contorne com `aws` na mão.
- Não invente `run_id`; sempre use o retornado por `run_sandbox_job`.
- Não faça busy-loop no status — intervale as consultas.
