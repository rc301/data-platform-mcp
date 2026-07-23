# Evals — qualidade do diagnóstico

Mede a parte determinística que mais afeta o `analyze-job-run`: o **extrator de
excerto** (`error_excerpt`). Dá um stream de erro gravado e verifica que o
excerto surfaça a causa real (o `Caused by:`), não o ruído do fim do log.

Sem AWS, sem modelo, sem dependências — feed direto pelo código real.

## Rodar

```bash
python evals/run_evals.py
```

Sai com código ≠ 0 se algum caso falhar (dá pra plugar na CI).

## Adicionar um caso

Um arquivo `cases/<nome>.json`:

```json
{
  "name": "descrição curta",
  "command_name": "glueetl",
  "run_id": "jr_x",
  "log_lines": ["... linhas do stream de erro ..."],
  "expect": {
    "found_markers": true,
    "excerpt_contains": ["a linha causal que TEM de aparecer"],
    "excerpt_excludes": ["ruído que NÃO deveria aparecer"]
  }
}
```

Regras ao preencher:
- **Anonimize.** Nada de conta, ARN, bucket, host interno ou dado real —
  substitua por placeholders. Estes arquivos são versionados.
- Use falhas **reais** do seu ambiente (é o valor do eval).
- Uma falha por arquivo; agrupe variações no `expect`.

## Fora de escopo (por ora)

O julgamento do **modelo** — "o agente nomeou a causa certa a partir do excerto?"
— precisa de um grader (LLM-judge) e de casos reais. Fica para depois de termos
um conjunto de casos; aqui fixamos a fundação determinística primeiro.
