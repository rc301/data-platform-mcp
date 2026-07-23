# CLI — `data-platform-mcp`

Um único comando de console, instalado junto com o pacote e **nomeado como o
pacote**. Tem três subcomandos: `init`, `list` e `serve`. O nome curto
`data-platform` é um alias para o mesmo dispatcher — os dois apontam para
`dataplatform.cli:main`.

```
data-platform-mcp <init|list|serve> [opções]
```

Por que uma CLI e não uma tool MCP? Escrever arquivos locais de projeto é um
bootstrap de desenvolvedor (como `git init`), que precisa existir **antes** do
repo ter qualquer config do Claude. O servidor MCP fala com a AWS e deve ficar
fino; bootstrap local não é responsabilidade dele.

## `init` — scaffold da config

```bash
data-platform-mcp init [path] [--force]
```

Copia os templates do pacote para o repo alvo.

- `path` — diretório do repo (padrão: diretório atual).
- `--force` — sobrescreve arquivos existentes (por padrão nunca sobrescreve).

**Idempotente:** cria só o que falta. Roda de novo sem medo para pegar templates
novos; arquivos que você editou são preservados (a menos que use `--force`).

Saída típica:

```
  criado   CLAUDE.md
  criado   .mcp.json
  criado   .claude/skills/analyze-job-run/SKILL.md
  mantido  CLAUDE.md (já existe; use --force para sobrescrever)
```

Arquivos gravados: `CLAUDE.md`, `.mcp.json` e a árvore
`.claude/{agents,skills,commands}/...`. A lista exata é declarada em `_FILES` em
[`src/dataplatform/cli.py`](../src/dataplatform/cli.py) — a fonte única de verdade
são os templates em `src/dataplatform/templates/`.

## `list` — descobrir o que o toolkit expõe

```bash
data-platform-mcp list
```

Imprime três blocos:

1. **Comandos de CLI** — `init`, `list`, `serve`.
2. **Tools do MCP** — introspectadas **ao vivo** do servidor (via
   `mcp.list_tools()`), então a listagem nunca diverge da realidade. Requer o
   extra `[mcp]`; sem ele, imprime uma dica em vez das tools.
3. **Assets criados pelo `init`** — as skills, subagentes e slash commands que
   vão para o repo.

## `serve` — subir o servidor MCP

```bash
data-platform-mcp serve
```

Sobe o servidor MCP em **stdio**. É exatamente o que o `.mcp.json` gerado invoca:

```json
{
  "mcpServers": {
    "data-platform": {
      "command": "data-platform-mcp",
      "args": ["serve"],
      "env": { "AWS_PROFILE": "...", "AWS_REGION": "..." }
    }
  }
}
```

Requer o extra `[mcp]` (`fastmcp`). Sem ele, o comando explica como instalar e
sai com código 1. Também é possível rodar direto com
`python -m dataplatform.mcp.server`.

## Portabilidade (Windows e Linux/RHEL 9)

- **Entry point:** o pip gera `data-platform-mcp` (Linux) ou
  `data-platform-mcp.exe` (Windows) a partir do mesmo `[project.scripts]`.
- **Caminhos:** montados com `pathlib` e traversal de `importlib.resources`. As
  chaves de template usam `/` (chaves de recurso, não caminhos de sistema), e o
  destino é `target / "a/b/c"`, que o `Path` normaliza corretamente em ambos os
  SOs.
- **Encoding:** toda leitura/escrita fixa `encoding="utf-8"`, então não depende
  do code page padrão do Windows (cp1252).
