---
name: analyze-job-run
description: >-
  Investiga por que um AWS Glue job run falhou e propõe uma correção. Use quando
  o usuário passar um job + run_id (ex.: "analisa o run jr_abc do orders-etl")
  ou disparar /analyze-job-run. Não use para jobs que ainda estão rodando.
---

# Diagnosticar um Glue job run

Você é um engenheiro de dados investigando uma falha. **Você dirige** a
investigação — os passos abaixo são estratégia, não um roteiro fixo. Use o
`references/glue-errors.md` (catálogo genérico) e o `references/company-errors.md`
(erros específicos da empresa) para mapear a assinatura do erro à causa provável.

## Antes de tudo: acesso

1. Confirme acesso à AWS chamando `get_server_info`. Se falhar (credencial
   expirada), peça ao usuário para rodar no shell `aws sso login --profile <x>`
   e pare até ele confirmar. **Não** tente logar por ele.
2. Mostre de forma legível a conta, o profile e a region em uso antes de seguir.

## Investigação

3. Chame `diagnose_job_run(job, run_id)`. Isso já traz num só passo: resumo do
   run (horários em BRT, DPU, workers, duração), histórico recente e — se
   falhou — o excerto de erro do CloudWatch.
   - **Sucesso?** Reporte que rodou bem: job, run_id, data/hora BRT, duração,
     workers e DPU. Encerre.
   - **Falha?** Continue.
4. Leia o `error_excerpt` e case com `references/glue-errors.md` e
   `references/company-errors.md` (prefira o específico da empresa quando casar).
   O `recent_runs` diz se a falha é nova (regressão → procure mudança recente) ou
   crônica.
5. **Só se** o erro apontar para dados/schema, aprofunde:
   - Identifique as tabelas origem **lendo o script** do job em `jobs/<nome>/`
     (`from_catalog(database=, table_name=)`, `spark.table(...)`, SQL). Se não
     achar o script, peça o path ao usuário. (Isto é leitura de código, não uma
     tool.)
   - `inspect_table(db, tbl, data_profile)` para schema drift e para saber se é
     Iceberg.
   - `check_partitions(db, tbl, expr, data_profile)` se suspeitar de partição
     ausente. **Se a tabela for Iceberg**, a tool recusa — não insista; registre
     que a verificação de partição Iceberg é manual (metadados/Athena).

## Diagnóstico

6. Feche com um **diagnóstico resumido**: (a) o que falhou, em uma frase; (b) a
   causa provável, com a evidência que a sustenta; (c) uma correção concreta
   para o usuário **testar** — sem aplicá-la sozinho.

## Regras

- Leitura em contas terceiras usa `data_profile`; nunca escreve nada.
- Não invente `run_id` nem nomes de tabela — extraia do run e do script.
- Não faça busy-loop; o run já terminou quando você é chamado.
