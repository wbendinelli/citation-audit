# tools/

Pipeline de auditoria de citações. Todo script é `python3 tools/audit_NN_nome.py`,
stdlib pura (nenhuma dependência externa de Python) + `pdftotext` do poppler
(`brew install poppler`) para os scripts que extraem PDF.

`auditlib.py` não é um script — é a biblioteca compartilhada (caminhos,
carregadores/gravadores de `data/*.json`, helpers de rede e texto, e as
constantes de taxonomia `TAXONOMIA`/`STATUS`) que todo `audit_*.py` importa.

## Fases

A numeração do script é `NN_nome`, onde `NN` é a fase:

| Fase | Nome | O que faz |
|---|---|---|
| 10 | colheita | monta e funde o grafo de citações (APIs + Google Scholar) |
| 20 | texto | baixa PDF/HTML/XML e extrai o texto de cada citante OA |
| 30 | integridade | valida que o texto baixado é do artigo certo e localiza a passagem citante |
| 40 | periódicos | metadados de cada veículo citante e o tier (proxy OpenAlex / quartil Scimago) |
| 50 | pendências | deriva CSVs de trabalho a partir do estado atual (o que falta, por quê) |
| 60 | análises | *(reservado — nenhum script ainda)* |
| 70 | números | *(reservado — nenhum script ainda)* |
| 80 | saídas | gera `report/index.html` |

## Scripts

| Script | Fase | Lê | Escreve | `--check`? |
|---|---|---|---|---|
| `audit_10_harvest.py` | 10 | `config.json`; OpenAlex, Semantic Scholar, OpenCitations, Europe PMC | `data/master.json` | não |
| `audit_11_triage.py` | 10 | `data/master.json`, `config.json`; OpenAlex, Unpaywall | `data/master.json` | não |
| `audit_12_merge_scholar.py` | 10 | `data/master.json`, `data/scholar/*.txt` | `data/master.json` | não |
| `audit_13_resolve_scholar.py` | 10 | `data/master.json`, `config.json`; Crossref, OpenAlex | `data/master.json` | não |
| `audit_20_download.py` | 20 | `data/master.json` | `data/master.json`, `text/*.txt`, `pdf/*.pdf` | não |
| `audit_21_download_deep.py` | 20 | `data/master.json`, `config.json`; OpenAlex | `data/master.json`, `text/*.txt`, `pdf/*.pdf` | não |
| `audit_22_retry_all.py` | 20 | `data/master.json`, `config.json`; OpenAlex, Unpaywall | `data/master.json`, `text/*.txt`, `pdf/*.pdf` | não |
| `audit_30_validate_texts.py` | 30 | `data/master.json`, `config.json`, `text/*.txt` | `data/master.json` | não |
| `audit_31_passages.py` | 30 | `data/master.json`, `config.json`, `data/classify.json`, `text/*.txt` | `data/master.json` | não |
| `audit_32_gate_bibonly.py` | 30 | `data/master.json`, `config.json`, `data/classify.json`, `text/*.txt` | `data/master.json` | não |
| `audit_40_journals.py` | 40 | `data/master.json`, `config.json`; OpenAlex | `data/master.json`, `data/journals.json` | não |
| `audit_41_scimago.py` | 40 | `data/journals.json`, `data/scimago/scimagojr_2025.csv` | `data/journals.json` | sim |
| `audit_80_report_html.py` | 80 | `data/master.json`, `data/classify.json`, `data/journals.json`, `config.json`, `data/scholar/*.txt` | `report/index.html` | sim |

`--check` nunca escreve: renderiza/computa em memória e compara com o que já
está commitado, saindo com código 1 se houver diferença.

## Como rodar

**A — nova edição do inventário (toca rede: OpenAlex, Semantic Scholar,
OpenCitations, Europe PMC, Unpaywall, Crossref, e download dos citantes OA).**

```
python3 tools/audit_10_harvest.py
python3 tools/audit_11_triage.py
python3 tools/audit_13_resolve_scholar.py
python3 tools/audit_20_download.py
python3 tools/audit_21_download_deep.py
python3 tools/audit_22_retry_all.py
python3 tools/audit_40_journals.py
```

**B — derivação offline (só `data/`, `text/` e `config.json` locais; seguro
rodar quantas vezes quiser).**

```
python3 tools/audit_12_merge_scholar.py
python3 tools/audit_30_validate_texts.py
python3 tools/audit_31_passages.py
python3 tools/audit_32_gate_bibonly.py
python3 tools/audit_41_scimago.py
python3 tools/audit_80_report_html.py
```

## Por que os portões de integridade existem

`audit_30_validate_texts.py` e `audit_32_gate_bibonly.py` vieram de reparos de
uso único do round anterior (`repairs/11_validate_texts.py` e
`repairs/12_gate_bibonly.py`), escritos em reação a erro real encontrado nos
dados — e continuam valendo como portão a cada coleta nova, não só como
correção pontual:

- **`audit_30`** — 5 arquivos de texto eram de outro artigo (colisão de nome
  no re-arquivamento da 1ª rodada). O portão exige que o texto contenha o
  próprio título do registro; senão desvincula.
- **`audit_32`** — 8 vereditos de "só na bibliografia" eram falsos: o
  documento era página de rosto de publisher, sem o corpo, não prova de
  citação-fantasma. O portão exige corpo comprovado para confirmar fantasma.

Um terceiro reparo, `repairs/10_repair_texts.py` (re-arquivava por DOI os
textos nomeados pelos IDs antigos da 1ª rodada), era estritamente de
uso único — já foi aplicado e não tem script correspondente em `tools/`.
