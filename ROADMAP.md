# ROADMAP

O que falta para fechar a auditoria além do que já está em `tools/` — cada
análise planejada com o nome de script reservado para ela, na numeração por
fase de [`tools/README.md`](tools/README.md#fases).

## Análises planejadas

**Entregues:** `audit_60_taxonomy_v2.py`, `audit_61_irr_pack.py` e
`audit_62_irr_stats.py` (fase 60) — migração para o codebook v2 de três
eixos ortogonais, pacote cego e estatísticas de confiabilidade entre
codificadores. Ver [`tools/README.md`](tools/README.md#scripts) e
METHOD.md §16–§17; a coleta de rótulos do segundo e do terceiro
codificador está em andamento, resultado ainda não preenchido em
`data/irr/`.

| Script reservado | Fase | O que faz |
|---|---|---|
| `audit_63_claim_map.py` | 60 | cruza `data/claims/claims.json` (as 63 afirmações dos dois artigos) com as passagens citantes — qual citação invoca qual afirmação específica |
| `audit_64_refs_audit.py` | 60 | audita as listas de referência dos dois artigos (`data/cd/refs_pdf_*.json`, 26 + 45 entradas) — DOI resolvível, autocitação, dependência da literatura de base |
| `audit_65_cd_index.py` | 60 | índice de distância de citação a partir de `data/cd/` |
| `audit_66_cocitation.py` | 60 | co-citação a partir das sementes em `data/cocit/` (particionadas por seção do artigo original, ex. `seeds_airline.json`) |
| `audit_67_ghost_audit.py` | 60 | audita especificamente as citações-fantasma verificadas (`flag: ghost`) — o que elas têm em comum |
| `audit_68_base_rates.py` | 60 | taxa-base de cada função de citação, para comparar contra a literatura (CiTO, Teufel et al., os *intents* do Semantic Scholar) |
| `audit_70_numbers.py` | 70 | extrai todo número impresso pelos scripts commitados, para `tools/check_numbers.py` conferir contra a prosa (ver nota no README) |
| `audit_81_figures.py` | 80 | os gráficos do relatório (as duas pins de `requirements.txt` também servem a esta fase — a fase 60 já usa `numpy`, ver CLAUDE.md) |
| `audit_82_readme_svgs.py` | 80 | os diagramas SVG do README |

Mais o relatório escrito — Typst, também em `reports/01-impacto/`, no mesmo
padrão de `reports/` que outros repositórios SAPIANS usam para o
deliverable final (prosa + `.bib` + PDF compilado), ao lado de
`dados.json`/`numeros.txt` (fonte única de números, `audit_70_numbers.py`)
e do dashboard HTML que `audit_80_report_html.py` já gera em
`reports/01-impacto/index.html`.

## Em aberto

- **17 citações pendentes por editora** (lista `cobertura_quartil.pendentes`
  do `dados.json`): Emerald 4, Inderscience 3, Wiley 3, Hindawi 2, Springer 2, De Gruyter 1, Academia Tcheca de Ciências Agrárias (*Agricultural Economics*) 1, ASABE 1. Bloqueio de acesso na maioria; o tcheco
  *Agricultural Economics* é de acesso relativamente aberto e merece nova
  tentativa. A contagem anterior (18) somava a aresta falsa `grains_s001`.
- **Dedup do `audit_12_merge_scholar` para registros `s`-prefixados** (caso
  `airline_s001`): revisar a regra antes da segunda colheita, para um registro
  do Scholar já resolvido a DOI não voltar como duplicata.
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

## Entregues em 2026-09-04 (fase de análises)

- `audit_63_adjudicate`, `audit_67_ghost_audit`, `audit_68_base_rates`; teste cego e colegiado completos (METHOD §17–§18).
- Auditoria de referências (`data/cd/refs_audit_*.json`); `audit_64/65/66` rodados pelo backend Semantic Scholar (CD nos dois artigos, co-citação em aviação).

- `audit_70_numbers` (fonte única de número), `audit_81_figures` (14 figuras), `audit_82_readme_svgs` (4 SVGs), `audit_80` lendo `dados.json` e escrevendo `reports/01-impacto/index.html`; relatório técnico `reports/01-impacto/main.typ` compilado, com §6 (CD e co-citação) reservada até o backend Semantic Scholar fechar.

## Pendências abertas pela fase de análises

- **Validação pelo autor** das 63 afirmações (`data/claims/claims.json`, `validated_by_author: false`) — o registro foi extraído por modelo e usado como verdade pelos codificadores; a validação humana é o que falta para fechar o argumento.
- **Codificação humana (H1/H2)** prevista em §17: 30 itens às cegas pelo autor e adjudicação humana das discordâncias. Os papéis foram preenchidos por painel de modelos; a versão humana substitui, não soma.
- **Persistir os corpos lidos por SSO**: 11 dos 12 vereditos de fantasma repousam em leitura documentada no navegador, não em arquivo em `text/`. Refazer a leitura salvando o corpo torna a auditoria 67 reproduzível.
- **Números da literatura marcados `verification_status: pendente`** em `data/base_rates.json`: conferir na fonte primária antes de citar (Boyack 2018 1,4%; Jergas & Baethge 2015 maior/menor; Moravcsik 1975).
- **Índice CD e co-citação pelo OpenAlex**: re-rodar `audit_65`/`audit_66` com `--backend openalex` quando houver cota e comparar com o Semantic Scholar (S2 conta 8–10% menos citantes; a divergência entre bases é ela própria um resultado, Leibel & Bornmann 2024).
- **Sensibilidade de profundidade** (D1 do codebook v2.1): reportar `foundational` com a leitura de texto completo de c1 nos 26 itens de janela automática.
