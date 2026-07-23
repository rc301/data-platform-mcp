# Adaptação para a empresa (`TODO(empresa)`)

O MVP roda com credenciais de dev e um caminho feliz. Para valer em produção na
empresa há pontos deliberados a ajustar, cada um ancorado no código com um
comentário `TODO(empresa) item N`. Descubra todos com:

```bash
grep -rn "TODO(empresa)" src/
```

Cada item abaixo aponta o arquivo, o que assumimos no MVP e o que revisar.

## Panorama

| Item | Arquivo | Tema | Bloqueia produção? |
|---|---|---|---|
| 1 | `config.py` | Modelo de auth (named profiles) | Não — decidido |
| 2 | `config.py` | Região da conta de dados | Depende |
| 3 | `glue/logs.py` | Log group / naming de stream | ✅ Implementado — confirmar em produção |
| 4 | `glue/jobs.py` | Campos de job incompletos | **Sim** se usar os campos faltantes |
| 5 | `glue/replicate.py` | Conflitos de replicação | **Sim** para pythonshell / VPC |
| 6 | `glue/validate.py` | Argumentos herdados no run | **Sim** para run de validação real |
| 7 | `glue/tables.py` | Paginação de partições | Não — só afeta contagem |
| 9 | `glue/tables.py` | Lake Formation filtra colunas | Atenção — falso "schema drift" |
| 10 | `config.py` | Trilha de auditoria | Não — ponto de extensão |

> (Não há item 8 aberto: uma suspeita inicial de account id hardcoded no
> `.mcp.json` foi verificada e o template já usa interpolação `${...}`.)

## Detalhe por item

### Item 1 — modelo de auth *(decidido)*
`config.py`, em `resolve_session`. A decisão é **named profiles por conta**; o
parâmetro `profile` já cobre `sandbox_profile`/`data_profile`. Só mexa se a infra
migrar para "profile base + assume-role por conta" — aí injete `role_arn` e use
`sts.assume_role` neste ponto. Ver [configuration.md](configuration.md).

### Item 2 — região da conta de dados
`config.py`. O fallback global é `sa-east-1` com a precedência descrita em
[configuration.md](configuration.md). Se a conta de dados ficar em **outra**
região, exponha um parâmetro `region` nas tools de tabela (`inspect_table` /
`check_partitions`) e propague até `resolve_session`.

### Item 3 — log group e naming de stream ✅
`glue/logs.py`. **Implementado.** `error_excerpt` tenta o grupo de continuous
logging (`/aws-glue/jobs/logs-v2`) e cai para o legado (`/aws-glue/jobs/error`);
dentro do grupo, **varre os streams por worker** (`<run_id>_g-<worker_hash>`, sem
rótulo de driver na empresa) e devolve o primeiro que contém o marcador de erro,
preferindo o grupo cujo stream realmente tem o traceback. Cobre os dois mundos
sem configuração. **A confirmar em produção:** que o marcador de erro cai dentro
das `_MAX_STREAMS_SCANNED` streams mais recentes em runs com muitos executores.

### Item 4 — campos de job incompletos
`glue/jobs.py`, `_PORTABLE_FIELDS`. Jobs reais costumam usar
`SecurityConfiguration`, `NonOverridableArguments`, `NotificationProperty` e
`MaxCapacity` (pythonshell **não** usa `NumberOfWorkers`). `Tags` nem vêm no
`get_job` — é `get_tags` à parte, e a governança pode exigi-las. Acrescente o que
a empresa usa aos campos portáveis.

### Item 5 — conflitos de replicação
`glue/replicate.py`, `_to_create_input`. Dois conflitos a tratar por tipo de job:
`pythonshell` com `MaxCapacity` + `NumberOfWorkers` no payload faz `create_job`
estourar (escolha um conforme `Command.Name`); e `Connections` apontam para
VPC/conexões de produção que não existem na sandbox — precisa de override.

### Item 6 — argumentos herdados no run de validação
`glue/validate.py`, `start_validation_run`. O `Arguments` do run **ignora** os
`DefaultArguments` do job. Jobs reais costumam precisar de `--JOB_NAME`,
`--job-bookmark-option`, etc. Para um run de validação barato e determinístico:
mesclar `DefaultArguments`, desabilitar o bookmark e capar DPU/workers.

### Item 7 — paginação de partições
`glue/tables.py`, `check_partitions`. `MaxResults=100` sem paginar. Para checar
**existência** basta a 1ª página; mas `matched_count` satura em 100 e engana em
tabelas grandes. Se for reportar contagem, pagine ou rotule `">=100"`.

### Item 9 — Lake Formation filtra colunas
`glue/tables.py`, `inspect_table`. Sob Lake Formation, `get_table` pode devolver
colunas filtradas pela permissão do `data_profile`. Um "schema drift" aparente
pode ser efeito de permissão, não do schema real — a skill de diagnóstico deve
registrar essa ressalva.

### Item 10 — trilha de auditoria
`config.py`, `ensure_sandbox`. É o único gargalo por onde toda escrita passa. Se
a empresa quiser "quem replicou/rodou o quê", emita ali um log estruturado
(account_id, profile, operação) antes de liberar. Ver [security.md](security.md).

## Além dos anchors de código

- **Skill `testes-unitarios`**: hoje é só uma casca com placeholder
  (`TODO(empresa)` no `SKILL.md`). Troque o corpo pelo padrão de testes da
  empresa (o markdown que você já tem). Ver [commands.md](commands.md).
- **Eval de diagnóstico**: a casca já existe em `evals/` (roda o extrator de
  excerto real contra streams gravados). Preencha `evals/cases/` com falhas reais
  anonimizadas — inclusive o naming `<run_id>_g-<worker_hash>` da empresa.
