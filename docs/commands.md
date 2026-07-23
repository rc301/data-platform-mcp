# Catálogo de comandos (skills, commands, subagentes)

Esta solução não é "um MCP para uma tarefa". É uma plataforma sobre a qual o
engenheiro roda vários comandos no repositório de jobs. Cada comando é uma
**skill** (o playbook) acionada por um **slash command** (o gatilho), compondo as
**tools** existentes. Nenhum comando novo cria tool nova. O "porquê" desse design
está em [architecture.md](architecture.md).

## As peças

| Peça | O que é | Onde vive | Contexto |
|---|---|---|---|
| **Skill** | Playbook + conhecimento estático (rubrica, catálogo de erro) | `.claude/skills/<nome>/SKILL.md` (+ `reference/`) | Carrega no contexto atual |
| **Command** | Gatilho manual `/x` que aciona uma skill | `.claude/commands/<nome>.md` | Roda no seu contexto |
| **Subagente** | Execução isolada, contexto próprio, só devolve o relatório final | `.claude/agents/<nome>.md` | Contexto isolado |

Relação: **command = "o quê"** (ponto de entrada), **skill = "como"** (playbook),
**subagente = "onde"** (contexto isolado). Um command roda a skill inline **ou**
delega a um subagente — é uma decisão escrita no `.md` do command. Um command
**não** instancia agente automaticamente; ele só faz isso se o texto dele mandar
delegar.

## Comandos disponíveis

| Comando | Skill | Compõe | Subagente |
|---|---|---|---|
| `/validar-job <job>` | `validar-job` | inspecionar → replicar na sandbox → rodar e validar | `job-validator` |
| `/analyze-job-run <job> <run>` | `analyze-job-run` | resumo do run → excerto de erro → schema/partição | `job-diagnoser` |
| `/code-review [job\|base]` | `code-review` | diff → contraste com produção/histórico → rubrica de risco | — |
| `/testes-unitarios [path]` | `testes-unitarios` | roda a suíte de testes puros do repo | — |

### `validar-job`
Exercita uma alteração de ponta a ponta na conta sandbox antes do PR: inspeciona
o job de produção, replica para a sandbox, roda um run de validação e reporta.
Escrita só na sandbox (guardada). Tem o subagente `job-validator` para isolar o
trabalho barulhento.

### `analyze-job-run`
Diagnostica um run que falhou. Começa em `diagnose_job_run` (resumo + histórico +
excerto de erro), e só aprofunda em `inspect_table`/`check_partitions` se o erro
apontar para dados/schema. Carrega o catálogo estático `reference/glue-errors.md`.
Read-only — propõe a correção, não conserta em produção. Subagente:
`job-diagnoser`.

### `code-review`
Parecer de risco **antes** de subir para produção. Read-only: não edita, não
replica, não roda. Delimita o diff, contrasta o `job.json` do PR com a config de
produção (`inspect_glue_job`), checa o histórico (`list_job_runs`), valida a
origem se o diff tocar dados, e aplica a rubrica estática
`code-review/reference/rubric.md`. Entrega veredito (aprovar / com ressalvas /
bloquear) + achados (severidade, arquivo:linha, correção) + checklist "antes de
subir".

### `testes-unitarios`
**Casca** propositalmente mínima: roda os testes puros do repo. O corpo da skill
é um placeholder marcado com `TODO(empresa)` para ser trocado pelo padrão de
testes da empresa (ver [company-adaptation.md](company-adaptation.md)).

## Como adicionar um comando novo

1. **Escreva a skill** em `.claude/skills/<nome>/SKILL.md` — estratégia + o
   conhecimento estático (rubrica, padrão de doc) em `reference/`. A skill compõe
   tools existentes.
2. **Adicione o slash command** em `.claude/commands/<nome>.md` apontando para a
   skill (com `$ARGUMENTS`).
3. **(Opcional) um subagente** em `.claude/agents/<nome>.md` se o trabalho for
   barulhento e valer isolar o contexto.
4. **Registre no scaffolder** — `_FILES` e `_SCAFFOLDED_ASSETS` em
   [`src/dataplatform/cli.py`](../src/dataplatform/cli.py) — para o `init`
   distribuir.
5. **Só crie tool nova** se surgir capacidade nova reutilizável (interação AWS que
   muda entre runs e que ≥1 comando usaria). Caso contrário, componha as que já
   existem.

## Distribuição: por-repo, por-usuário ou plugin

O `init` grava agentes/skills/commands **no repo** (`.claude/`). Se você não quer
uma cópia por repo, as alternativas do Claude Code são:

- **Escopo de usuário** `~/.claude/agents|skills|commands/` — instala uma vez,
  vale para todos os repos.
- **Plugin** do Claude Code — empacota tudo e distribui central.

Importante: subagente é construto do Claude Code, lido de arquivos markdown
(projeto ou usuário) ou de um plugin. **Não** é lido de dentro de um pacote
Python — o `pip install` da lib entrega as *tools* (via MCP) e a CLI, não os
agentes. O que dá para mover para a lib é o *texto de um comando* como **MCP
prompt**, mas isso vira um comando (roda no contexto atual), não um subagente.
