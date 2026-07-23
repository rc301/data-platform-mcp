---
description: Revisa a alteração de um Glue job antes de subir para produção.
argument-hint: [job-name | branch-base]
---

Faça o code review da mudança seguindo a skill `code-review`. Alvo/base
(opcional): `$ARGUMENTS`

Em resumo:

1. Delimite o diff e os jobs tocados em `jobs/<nome>/`.
2. `inspect_glue_job` + `list_job_runs` para contrastar com produção e histórico.
3. Se tocar origem, `inspect_table` / `check_partitions` no `data_profile`.
4. Aplique `reference/rubric.md` ao script e ao `job.json`.
5. Dê o parecer: veredito, achados (severidade + arquivo:linha + correção) e um
   checklist "antes de subir". Read-only — não edite, não replique, não rode.
