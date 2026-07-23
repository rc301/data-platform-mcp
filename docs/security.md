# Segurança

Três garantias estruturais: **credencial é sempre a do desenvolvedor**, **escrita
só em sandbox declarada (fail-closed)** e **nada de segredo no git**.

## 1. Credenciais do próprio desenvolvedor

O toolkit usa a cadeia padrão AWS (`AWS_PROFILE` / `AWS_*`). Não há service
account: ele age como o humano que o roda, com as permissões desse humano. Isso
mantém a auditoria da AWS apontando para uma pessoa real e evita credencial de
longa duração embutida na ferramenta. Modelo de profiles em
[configuration.md](configuration.md).

## 2. Escrita só em sandbox — e fail-closed

**As tools do MCP são somente-leitura** — nenhuma escreve na AWS. As funções de
escrita (`glue.replicate_to_sandbox`, `glue.start_validation_run`) continuam na
biblioteca como substrato reutilizável, mas não são expostas como tools neste
build. Quando forem chamadas (por lib ou por um futuro caminho de code-execution),
passam pela mesma guarda: chamam `ensure_sandbox(session)` **antes** de qualquer
mutação (em [`config.py`](../src/dataplatform/config.py)):

```python
def ensure_sandbox(session: Session) -> None:
    allowed = sandbox_account_ids()          # de DATAPLATFORM_SANDBOX_ACCOUNTS
    if not allowed:
        raise SandboxViolation(...)          # nenhuma sandbox configurada ⇒ nega tudo
    if session.account_id not in allowed:
        raise SandboxViolation(...)          # conta resolvida não está na lista
```

Duas propriedades importantes:

- **Fail-closed:** se `DATAPLATFORM_SANDBOX_ACCOUNTS` estiver vazio, **toda**
  escrita é recusada. O default seguro é "não escreve", não "escreve em qualquer
  lugar".
- **Identidade autoritativa:** a conta vem do **STS** (`get_caller_identity`), não
  de um parâmetro que o modelo poderia inventar. O agente não consegue burlar a
  guarda passando um nome de conta.

A regra de negócio no `CLAUDE.md` reforça: nunca contornar isso com chamadas `aws`
diretas; falha em produção é investigação read-only, não conserto às cegas.

## 3. Higiene de segredos

- **Nunca commitar** credenciais, ARNs de conta ou IDs de conta reais.
- `job.json` usa **placeholders** (`<ACCOUNT_ID>`, role, bucket); valores reais
  ficam em variáveis de ambiente locais.
- Nomes internos/de produto são **genéricos** no repositório — nada que não possa
  estar num GitHub.
- O `.mcp.json` template usa interpolação `${...}` para não gravar valores.

## Separação de contas por operação

| Operação | Conta | Acesso |
|---|---|---|
| Inspecionar/listar jobs, diagnosticar runs | conta do job (dev) | read (via MCP) |
| Inspecionar schema/partição de origem | conta de dados (terceira) | read-only (via MCP) |
| Replicar / rodar validação (funções de lib) | conta **sandbox** | **write, guardada** (não exposta no MCP) |

Leituras na conta de dados usam um `data_profile` próprio e são sempre
read-only. Isso evita que uma sessão de diagnóstico toque, mesmo por engano, na
conta que guarda os dados.

## Auditoria (ponto de extensão)

`ensure_sandbox` é o único gargalo por onde toda escrita passa. Se a empresa
quiser trilha de "quem replicou/rodou o quê", o lugar de emitir um log
estruturado (account_id, profile, operação) é ali — marcado como
`TODO(empresa) item 10`. Ver [company-adaptation.md](company-adaptation.md).
