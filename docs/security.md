# Segurança

Três garantias estruturais: **credencial é sempre a do desenvolvedor**, **o
toolkit é somente-leitura (não existe caminho de escrita)** e **nada de segredo
no git**.

## 1. Credenciais do próprio desenvolvedor

O toolkit usa a cadeia padrão AWS (`AWS_PROFILE` / `AWS_*`). Não há service
account: ele age como o humano que o roda, com as permissões desse humano. Isso
mantém a auditoria da AWS apontando para uma pessoa real e evita credencial de
longa duração embutida na ferramenta. Modelo de profiles em
[configuration.md](configuration.md).

## 2. Somente-leitura — não existe caminho de escrita

A garantia mais forte é estrutural: **não há operação de escrita no toolkit**.
Nenhuma tool do MCP muta a AWS, e a biblioteca também não expõe funções de
escrita — elas foram removidas. Não é "escrita bloqueada por uma trava"; é
"escrita não existe". Nada a burlar.

A identidade da conta ainda é resolvida via **STS** (`get_caller_identity`), mas
só para **reportar** com precisão qual conta/profile está em uso — não para
guardar mutação nenhuma.

A regra de negócio no `CLAUDE.md` reforça o flanco de fora: nunca rodar `aws`/
`boto3` direto para alterar algo; falha em produção é investigação read-only, não
conserto às cegas. Se uma operação de escrita for mesmo necessária, o Claude
avisa que não está autorizado e o humano a executa.

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
| Inspecionar/listar jobs, diagnosticar runs | conta do job (dev) | read |
| Inspecionar schema/partição de origem | conta de dados (terceira) | read-only |

Leituras na conta de dados usam um `data_profile` próprio e são sempre
read-only. Isso evita que uma sessão de diagnóstico toque, mesmo por engano, na
conta que guarda os dados.
