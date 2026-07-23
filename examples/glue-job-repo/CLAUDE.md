# CLAUDE.md — repositório de Glue jobs

Contexto e regras para o Claude Code trabalhar neste repositório. Este arquivo
é carregado automaticamente no início de cada sessão.

## O que é este repo

Cada pasta em `jobs/<nome>/` é um Glue job: um `script.py` (o código que roda no
Glue) e um `job.json` (a configuração do job — role, worker, argumentos).

## Fluxo de trabalho padrão

Ao alterar um job, o ciclo é sempre:

1. **Inspecionar** o job existente em produção para entender a configuração atual.
2. **Replicar** para a conta sandbox (nunca se testa em produção).
3. **Rodar e validar** na sandbox, olhando o log quando falhar.
4. Só então abrir PR para `develop`.

Este fluxo está encapsulado na skill **`validar-job`** — use-a quando for
validar uma alteração.

## Ferramentas (MCP)

O servidor MCP **`data-platform`** (configurado em `.mcp.json`) expõe as tools
para inspecionar/replicar/rodar/logar jobs. Prefira essas tools a chamar `aws`
na mão — elas já aplicam as travas de segurança.

## Regras de segurança — inegociáveis

- **Escrita só em sandbox.** As tools de escrita (`replicate_job_to_sandbox`,
  `run_sandbox_job`) são recusadas fora das contas em
  `DATAPLATFORM_SANDBOX_ACCOUNTS`. Nunca contorne isso com chamadas `aws` diretas.
- **Credencial é a do dev** (`AWS_PROFILE`). Não há service account.
- **Nunca commite** credenciais, ARNs de conta ou IDs de conta reais. `job.json`
  usa placeholders; valores reais ficam em variáveis de ambiente locais.

## Convenções (conhecimento estático — não são tools)

- Script de job em `jobs/<nome>/script.py`, ponto de entrada compatível com
  Glue (lê `getResolvedOptions`).
- Nome do job na sandbox: sufixo `-sandbox` sobre o nome de produção.
- Testes de transformação pura em `tests/`, sem depender de AWS.
