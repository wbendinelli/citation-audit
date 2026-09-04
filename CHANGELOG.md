# Changelog

Mudanças notáveis no repositório. Entradas citam a mensagem do commit pelo
**assunto**, nunca pelo hash — o histórico será reescrito (`git filter-repo`,
para tirar `text/`/`pdf/` das rodadas antigas) antes da publicação, e um hash
citado aqui ficaria órfão no dia seguinte.

## 2026-09-04 — taxonomia v2 e confiabilidade entre codificadores

- **Codebook v2: três eixos ortogonais substituem `role`+`flag`.**
  `audit_60_taxonomy_v2.py` migra as 104 entradas vivas + 1 órfã de
  `data/classify.json`/`classify_orfas.json` do `role` de sete valores (mais
  uma `flag`) do codebook v1 para `presence`/`depth`/`accuracy` (+
  `distortion`, sub-códigos de Greenberg 2009) julgados independentemente,
  sem perda: a projeção inversa `auditlib.role_flag_v1()` reproduz
  `(role, flag)` em 105/105 entradas (round-trip conferido a cada migração,
  aborta se falhar). `stance` e `reuse` seguem eixos próprios; `relation`,
  `record_flags` e `highlight` (editorial, fora das estatísticas) saem do
  `role`/`flag` único do v1. `data/taxonomy_v2.json` documenta o vocabulário
  de cada eixo, as regras de migração R1–R9 e o crosswalk contra Moravcsik &
  Murugesan (1975), Teufel (2006), Jurgens et al. (2018), SciCite (Cohan et
  al. 2019), Valenzuela et al. (2015) e CiTO.
- **`check_data.py` (4) passa a validar o codebook v2**, não mais
  `role`/`stance`/`reuse`/`flag` do v1: vocabulário de `presence`/`depth`/
  `accuracy`/`distortion`/`stance`/`reuse`/`relation`/`record_flags`/
  `highlight` contra `auditlib.TAXONOMIA_V2` (conferida por sua vez contra
  `data/taxonomy_v2.json`, para os dois nunca divergirem em silêncio), a
  consistência `depth`/`accuracy` nulos sse `presence != in_text`,
  `distortion` não-nulo só quando `accuracy != accurate`, e as chaves novas
  de `prov` (`migrated_from_v1`, `migration_rules`, `adjudicated`).
- **`audit_80_report_html.py` lê role/flag via `auditlib.role_flag_v1()`**
  em vez de campo direto no topo da entrada — `report/index.html` sai
  byte-idêntico ao commitado (a mudança é de onde o dado vem, não do que é
  mostrado).
- **Fase 60 deixa de ser stdlib-pura.** `audit_62_irr_stats.py` usa `numpy`
  (já pinado em `requirements.txt`, antes reservado só à fase 81) para as
  estatísticas de concordância entre codificadores — fases 10–50 e 70–80
  continuam stdlib + `pdftotext`.
- **METHOD.md §16–§17.** §16 documenta os cinco eixos do codebook v2, os
  campos auxiliares (`relation`/`record_flags`/`highlight`), as regras de
  migração R1–R9, a garantia de round-trip (105/105) e o crosswalk contra
  Moravcsik & Murugesan 1975, Teufel 2006, Jurgens et al. 2018, SciCite 2019,
  Valenzuela et al. 2015 e CiTO. §17 registra o protocolo do teste cego de
  confiabilidade entre codificadores: pacote com as 104 entradas vivas + 10
  duplicadas como sonda intra-codificador, 4 lotes, identidade apagada
  (`audit_61_irr_pack.py`), segundo codificador (Opus) e terceiro (Sonnet)
  cada um em contexto novo lendo só o pacote, estatística por eixo (α
  ordinal de Krippendorff para `depth`; κ de Cohen + PABAK + AC1 de Gwet
  para os eixos nominais; Jaccard para `reuse`), exclusão dos 7 exemplares
  do codebook das estatísticas primárias, e inferência com poder de
  predição (PPI/PPI++). Resultados ainda pendentes — preenchidos por
  `audit_62_irr_stats.py` quando a coleta terminar.
- **Pacote cego gravado em `data/irr/`.** `audit_61_irr_pack.py` gera
  `pack_blind.json` (114 itens — 104 vivos + 10 duplicados — em 4 lotes,
  sem DOI/veículo/ano/rótulo), `pack_key.json` (a chave, nunca exposta a um
  codificador), `instructions.md` (o codebook v2 completo mais os casos de
  fronteira literais de §6) e `irr_c1_from_v2.json` (rótulos do codificador
  1, projetados do `classify.json` já migrado). `--audit` confirma 0
  vazamentos de identidade. `audit_62_irr_stats.py --selftest` passa
  16/16 (Krippendorff 2011, κ de Cohen de livro-texto, identidades de
  PABAK/AC1/PPI, e ponta a ponta c1 vs. c1). Rótulos do codificador 2
  (Opus) e do codificador 3 (Sonnet) ainda não chegaram — `data/irr/README.md`
  documenta os arquivos e o que falta.

## 2026-09-04 — reorganização SAPIANS

Oito passos que levaram o repositório do formato da auditoria original ao
padrão de engenharia SAPIANS (golden path, tier C) — cada bullet é uma
inconsistência resolvida.

- **`classificado` cai do esquema.** O campo booleano `classificado` em cada
  registro de `master.json` duplicava o que já era decidível perguntando "o
  DOI está em `classify.json`?" — 33 registros o carregavam `true` de forma
  redundante. Esquema v2 remove o campo (372 ocorrências); nenhum script lê
  mais `classificado`.
- **README.md reescrito** no padrão SAPIANS: seções `§1`–`§6` numeradas,
  badges de CI/canary/licença, e as duas licenças (MIT + CC BY-SA 4.0)
  declaradas por fronteira de conteúdo.
- **`pipeline/14_tiers.py` + `pipeline/15_scimago.py` fundidos** num único
  `tools/audit_41_scimago.py` idempotente — uma regra de tier só
  (`tier_proxy` por citedness, quartil Scimago por ISSN quando casa), com
  `--check` que valida `journals.json` sem rede nem CSV.
- **17 arquivos órfãos de `text/` estacionados** em `text/_orfaos/` — texto
  extraído que não é o `text_path` de nenhum registro (ligação perdida em
  deduplicação ou re-arquivamento), fora da verificação de órfãos mas
  preservado para re-vinculação manual.
- **12 grupos de arquivo byte-idênticos em `text/` dissolvidos** a zero: cada
  grupo tinha exatamente um membro não-órfão (a única exceção, um grupo
  formado só por dois órfãos, some inteiro) — estacionar os órfãos resolveu
  a duplicação como efeito colateral, sem tocar em nenhum arquivo vivo.
- **4 status incorretos de leitura SSO corrigidos.** `airline_002`,
  `airline_007`, `airline_051` e `grains_028` alegavam `tem_texto` sem
  arquivo correspondente em disco — fecham explicitamente; a leitura feita
  por acesso institucional (SSO) passa a morar em `classify.prov.source`,
  não em `text_path`.
- **CSVs de trabalho passam a ser gerados, não editados.**
  `tools/audit_50_pending.py` deriva `data/derived/pendencias.csv` e
  `data/derived/sem_quartil.csv` de `master`+`classify`+`journals`+
  `decisoes_scimago`, com `--check` bit-a-bit contra o commitado —
  aposentam `data/pending_downloads.csv`, `faltam_doi.csv`,
  `faltam_grandes.csv` e `com_doi_sem_scimago.csv`, mantidos à mão até aqui.
- **`data/inventory.json` (rodada 1) aposentado** — os campos que ainda
  importavam (`s2_intents`/`s2_influential` de 80 registros) foram
  incorporados a `master.json` por back-fill antes da remoção; nenhum script
  lê mais o arquivo.
- **Valores hard-coded migram para `config.json`.**
  `audit_80_report_html.py` lia título, veículo e a lista de editoras
  estabelecidas de dicionários no próprio código; agora lê
  `config.json › papers.*.title/venue` e `config.json ›
  editoras_estabelecidas` (16 prefixos de DOI).
- **A lista de editoras passa a ter uma fonte só.** METHOD.md enumerava os
  16 prefixos em prosa, arriscando divergir do que o código de fato usa;
  a seção agora aponta para `config.json › editoras_estabelecidas` em vez
  de repetir a lista.
- **Numeração por fase.** `pipeline/` + `repairs/` (numeração ad hoc, script
  por tarefa pontual) viram `tools/`, um script por fase (`10` colheita,
  `20` texto, `30` integridade, `40` periódicos, `50` pendências, `80`
  saídas), com `tools/auditlib.py` centralizando caminho, I/O de
  `data/*.json`, rede e taxonomia.
- **`text_legacy/` removido.** Mecanismo de uso único de
  `repairs/10_repair_texts.py` (movia órfão para `text_legacy/` como efeito
  colateral de um script de reparo, sem README nem convenção) — substituído
  pelo par explícito e documentado `text/_orfaos/` + `text/README.md`.
- **`aresta_falsa` vira veredito terminal.** Os portões de integridade
  recalculavam status a cada rodada e reescreviam `aresta_falsa` →
  `tem_texto` nos dois PDFs verificados que não citam o artigo, apagando o
  achado. `airline_s008` e `grains_s001` restaurados; os três portões agora
  pulam status terminal em vez de sobrescrevê-lo.

## 2026-09-04 — o estudo, importado do histórico

A auditoria em si — o trabalho que a reorganização acima empacota, não
substitui. Os commits originais ficam no `git log`; aqui vão agrupados por
tema, porque o histórico será reescrito e um ponteiro por hash não
sobreviveria a isso.

- **Inventário.** União de quatro fontes automáticas (OpenAlex, Semantic
  Scholar, OpenCitations, Europe PMC) com as listas completas do Google
  Scholar, deduplicada por DOI e por título normalizado — 176 citações
  mapeadas, mais do que qualquer fonte isolada.
- **Portões de integridade e proveniência.** Os três portões que impedem
  conclusão falsa (texto do artigo certo; página de rosto não é texto
  completo; "só na bibliografia" exige corpo comprovado) e o bloco `prov`
  (codebook, codificador, hash da evidência) em toda entrada de
  `classify.json`.
- **Classificação por acesso Elsevier e Springer.** Rodadas de leitura via
  acesso institucional — Elsevier chega a 49/49 completo (quatro fantasmas
  confirmados), Springer via SSO soma 5 classificadas e 3 fantasmas.
- **Denominador e população do estudo definidos.** O denominador de
  cobertura é "citações com DOI" (147 das 176 — as 29 sem DOI documentam
  alcance mas não entram em taxa); a população do estudo acrescenta editora
  estabelecida + artigo de periódico, e fecha em 87 (49 aviação + 38 grãos).
- **Periódicos e Scimago.** Banco de metadados por periódico citante
  (`data/journals.json`, 93 periódicos) e o quartil oficial do Scimago
  Journal Rank (edição 2025, casado por ISSN) substituindo o proxy por
  `citedness` do OpenAlex como tier.
- **Cobertura de evidência por quartil.** A tabela que cruza quartil ×
  passagem-recuperada × fantasma-verificado × pendência, a correção da
  contagem de pendências (18, não 19) e a preservação, em
  `classify_orfas.json`, do achado de duplicata que a deduplicação por DOI
  apagaria (as duas publicações do mesmo trabalho no *SHS Web of
  Conferences*).
- **Registro de afirmações.** `data/claims/claims.json`: 63 afirmações dos
  dois artigos extraídas dos PDFs publicados, cada uma com citação literal
  verificada contra três extrações independentes; 16 marcadas `relayed`
  (o que o próprio artigo atribui a terceiros, e que um citante pode
  erroneamente atribuir aos autores). Documentada a armadilha do
  `pdftotext` no PDF de aviação, que descarta todo sinal de menos.
