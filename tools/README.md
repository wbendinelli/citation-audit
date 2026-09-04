# tools/

Pipeline de auditoria de citações. Todo script é `python3 tools/audit_NN_nome.py`,
stdlib pura (nenhuma dependência externa de Python) + `pdftotext` do poppler
(`brew install poppler`) para os scripts que extraem PDF — exceto a fase 60
(análises), onde `audit_62_irr_stats.py` usa `numpy` (ver a nota no fim de
"Scripts" abaixo).

`auditlib.py` não é um script — é a biblioteca compartilhada (caminhos,
carregadores/gravadores de `data/*.json`, helpers de rede e texto, e as
constantes de taxonomia `TAXONOMIA`/`TAXONOMIA_V2`/`STATUS`) que todo
`audit_*.py` importa.

## Fases

A numeração do script é `NN_nome`, onde `NN` é a fase:

| Fase | Nome | O que faz |
|---|---|---|
| 10 | colheita | monta e funde o grafo de citações (APIs + Google Scholar) |
| 20 | texto | baixa PDF/HTML/XML e extrai o texto de cada citante OA |
| 30 | integridade | valida que o texto baixado é do artigo certo e localiza a passagem citante |
| 40 | periódicos | metadados de cada veículo citante e o tier (proxy OpenAlex / quartil Scimago) |
| 50 | pendências | deriva CSVs de trabalho a partir do estado atual (o que falta, por quê) |
| 60 | análises | taxonomia v2 (`audit_60`), pacote cego e estatísticas de confiabilidade entre codificadores (`audit_61`/`audit_62`); demais análises de ROADMAP.md ainda reservadas |
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
| `audit_50_pending.py` | 50 | `data/master.json`, `data/classify.json`, `data/journals.json`, `data/decisoes_scimago.json`, `config.json` | `data/derived/pendencias.csv`, `data/derived/sem_quartil.csv` | sim |
| `audit_60_taxonomy_v2.py` | 60 | `data/classify.json`, `data/classify_orfas.json`, `data/master.json`, `METHOD.md` | `data/classify.json`, `data/classify_orfas.json`, `data/taxonomy_v2.json` | não¹ |
| `audit_61_irr_pack.py` | 60 | `data/classify.json` (v2), `data/master.json`, `data/claims/claims.json`, `METHOD.md`, `config.json`, `data/claims/source_text/*.txt` | `data/irr/pack_blind.json`, `pack_key.json`, `instructions.md`, `irr_c1_from_v2.json` | não² |
| `audit_62_irr_stats.py` | 60 | JSON de codificador (`--c1`/`--c2`/`--c3`/`--human`), `data/irr/pack_key.json` | `--out` (estatísticas de concordância) | não³ |
| `audit_80_report_html.py` | 80 | `data/master.json`, `data/classify.json`, `data/journals.json`, `config.json`, `data/scholar/*.txt` | `report/index.html` | sim |
| `audit_70_numbers.py` | 70 | Única fonte de todo número do relatório: lê `data/*.json` e escreve `reports/01-impacto/dados.json` + `numeros.txt` (seções `== audit_70 §chave ==`); `--check` exige byte-igualdade; blocos opcionais saem `PENDENTE: motivo` |

`--check` nunca escreve: renderiza/computa em memória e compara com o que já
está commitado, saindo com código 1 se houver diferença.

¹ `audit_60_taxonomy_v2.py` não tem `--check` — é migração de uso pontual
(v1 -> v2), não derivação recorrente. Tem `--dry-run` (não grava, só imprime
distribuições e a checagem de round-trip) e `--force` (re-migra um
`classify.json` já em v2, a partir de `prov.migrated_from_v1`; recusa se
alguma entrada já foi adjudicada).
² `audit_61_irr_pack.py` tem `--audit` em vez de `--check`: não gera pacote
novo, só audita o pacote já gravado em `data/irr/` por vazamento de
identidade (DOI, veículo, ano junto de "et al.", palavras de rótulo fora das
passagens) — sai com código 1 se achar algum.
³ `audit_62_irr_stats.py` tem `--selftest` em vez de `--check`: roda os casos
de referência publicados (Krippendorff 2011, κ de Cohen de livro-texto,
identidades de PABAK/AC1/PPI) e, se o pacote já existir em `data/irr/`,
codificador-1 contra si mesmo — sem argumento nenhum sobre dado real.

Fase 60 (`audit_60`/`audit_61`/`audit_62`) é a única exceção ao stdlib-puro:
`audit_62_irr_stats.py` importa `numpy` (pin em `requirements.txt`, já usada
por essa fase — ver CLAUDE.md). `audit_60` e `audit_61` continuam stdlib
pura.

`tools/check_data.py` não segue a numeração de fase — não deriva nada, só
valida. Lê `data/master.json`, `data/classify.json`, `data/classify_orfas.json`,
`data/journals.json` e `data/decisoes_scimago.json`; sem `--local` roda em
segundos (só `data/*.json`); com `--local` também confere `text/*.txt` contra
`text_path` (mais lento). Sai com código 1 e uma mensagem por violação; código
0 com um resumo de uma linha. Órfãos de `text/` e grupos de arquivo
byte-idênticos são avisos, não violação — só falha se um `text_path`
referenciado não existir em disco ou o arquivo não contiver o título do
registro. Ver o cabeçalho do script para a lista completa das 8 invariantes.

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
python3 tools/audit_50_pending.py
python3 tools/audit_80_report_html.py
```

Depois de A ou B, valide os dados com `python3 tools/check_data.py` (e
`--local` se `text/` também mudou).

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
