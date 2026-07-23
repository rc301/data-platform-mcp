---
name: testes-unitarios
description: >-
  Roda os testes unitários deste repositório de Glue jobs. Use quando o usuário
  pedir para rodar/validar os testes (ex.: "roda os testes", "testa o transform")
  ou disparar /testes-unitarios. Não use para rodar o job na AWS — isso é validar-job.
---

# Rodar testes unitários

<!-- CASCA: este corpo é um placeholder. Substitua pelo markdown de testes que
     já existe na empresa (o playbook real de como rodar/interpretar a suíte). -->

Rode a suíte de testes unitários deste repositório e reporte o resultado.

1. Descubra o runner do projeto (ex.: `pytest` sobre `tests/`) e execute-o.
2. Se algum teste falhar, mostre o nome do teste e o trecho relevante do erro.
3. Feche com um resumo: quantos passaram/falharam e o que precisa de atenção.

> TODO(empresa): trocar todo o conteúdo acima pelo padrão de testes da empresa.
