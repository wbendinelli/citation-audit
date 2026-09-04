# citation-audit

[![CI](https://github.com/wbendinelli/citation-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/wbendinelli/citation-audit/actions/workflows/ci.yml)
[![canary](https://github.com/wbendinelli/citation-audit/actions/workflows/canary.yml/badge.svg)](https://github.com/wbendinelli/citation-audit/actions/workflows/canary.yml)
[![Code: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)
[![Content: CC BY-SA 4.0](https://img.shields.io/badge/content-CC%20BY--SA%204.0-lightgrey.svg)](LICENSE-CC-BY-SA-4.0.md)

Auditoria da **qualidade** das citações recebidas por dois artigos — quem
usou o trabalho de verdade, quem citou de passagem, quem citou errado. A
pergunta não é "quantos me citaram", é "quem me usou de verdade".

Os números deste README são conferidos por `tools/check_numbers.py` — a
partir da próxima etapa (fase 70, ver [ROADMAP.md](ROADMAP.md)); até lá, cada
um é rastreável a um script ou tabela commitados, apontados abaixo.

## §1 — Os dois artigos

| Chave | Artigo | Periódico | DOI |
|---|---|---|---|
| `airline` | Airline delays, congestion internalization and non-price spillover effects of low cost carrier entry (2016) | Transportation Research Part A: Policy and Practice | [`10.1016/j.tra.2016.01.001`](https://doi.org/10.1016/j.tra.2016.01.001) |
| `grains` | What are the main factors that determine post-harvest losses of grains? (2019) | Sustainable Production and Consumption | [`10.1016/j.spc.2019.09.002`](https://doi.org/10.1016/j.spc.2019.09.002) |

Fonte: `config.json › papers`.

## §2 — Resultado em uma tela

- **176** citações mapeadas — união de quatro APIs (OpenAlex, Semantic
  Scholar, OpenCitations, Europe PMC) + listas completas do Google Scholar
  (`python3 tools/check_data.py`)
- **147** com DOI depositado — o denominador de toda taxa de cobertura
  (METHOD.md §8)
- **104** com passagem recuperada e classificadas em `data/classify.json`
  (`python3 tools/check_data.py`)
- **93** periódicos citantes distintos (`data/journals.json`), dos quais
  **70** casaram com o Scimago Journal Rank 2025 (METHOD.md §10)
- **87** citações na população do estudo — DOI + editora estabelecida +
  artigo de periódico, 49 do artigo de aviação e 38 do de grãos
  (METHOD.md §9)
- **98** registros com DOI cujo periódico tem quartil Scimago oficial,
  qualquer tipo de documento (METHOD.md §12)

## §3 — Como reproduzir

**A — nova edição do inventário** (toca rede: OpenAlex, Semantic Scholar,
OpenCitations, Europe PMC, Unpaywall, Crossref, e download dos citantes OA).

```bash
python3 tools/audit_10_harvest.py
python3 tools/audit_11_triage.py
python3 tools/audit_13_resolve_scholar.py
python3 tools/audit_20_download.py
python3 tools/audit_21_download_deep.py
python3 tools/audit_22_retry_all.py
python3 tools/audit_40_journals.py
```

**B — derivação offline** (só `data/`, `text/` e `config.json` locais;
seguro rodar quantas vezes quiser).

```bash
python3 tools/audit_12_merge_scholar.py
python3 tools/audit_30_validate_texts.py
python3 tools/audit_31_passages.py
python3 tools/audit_32_gate_bibonly.py
python3 tools/audit_41_scimago.py
python3 tools/audit_50_pending.py
python3 tools/audit_80_report_html.py
```

Depois de A ou B: `python3 tools/check_data.py` (e `--local` se `text/`
também mudou). Detalhe de cada script — o que lê, o que escreve, se tem
`--check` — em [`tools/README.md`](tools/README.md).

## §4 — Mapa do repositório

| Caminho | O que é |
|---|---|
| [`tools/`](tools/) | o pipeline — um script por fase, biblioteca compartilhada em `auditlib.py` |
| [`config.json`](config.json) | os dois artigos, a lista de editoras estabelecidas, os metadados do Scimago |
| `data/` | `master.json` (o grafo de citações), `classify.json` (as classificações com evidência), `journals.json` (periódicos + tier), `decisoes_scimago.json`, `data/claims/` (afirmações dos dois artigos), `data/derived/` (CSVs de trabalho gerados) |
| [`text/`](text/), [`pdf/`](pdf/) | texto e PDF completos dos citantes, extraídos localmente — fora do git, não redistribuível (ver os READMEs de cada um) |
| [`report/index.html`](report/index.html) | dashboard HTML gerado por `audit_80_report_html.py` |
| `reports/01-impacto/` | *(planejado — ver ROADMAP.md)* o relatório Typst |
| [`METHOD.md`](METHOD.md) | taxonomia, regra de evidência, portões de integridade, definições de escopo |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | régua de evidência, setup, estilo de commit |
| [`CLAUDE.md`](CLAUDE.md) | manual de operação para agentes de código |
| [`CHANGELOG.md`](CHANGELOG.md) / [`ROADMAP.md`](ROADMAP.md) | o que mudou / o que falta |

## §5 — Regra de evidência

Nenhuma classificação sem a passagem literal do texto citante. Citação sem
evidência recuperada fica fora de toda contagem — não é "ruim", é "não
lida". A taxonomia (ROLE/STANCE/REUSE/CITATION_STATUS), os três portões de
integridade e os casos de fronteira do codebook estão em
[METHOD.md](METHOD.md).

## §6 — Limites

- **"Editora estabelecida" é proxy grosso para relevância** — Scopus/Web of
  Science com quartil seria critério mais defensável (ROADMAP.md).
- **O tier de periódico não é normalizado por área** — comparar aviação com
  agronomia pelo quartil Scimago é comparar réguas diferentes (METHOD.md
  §10).
- **A evidência é mais densa em Q1** — efeito colateral de o Elsevier
  (concentra os Q1 das duas áreas) ter liberado acesso institucional
  enquanto Emerald e Wiley não liberaram; as estatísticas de Q4 se apoiam em
  1 observação (METHOD.md §13).
- **Overton (citação em documento de política) só existe por periódico**,
  não por artigo — o dado por artigo exigiria a base paga ou busca dirigida
  (METHOD.md §11, ROADMAP.md).
- **18 citações seguem pendentes** por bloqueio de acesso, majoritariamente
  Emerald e Wiley (ROADMAP.md).

## Citação

Ver [`CITATION.cff`](CITATION.cff) — o GitHub renderiza um botão "Cite this
repository" a partir dele.

## Licença

**MIT** para código — `tools/`, `config.json`, `.github/` (ver
[LICENSE](LICENSE)). **CC BY-SA 4.0** para prosa — este README, METHOD.md,
ROADMAP.md, as notas em `data/classify.json` e o texto de
`report/index.html` (ver [LICENSE-CC-BY-SA-4.0.md](LICENSE-CC-BY-SA-4.0.md)).

Três ressalvas: as passagens citadas em `data/classify.json` pertencem aos
seus próprios autores — são citação de escopo limitado (direito de citação),
não conteúdo deste repositório relicenciado; os dados do OpenAlex usados no
grafo de citações são CC0; os dados do Scimago seguem os termos do próprio
Scimago e não são redistribuídos (ver [`data/scimago/README.md`](data/scimago/README.md)).
