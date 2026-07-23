# Documentação — data-platform-mcp

Toolkit de desenvolvedor para trabalhar com AWS Glue jobs, mais um servidor MCP
que expõe esse toolkit a agentes de IA (Claude Code). Dá ao agente uma janela
**somente-leitura** sobre o Glue — inspecionar configs, diagnosticar runs que
falharam e checar tabelas de origem — e um catálogo de comandos que cresce por
composição, sem inchar a camada de tools.

## Mapa da documentação

| Documento | Para quê |
|---|---|
| [getting-started.md](getting-started.md) | Instalar, configurar, rodar `init` e abrir a primeira sessão. Começa aqui. |
| [cli.md](cli.md) | A CLI `data-platform-mcp`: `init`, `list`, `serve`. Flags, idempotência, portabilidade. |
| [configuration.md](configuration.md) | Variáveis de ambiente, profiles por conta e região. |
| [mcp-server.md](mcp-server.md) | O servidor MCP (casca fina) e a referência completa das tools. |
| [commands.md](commands.md) | O catálogo de comandos (skills / commands / subagentes) e como adicionar um. |
| [architecture.md](architecture.md) | As quatro camadas e o mapa de reuso tools × comandos. O "porquê" do design. |
| [security.md](security.md) | Somente-leitura (sem caminho de escrita), credenciais e higiene de segredos. |
| [company-adaptation.md](company-adaptation.md) | Os pontos `TODO(empresa)` a ajustar para rodar na empresa. |

## Leitura sugerida por papel

- **Vou usar num repo de jobs** → [getting-started.md](getting-started.md) →
  [commands.md](commands.md).
- **Vou adaptar para a empresa** → [company-adaptation.md](company-adaptation.md)
  → [configuration.md](configuration.md) → [security.md](security.md).
- **Vou estender (novo comando/tool)** → [architecture.md](architecture.md) →
  [commands.md](commands.md) → [mcp-server.md](mcp-server.md).

## Em uma frase

A biblioteca (`dataplatform.glue.*`) tem toda a lógica; o servidor MCP é só uma
casca que liga essas funções a tools; comandos e skills **compõem** essas tools.
As tools do MCP são somente-leitura e sempre usam a credencial do próprio
desenvolvedor. Não há operações de escrita — o toolkit nunca altera a AWS. Ver
[security.md](security.md).
