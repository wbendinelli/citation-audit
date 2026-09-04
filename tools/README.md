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
| 70 | números | fonte única de todo número do relatório (`audit_70_numbers.py`) |
| 80 | saídas | gera `reports/01-impacto/index.html` a partir de `dados.json` |

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
| `openalex_client.py` | 60 | Cliente OpenAlex com cache em `data/cache/openalex/`, `mailto`, paginação por cursor e contagem de requisições; sem `None` em cache |
| `s2_client.py` | 60 | Cliente Semantic Scholar (backend alternativo quando a cota de lista do OpenAlex zera): cache em `data/cache/s2/`, ritmo 1,1 s, recuo em 429, mapa OpenAlex→S2 por DOI/título com piso de similaridade |
| `audit_64_refs_audit.py` | 64 | Casa as referências do OpenAlex com a lista do PDF (`data/cd/refs_pdf_*.json`) e escreve `data/cd/refs_audit_*.json` com `matched / repaired / false_reference / unresolvable` — pré-requisito do CD |
| `audit_65_cd_index.py` | 65 | Índice CD (t = 1, 3, 5, 10), CD_nok, DI2, DI5, variante Holst, bootstrap, *leave-one-reference-out* e cruzamento n_i/n_j × profundidade; `--backend {openalex,s2}`; escreve `data/cd/cd_*.json` |
| `audit_66_cocitation.py` | 66 | Co-citação antes/depois das duas vertentes do artigo de aviação (seeds em `data/cocit/seeds_airline.json`): share A–B, Jaccard, Salton, *brokerage share*, Fisher, permutação, placebos; escreve `data/cocit/{cocit,universe}_airline.json` |
| `audit_70_numbers.py` | 70 | `config.json`, `data/*.json` — única fonte de todo número que o relatório pode citar | `reports/01-impacto/dados.json`, `numeros.txt` (seções `== audit_70 §chave ==`) | sim⁴ |
| `audit_80_report_html.py` | 80 | `data/master.json`, `data/classify.json`, `reports/01-impacto/dados.json` | `reports/01-impacto/index.html` | sim⁵ |
| `audit_81_figures.py` | 81 | Catorze figuras de medida em `reports/01-impacto/figuras/` lendo só `dados.json`, via `sapians.mplstyle` e fontes vendorizadas; `--check` compara bytes e afirma regras da casa (barras do zero, sem `twinx`, ≤5 cores). Roda no venv pinado (`.venv/bin/python`) |
| `audit_82_readme_svgs.py` | 82 | Quatro SVGs didáticos em `docs/assets/` (pipeline, funil, taxonomia, portões); só o funil lê números, do `dados.json`; `--check` compara bytes |

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
⁴ `audit_70_numbers.py` também aceita `--root PATH` (raiz onde lê
`config.json`/`data/`; a saída cai sempre em
`<pasta do script>/../reports/01-impacto/`, independente de `--root`) e
`--classify PATH` (override de `data/classify.json`). Bloco opcional cujo
arquivo-fonte falta (ou está auto-invalidado) não vira erro: sai como
`{"pendente": true, "motivo": ...}` em `dados.json` e uma linha `PENDENTE:
motivo` em `numeros.txt` — `--check` continua exigindo byte-igualdade com o
que está commitado, PENDENTE incluso.
⁵ `audit_80_report_html.py` também aceita `--root PATH` (raiz do
repositório; padrão inferido de `__file__`, como `auditlib.ROOT`) — governa
de onde `data/master.json`, `data/classify.json` e
`reports/01-impacto/dados.json` são lidos e onde
`reports/01-impacto/index.html` é gravado, todos juntos (diferente do
`--root` de `audit_70_numbers.py`, que não afeta onde a saída cai).

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
python3 tools/audit_70_numbers.py
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
