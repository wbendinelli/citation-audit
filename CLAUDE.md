# CLAUDE.md — manual de operação para agentes neste repositório

Auditoria da qualidade das citações recebidas por dois artigos do autor —
ver [README.md](README.md) e [METHOD.md](METHOD.md). O repositório tem
**uma regra dura** e o resto serve a ela:

> **Todo número quantitativo em prosa é impresso por um script versionado
> commitado.** Um número sem script que o imprima é bug — ou some o script,
> ou apague o número. Quando uma medição contradiz a prosa, a prosa muda e o
> valor antigo fica registrado na nota, marcado como corrigido (régua de
> evidência, regra 3 — ver CONTRIBUTING.md).

Política completa: [CONTRIBUTING.md](CONTRIBUTING.md). Este arquivo é a
versão condensada, voltada a agente, mais os deveres que nenhuma checagem
automática cobre.

## Língua

**Português**, por decisão do dono do repositório — inclusive para
código-comentário e mensagem de commit. Isto é uma exceção deliberada ao
padrão em inglês de outros repositórios SAPIANS; não "corrija" para inglês.

## O que o CI já garante (não brigue com ele, não duplique)

CI vermelho é comportamento correto — conserte na causa, nunca enfraqueça a
checagem:

- **links** — links relativos e âncoras em todo `.md` + `CITATION.cff`
  (lychee, offline).
- **checks** — `pre-commit run --all-files` (yaml/json, ruff em `tools/`,
  actionlint, e os hooks locais `data-invariants`, `pending-generated`,
  `report-generated`, `tier-rule` — ver `.pre-commit-config.yaml`).
- **scripts** — `audit_50_pending.py`, `audit_41_scimago.py --check`,
  `audit_80_report_html.py` e `check_data.py` rodam de novo em CI; a árvore
  de trabalho tem de sair limpa (`git status --porcelain` vazio) — um script
  `--check` que não bate com o commitado é a checagem funcionando, não uma
  falha do CI.
- **citation** — `CITATION.cff` continua válido (schema 1.2.0).

## Deveres que o CI não cobre (faça sem que peçam)

1. **CHANGELOG.md** — uma linha por mudança notável em `tools/`, `data/` ou
   `METHOD.md`, sob o cabeçalho de data certo. O CI não te obriga a tocar o
   arquivo aqui (diferente do repositório de referência) — é disciplina, não
   checagem.
2. **Rode o bloco B antes de commitar** qualquer mudança em `tools/` que
   toque `data/*.json` (ver [`tools/README.md`](tools/README.md#como-rodar)):
   `audit_12_merge_scholar.py`, `audit_30_validate_texts.py`,
   `audit_31_passages.py`, `audit_32_gate_bibonly.py`, `audit_41_scimago.py`,
   `audit_50_pending.py`, `audit_80_report_html.py`, depois
   `check_data.py --local`. É a única forma de saber se a mudança bate com
   os dados reais antes do CI dizer.
3. **Nunca reintroduza `text/` ou `pdf/` no git.** Saíram do controle de
   versão de propósito (texto e PDF de terceiros, não redistribuível — ver
   `text/README.md`, `pdf/README.md`). Um `git add`/`git status` mostrando
   arquivo novo ali é esperado (é onde o pipeline escreve) — não é uma
   mudança para stagear.
4. **`status` é o estado automático de acesso** (`fechado`, `oa_baixavel`,
   `oa_bloqueado`, `tem_texto`, `texto_parcial`, `texto_incorreto`,
   `evidencia_insuficiente`…, `sem_doi`, `so_scholar` — ver
   `auditlib.STATUS`) — os portões (`audit_30`/`audit_32`) o recalculam a
   cada rodada. **`aresta_falsa` é veredito manual terminal**: PDF obtido e
   verificado, o citante não cita o artigo em lugar nenhum. Os portões devem
   pular status terminal, nunca sobrescrevê-lo de volta para `tem_texto` — é
   exatamente o bug que o commit "aresta_falsa vira veredito terminal"
   corrigiu; não o reintroduza ao editar `audit_30`/`audit_32`.
5. **A história será reescrita antes da publicação** (as rodadas antigas
   commitaram `text/`/`pdf/` inteiros — isso sai via `git filter-repo` num
   passo futuro, separado). Até lá: nunca rode `git filter-repo` por conta
   própria, e nunca faça `git rm --cached` para "consertar" um arquivo de
   `text/`/`pdf/` que reapareça no índice por engano de um merge/rebase —
   devolva o índice ao estado do `.gitignore` atual (o arquivo já deveria
   estar ausente do índice; se está presente, algo mais cedo no histórico
   precisa de correção, não uma remoção pontual).

## Coisas que parecem melhoria mas são violação de política

- **Recontar a população ou o denominador do estudo por conta própria.**
  As definições em METHOD.md (denominador = citações com DOI; população =
  DOI + editora estabelecida + artigo de periódico) são decisão de escopo
  registrada, não um filtro a "otimizar". Mudar o critério é uma proposta de
  método, não uma correção de bug.
- **Adicionar dependência Python ao pipeline** (`tools/` é stdlib pura +
  `pdftotext`, de propósito — ver `tools/README.md`). As duas pins em
  `requirements.txt` servem só à fase 81 (figuras), reservada e ainda não
  escrita.
- **Rodar os scripts de coleta (fase 10–22) sem necessidade.** Tocam rede
  (OpenAlex, Semantic Scholar, OpenCitations, Europe PMC, Unpaywall,
  Crossref) e podem mudar `data/master.json` sob você — prefira o bloco B
  (offline) para qualquer verificação que não precise de dado novo.

## Fluxo de trabalho

- **Branch → PR → CI verde → merge.** Estilo de commit:
  `tipo(escopo): resumo`, escopos `tools data method readme report ci` (ver
  CONTRIBUTING.md). Uma correção de número é sempre `fix`.
- Antes de abrir o PR: `pre-commit run --all-files`.
- `data/classify.json` não é marcado `linguist-generated` (ver
  `.gitattributes`) — o diff de uma nova classificação precisa ficar
  legível em revisão, célula por célula da mudança.
