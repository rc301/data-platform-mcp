# Catálogo de erros da empresa

Este é o **seu** catálogo — preencha com as mensagens de erro que aparecem de
verdade no seu ambiente e como resolvê-las. A skill `analyze-job-run` carrega
este arquivo junto com o `glue-errors.md` (o catálogo genérico) ao casar a
assinatura de um erro.

Por que um arquivo separado: o `glue-errors.md` é atualizado pelo toolkit; este
aqui é seu e **não** é sobrescrito por `data-platform-mcp init --force`. Cure-o
com o tempo, a cada incidente novo.

## Como preencher

Uma linha por erro recorrente. Colunas:

- **Mensagem / assinatura no log** — o trecho estável que identifica o erro (sem
  IDs/timestamps variáveis). É o que casa com o `error_excerpt`.
- **Causa provável** — o que costuma estar por trás no seu ambiente.
- **Como solucionar** — a ação concreta (e qual tool ajuda a confirmar:
  `inspect_table`, `check_partitions`, `list_job_runs`, `get_server_info`).

Mantenha as mensagens genéricas — **nunca** cole nomes de conta, ARNs, buckets
ou dados reais aqui (este arquivo é versionado).

## Erros conhecidos

| Mensagem / assinatura no log | Causa provável | Como solucionar |
|---|---|---|
| _(exemplo)_ `Connection timed out to <host interno>` | Job na sandbox sem a `Connection`/VPC de produção | Rodar na conta certa, ou adicionar a Connection equivalente da sandbox |
| _(exemplo)_ `<mensagem específica do seu ETL>` | _(o que costuma causar)_ | _(a correção; tool que confirma)_ |

<!-- TODO(empresa): trocar as linhas de exemplo pelos erros reais do ambiente.
     Adicione uma seção nova (## ...) se quiser agrupar por domínio/job. -->
