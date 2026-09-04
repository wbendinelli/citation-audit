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

- **113** citações mapeadas
- **31** com passagem recuperada e classificadas
- **82** pendentes — 33 são open access (falha de coleta, recuperável) e 49 exigem acesso institucional

Pendências listadas em [`data/pending_downloads.csv`](data/pending_downloads.csv),
com DOI, link e nome de arquivo de destino.

## Pipeline

```
pipeline/01_inventory.py        grafo de citações + rotas de texto completo
pipeline/02_fetch.py            download e extração (pdftotext / XML / HTML)
pipeline/03_fetch_fallback.py   rotas alternativas
pipeline/04_passages.py         localiza a passagem citante
pipeline/05_report.py           gera report/index.html
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
