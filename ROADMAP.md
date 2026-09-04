# ROADMAP

O que falta para fechar a auditoria além do que já está em `tools/` — cada
análise planejada com o nome de script reservado para ela, na numeração por
fase de [`tools/README.md`](tools/README.md#fases).

## Análises planejadas

| Script reservado | Fase | O que faz |
|---|---|---|
| `audit_60_taxonomy_v2.py` | 60 | segunda passada da taxonomia ROLE/STANCE/REUSE sobre as classificações existentes — fecha os casos de fronteira que o codebook v1 deixou em aberto |
| `audit_61_irr_pack.py` | 60 | empacota uma amostra de citações já classificadas para um segundo codificador, sem revelar o veredito original |
| `audit_62_irr_stats.py` | 60 | calcula a concordância entre codificadores (kappa) sobre o pacote do 61 |
| `audit_63_claim_map.py` | 60 | cruza `data/claims/claims.json` (as 63 afirmações dos dois artigos) com as passagens citantes — qual citação invoca qual afirmação específica |
| `audit_64_refs_audit.py` | 60 | audita as listas de referência dos dois artigos (`data/cd/refs_pdf_*.json`, 26 + 45 entradas) — DOI resolvível, autocitação, dependência da literatura de base |
| `audit_65_cd_index.py` | 60 | índice de distância de citação a partir de `data/cd/` |
| `audit_66_cocitation.py` | 60 | co-citação a partir das sementes em `data/cocit/` (particionadas por seção do artigo original, ex. `seeds_airline.json`) |
| `audit_67_ghost_audit.py` | 60 | audita especificamente as citações-fantasma verificadas (`flag: ghost`) — o que elas têm em comum |
| `audit_68_base_rates.py` | 60 | taxa-base de cada função de citação, para comparar contra a literatura (CiTO, Teufel et al., os *intents* do Semantic Scholar) |
| `audit_70_numbers.py` | 70 | extrai todo número impresso pelos scripts commitados, para `tools/check_numbers.py` conferir contra a prosa (ver nota no README) |
| `audit_81_figures.py` | 80 | os gráficos do relatório (as duas pins de `requirements.txt` existem só para esta fase) |
| `audit_82_readme_svgs.py` | 80 | os diagramas SVG do README |

Mais o relatório escrito — Typst, em `reports/01-impacto/`, no mesmo padrão
de `reports/` que outros repositórios SAPIANS usam para o deliverable final
(prosa + `.bib` + PDF compilado), diferente do dashboard HTML que
`audit_80_report_html.py` já gera em `report/index.html`.

## Em aberto

- **18 citações pendentes por editora**: Emerald 4, Wiley 4, Hindawi 2,
  Springer 2, Inderscience 3, ASABE 1, *Journal of Aerospace Technology and
  Management* 1, *Agricultural Economics* 1 — ver METHOD.md, cobertura por
  quartil. Bloqueio de acesso na maioria; dois casos (JATM, *Agricultural
  Economics*) são de acesso relativamente aberto e merecem nova tentativa.
- **`grains_050` para classificar** — `evidencia_insuficiente`, ainda fora
  de `data/classify.json`.
- **Validação pelo autor de `data/claims/claims.json`** — 63 afirmações,
  `validated_by_author: false` em todas; até a validação, o registro vale
  como leitura de segundo codificador, não como afirmação confirmada.
- **Overton por artigo** — o CSV do Scimago só dá o sinal por periódico (41
  dos 70 periódicos casados têm citação em documento de política); o dado
  por artigo exige a base Overton paga, ou busca dirigida nos repositórios
  de FAO, Banco Mundial, OCDE, Embrapa e CONAB.
- **Scopus/WoS como critério alternativo de população** — "editora
  estabelecida" (METHOD.md) é proxy grosso para relevância; indexação em
  Scopus ou Web of Science com quartil seria critério mais defensável, se a
  análise final exigir.
- **Segunda edição da colheita** — re-rodar o bloco A
  (`tools/README.md#como-rodar`) para capturar citações novas desde a
  primeira colheita.
