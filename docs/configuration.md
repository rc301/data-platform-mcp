# Configuração

Toda a configuração de runtime vive em variáveis de ambiente e no modelo de
profiles AWS. Nada de segredo em arquivo versionado. A implementação está em
[`src/dataplatform/config.py`](../src/dataplatform/config.py).

## Variáveis de ambiente

| Variável | Obrigatória | Para quê |
|---|---|---|
| `AWS_PROFILE` | sim (na prática) | Named profile do desenvolvedor para a conta do job. Cadeia padrão AWS. |
| `DATAPLATFORM_SANDBOX_ACCOUNTS` | sim para escrever | Lista, separada por vírgula, das contas onde escrita é permitida. Vazio ⇒ toda escrita recusada (fail-closed). |
| `AWS_REGION` / `AWS_DEFAULT_REGION` | não | Região, lida nativamente pelo boto3. Se ausente, cai para o fallback. |

```bash
export AWS_PROFILE=meu-profile-dev
export DATAPLATFORM_SANDBOX_ACCOUNTS=111122223333,444455556666
```

## Modelo de autenticação: named profiles por conta

A decisão do projeto é **um named profile por conta** (decidido). O toolkit age
como o humano que o roda — não há service account. Os parâmetros das tools já
cobrem as três contas:

- **conta do job** → `AWS_PROFILE` ambiente (default).
- **conta sandbox** → parâmetro `sandbox_profile` das tools de escrita.
- **conta de dados** → parâmetro `data_profile` das tools de tabela.

`resolve_session(profile=...)` constrói a sessão boto3 e resolve o **account id
via STS**, para que toda guarda tenha uma identidade autoritativa. Se um dia a
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

## Contas sandbox e a trava de escrita

`DATAPLATFORM_SANDBOX_ACCOUNTS` é o coração da segurança de escrita. `ensure_sandbox`
roda no topo de toda operação mutante e:

- **Falha fechado:** se a variável estiver vazia, **toda** escrita é recusada.
- **Confere identidade:** a conta resolvida (via STS) precisa estar na lista.

Detalhes e racional em [security.md](security.md).

## Fuso horário

Os resumos de run reportam horários em **BRT** (UTC−03:00 fixo). É uma convenção
de apresentação nas funções de diagnóstico, não uma configuração.
