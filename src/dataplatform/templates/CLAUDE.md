# CLAUDE.md — repositório de Glue jobs

Contexto e regras para o Claude Code trabalhar neste repositório. Este arquivo
é carregado automaticamente no início de cada sessão.

## O que é este repo

Cada pasta em `jobs/<nome>/` é um Glue job: um `script.py` (o código que roda no
Glue) e um `job.json` (a configuração do job — role, worker, argumentos).

Você trabalha aqui como um engenheiro de dados: entende jobs, altera scripts,
valida mudanças, investiga falhas e documenta. Não há um único fluxo — há um
**catálogo de comandos**, cada um encapsulado numa skill que compõe as tools do
MCP. Escolha o comando pela intenção do usuário.

## Comandos disponíveis

| Quando o usuário quer… | Use a skill / comando | Encapsula |
|---|---|---|
| Entender por que um run falhou | **`analyze-job-run`** (`/analyze-job-run`) | resumo do run → excerto de erro → schema/partição da origem |
| Revisar uma mudança antes de subir p/ produção | **`code-review`** (`/code-review`) | diff → contraste com produção/histórico → rubrica de risco |
| Rodar os testes unitários | **`testes-unitarios`** (`/testes-unitarios`) | suíte de testes puros do repo |

Novos comandos entram como skill + slash command sobre as **mesmas** tools — não
como tools novas. Rode `data-platform list` para ver o catálogo atual, ou veja o
mapa de reuso em `docs/architecture.md` (no repo do toolkit).

## Como trabalhar

- **Nunca altere produção às cegas.** Antes de subir, use `/code-review` para o
  parecer de risco e `/testes-unitarios` para as transformações puras. As tools
  do MCP são somente-leitura — não faça mudanças na AWS via `aws` na mão.
- **Leituras em contas de dados terceiras** (schema/partição de tabela origem)
  usam um `data_profile` próprio e são sempre read-only.
- **Falha em produção é investigação, não conserto às cegas**: diagnostique com
  `analyze-job-run` (ou o subagente `job-diagnoser`) e proponha a correção para o
  usuário testar — não a aplique sozinho em produção.

## Ferramentas (MCP)

O servidor MCP **`data-platform`** (configurado em `.mcp.json`) expõe tools
somente-leitura para inspecionar e diagnosticar jobs/runs e inspecionar tabelas
de origem. Prefira essas tools a chamar `aws` na mão.

## Regras de segurança — inegociáveis

- **MCP é somente-leitura.** Nenhuma tool escreve na AWS. Não contorne isso com
  chamadas `aws` diretas para alterar jobs.
- **Credencial é a do dev** (`AWS_PROFILE`). Não há service account.
- **Nunca commite** credenciais, ARNs de conta ou IDs de conta reais. `job.json`
  usa placeholders; valores reais ficam em variáveis de ambiente locais.

## Convenções (conhecimento estático — não são tools)

- Script de job em `jobs/<nome>/script.py`, ponto de entrada compatível com
  Glue (lê `getResolvedOptions`).
- Testes de transformação pura em `tests/`, sem depender de AWS.
