# Simulação — testar tudo sem AWS

Um AWS falso (Glue + CloudWatch Logs) com dados realistas, para exercitar o
toolkit inteiro **sem credencial, sem rede e sem conta**.

## O comando único

Da raiz do repo:

```bash
python simulate.py
```

Roda em sequência: lint → tipos → testes → evals → simulação end-to-end das
tools. Sai com código ≠ 0 se algo falhar. É só isso que você precisa rodar.

## O que tem dentro

| Arquivo | Para quê |
|---|---|
| `fake_aws.py` | O AWS falso: fixtures + clients Glue/Logs com só os métodos que o código chama |
| `demo.py` | Exercita todas as tools e **confere** os resultados (demo + smoke test) |
| `serve_fake.py` | Sobe o servidor MCP **real** ligado ao AWS falso, para o Claude Code |

Nada disso é empacotado: `simulation/` vive fora de `src/`, é ferramenta de dev.

## Os dados simulados

**Jobs:** `orders-etl` (glueetl), `clicks-ingest` (glueetl), `legacy-report`
(pythonshell) — servidos em 2 páginas, para exercitar a paginação.

**Runs de `orders-etl`:**

| Run | Estado | Por que existe |
|---|---|---|
| `jr_20260722_failed` | FAILED | Traceback (`AnalysisException`) no stream do **driver** — o caso comum |
| `jr_20260719_oom` | FAILED | `OutOfMemoryError` **só no stream do executor** (`_g-9f2c1a`) — o caso do item 3 |
| `jr_20260721_ok` | SUCCEEDED | Confirma que run bom não vai buscar log |

**Log groups** imitam o aninhamento por conta:
`/aws-glue/jobs/sec-config-prod/vendas/etl-role/error` (stderr) e
`/aws-glue/jobs/logs-v2-sec-config-prod` — servidos em 2 páginas (exercita o
`nextToken`), e os grupos genéricos de fallback devolvem `ResourceNotFoundException`
como numa conta real.

**Tabelas:** `db_vendas.orders` (hive, partição `dt`) e `db_vendas.orders_iceberg`
(Iceberg, para ver o `check_partitions` recusar de propósito). Partições
existentes: `dt='2026-07-22'` e `dt='2026-07-21'`.

## Testar no Claude Code, offline

Dá para conversar com o agente de verdade — `/analyze-job-run` completo — sem AWS.
Num repo de teste, crie `.mcp.json`:

```json
{
  "mcpServers": {
    "data-platform": {
      "command": "python",
      "args": ["/caminho/absoluto/para/simulation/serve_fake.py"]
    }
  }
}
```

Abra o Claude Code nesse repo e peça:

```
/analyze-job-run orders-etl jr_20260722_failed
```

O servidor é o **de produção** (mesmas tools, mesmas docstrings); só a resolução
de sessão é trocada. Bom para validar o texto das skills e o comportamento do
agente antes de apontar para a AWS real.

## Adicionar um cenário

Edite `fake_aws.py`: acrescente o run em `_RUNS`, os streams em `_STREAMS` e as
linhas de log em `_EVENTS`. Se for um erro real da empresa, considere também
gravá-lo como caso de eval em `evals/cases/` — ali ele vira teste permanente.
