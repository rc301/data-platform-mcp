# Configuração

Toda a configuração de runtime vive em variáveis de ambiente e no modelo de
profiles AWS. Nada de segredo em arquivo versionado. A implementação está em
[`src/dataplatform/config.py`](../src/dataplatform/config.py).

## Variáveis de ambiente

| Variável | Obrigatória | Para quê |
|---|---|---|
| `AWS_PROFILE` | sim (na prática) | Named profile do desenvolvedor para a conta do job. Cadeia padrão AWS. |
| `AWS_REGION` / `AWS_DEFAULT_REGION` | não | Região, lida nativamente pelo boto3. Se ausente, cai para o fallback. |
| `DATAPLATFORM_GLUE_LOG_GROUPS` | não | Lista explícita de log groups (separada por vírgula, melhor primeiro) que **pula a descoberta** e dispensa `logs:DescribeLogGroups`. |

```bash
export AWS_PROFILE=meu-profile-dev
```

## Descoberta de log group do Glue

Os grupos de log do Glue **variam por conta**: os **Error Logs** ficam num caminho
aninhado por security configuration terminando em `/error`
(`/aws-glue/jobs/<sec-config>/<domínio>/<role>/error`), e os **All Logs**
(contínuo) num nome achatado começando com `logs-v2`
(`/aws-glue/jobs/logs-v2-<sec-config>`). Por isso o `analyze-job-run` **descobre**
os grupos: lista sob `/aws-glue/jobs` e classifica — os `/error` primeiro (stderr,
onde cai o traceback), depois os `logs-v2*`. Isso exige a permissão IAM
**`logs:DescribeLogGroups`** no profile do dev.

Se seus grupos forem fixos, `DATAPLATFORM_GLUE_LOG_GROUPS` os passa explicitamente
e pula a descoberta (dispensando `DescribeLogGroups`). Detalhe do stream (driver =
`<run_id>`, executores `<run_id>_g-<worker>`, `progress-bar` descartado) em
[company-adaptation.md](company-adaptation.md).

## Modelo de autenticação: named profiles por conta

A decisão do projeto é **um named profile por conta** (decidido). O toolkit age
como o humano que o roda — não há service account. Os parâmetros das tools cobrem
as duas contas lidas:

- **conta do job** → `AWS_PROFILE` ambiente (default).
- **conta de dados** → parâmetro `data_profile` das tools de tabela.

`resolve_session(profile=...)` constrói a sessão boto3 e resolve o **account id
via STS**, para reportar a identidade em uso. Se um dia a
infra migrar para "um profile base + assume-role por conta", o único ponto a
mudar é `resolve_session` (injetar `role_arn` e usar `sts.assume_role`) — está
marcado com `TODO(empresa) item 1`. Ver [company-adaptation.md](company-adaptation.md).

## Região

Precedência ao resolver a região (a primeira que existir vence):

```
1. argumento region= explícito na chamada
2. região do profile (~/.aws/config)
3. AWS_REGION / AWS_DEFAULT_REGION   (lidos nativamente pelo boto3)
4. DEFAULT_REGION = "sa-east-1"      (fallback)
```

Sem o passo 4, um profile sem região deixaria os clients Glue/CloudWatch Logs sem
endpoint. `sa-east-1` é o padrão porque é onde a empresa roda. Se a conta de
dados estiver em **outra** região, hoje seria preciso expor `region` nas tools de
tabela — marcado como ajuste futuro em `config.py`.

## Fuso horário

Os resumos de run reportam horários em **BRT** (UTC−03:00 fixo). É uma convenção
de apresentação nas funções de diagnóstico, não uma configuração.
