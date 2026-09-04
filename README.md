# citation-audit

Auditoria da **qualidade** das citações recebidas — quem usou o trabalho de verdade,
quem citou de passagem, quem citou errado.

Ver [METHOD.md](METHOD.md) para a taxonomia e a regra de evidência.

## Artigos auditados

| Chave | Artigo | DOI | Citações |
|---|---|---|---|
| `airline` | Airline delays, congestion internalization and non-price spillover effects of low cost carrier entry | `10.1016/j.tra.2016.01.001` | 53 |
| `grains` | What are the main factors that determine post-harvest losses of grains? | `10.1016/j.spc.2019.09.002` | 60 |

## Estado atual

- **176** citações mapeadas (união de quatro APIs + listas completas do Google Scholar)
- **33** com passagem recuperada e classificadas
- **124** pendentes, das quais 70 fechadas e 24 sem DOI depositado

Pendências listadas em [`data/pending_downloads.csv`](data/pending_downloads.csv),
com DOI, link e nome de arquivo de destino.

## Pipeline

```
pipeline/01_inventory.py        grafo de citações + rotas de texto completo
pipeline/02_fetch.py            download e extração (pdftotext / XML / HTML)
pipeline/03_fetch_fallback.py   rotas alternativas
pipeline/04_passages.py         localiza a passagem citante
pipeline/05_report.py           gera report/index.html
pipeline/06_merge_scholar.py    cruza as listas do Scholar com o inventário
pipeline/07_resolve_scholar.py  resolve DOI dos exclusivos do Scholar via Crossref
```

Classificação em `data/classify.json`, feita com a passagem literal em mãos.

## Requisitos

Python 3.8+ e `pdftotext` (`brew install poppler`). Sem dependências externas de
Python, sem chave de API, sem conta.

## Como adicionar PDFs obtidos manualmente

Baixe pelo seu acesso institucional, salve com o nome indicado na coluna
`arquivo_destino` do CSV, dentro de `pdf/`, e rode `04_passages.py` de novo.

Download avulso e manual. Coleta automatizada através de proxy institucional viola os
termos dos publishers e costuma derrubar o acesso da instituição inteira.

## Fontes do grafo de citação

A união de quatro índices, deduplicada por DOI e por título normalizado:

| Fonte | airline | grains |
|---|---|---|
| OpenAlex | 53 | 60 |
| Semantic Scholar | 49 | 54 |
| OpenCitations | 39 | 50 |
| Europe PMC | 0 | 0 |
| **União** | **69** | **62** |

O Google Scholar reporta 95 e 76. As listas completas foram paginadas e estão em
`scholar/*.txt` (título truncado em ~76 chars + ano, como o Scholar entrega).

O cruzamento: o Scholar confirmou 118 registros que as APIs já tinham, acrescentou 45,
e as APIs por sua vez acharam registros que o Scholar não lista. **A união dá 176** —
mais do que qualquer fonte isolada. Dos 45 exclusivos do Scholar, 21 foram resolvidos
a DOI via Crossref; os 24 restantes são tese, capítulo de livro e periódico sem DOI.

## Etapas

```
pipeline/00_harvest.py          união multi-fonte do grafo de citação
pipeline/01_triage.py           enriquecimento + classificação de acesso
pipeline/02_download.py         download OA e extração de texto
pipeline/03_download_deep.py    varredura de todas as localizações OA
pipeline/04_passages.py         localização da passagem citante
pipeline/05_report.py           gera report/index.html
pipeline/06_merge_scholar.py    cruza as listas do Scholar com o inventário
pipeline/07_resolve_scholar.py  resolve DOI dos exclusivos do Scholar via Crossref
```
