# Método de auditoria de citações

Codebook v1 — 2026-09-04
Codebook v2 — 2026-09-04 · Codebook v2.1 — 2026-09-04 (pós-teste cego, §18)

Avaliar **a qualidade de cada citação recebida**, não a contagem. A pergunta não é
"quantos me citaram", é "quem me usou de verdade, quem me citou de passagem, e quem
me citou errado".

As seções abaixo são numeradas `§1`…`§17`, em ordem fixa. **O número de uma seção é
contrato** — README.md e outros documentos apontam para ele — e nunca muda depois de
publicado; renomear o título de uma seção é livre, renumerar não é.

## §1 — Taxonomia

Quatro eixos independentes. A taxonomia foi extraída do código-fonte do
`citation-explorer` do Paperclip (pacote `gxl_paperclip` 0.7.47, módulo
`cli/citation_explorer.py`), e é compatível com a literatura de *citation function
analysis* (CiTO; Teufel et al.; os *intents* do Semantic Scholar).

### 1. ROLE — quanto o artigo importou para quem citou

| Valor | Significado |
|---|---|
| `bibliography_only` | Consta na lista de referências, sem menção no corpo |
| `drive_by` | Citação em bloco, afirmação genérica, sem uso próprio |
| `brief_mention` | Uma afirmação específica é atribuída ao artigo |
| `real_mention` | O artigo é descrito com seu conteúdo real |
| `supporting` | O artigo sustenta parte do argumento ou do desenho do citante |
| `foundational` | O citante constrói sobre o artigo, ou o identifica como referência única |
| `wrongly_interpreted` | O artigo é citado para algo que ele não diz |

### 2. STANCE — postura do citante

`supporting` · `contradictory` · `none`

Regra deliberadamente liberal, como no original: qualquer contraponto conta como
`contradictory`, mesmo sem linguagem hostil e mesmo quando o citante também usa o
artigo como baseline. "Unlike X", "X não considera", "X é limitado a" — todos contam.

### 3. REUSE_TAGS — reuso efetivo

`method_adoption` · `result_validated` · `dataset_reuse` · `benchmarking` · `work_extended`

Só marcado quando o citante **usa** o trabalho, não quando apenas o menciona.
É o sinal mais forte de impacto real.

### 4. CITATION_STATUS

`in_text` · `bibliography_only` · `not_found`

## §2 — Regra de evidência

**Nenhuma classificação sem a passagem literal.** Toda entrada classificada guarda o
trecho exato do texto citante. Citação sem passagem recuperada fica fora de todas as
contagens — não é classificada como "ruim", é classificada como "não lida".

Isso torna as métricas honestas: elas são sempre "entre as citações que deu para ler".

## §3 — Fontes

| Camada | Fonte |
|---|---|
| Grafo de citações | OpenAlex (`filter=cites:`), Semantic Scholar, OpenCitations, Europe PMC |
| Texto completo | Unpaywall, Europe PMC, arXiv, repositórios institucionais |
| Passagem citante (a evidência da regra em §2) | extraída do texto completo baixado (`audit_31_passages.py`), não da API de nenhuma fonte |
| Metadados | OpenAlex, Crossref |

Todas gratuitas e sem autenticação.

Os campos `s2_intents`/`s2_influential` de `master.json` (presentes em 80 dos 176
registros) vêm do Semantic Scholar (`intents`/`isInfluential` da API de citações), mas
por back-fill único a partir do `data/inventory.json` da rodada 1, feito na migração
para o esquema v2 — o `audit_10_harvest.py` atual não pede `contexts`/`intents`/
`isInfluential` à API (só `title,year,venue,externalIds,isOpenAccess,openAccessPdf,
publicationTypes`), então uma colheita nova não preenche esses dois campos para
registro novo. Tratar os dois como cobertura completa seria erro.

## §4 — Portões de integridade

Três verificações automáticas impedem que a auditoria produza conclusões falsas.
Todas foram acrescentadas depois de detectarem erro real nos dados.

**1. O texto tem de ser do artigo certo.** O arquivo baixado precisa conter o próprio
título do registro. Cinco arquivos falharam nesse teste — eram de outro artigo, por
colisão de nome durante o re-arquivamento. Teriam contaminado a classificação.

**2. Página de rosto não é texto completo.** Documento curto sem o sobrenome citado é
abstract, não artigo. Marcado como parcial e fora de toda contagem.

**3. "Só na bibliografia" exige o corpo do artigo.** Páginas de rosto de publisher
(Springer, Wiley) exibem a lista de referências inteira sem o corpo. Encontrar o
sobrenome só na bibliografia desses documentos **não** prova citação-fantasma — prova
apenas que o corpo não foi obtido. O veredito de fantasma só vale com corpo comprovado.
Esse portão derrubou 8 falsos positivos e confirmou 6 fantasmas legítimos.

**`aresta_falsa` é veredito terminal, não estado que os portões recalculam.** Os três
portões acima rodam a cada nova coleta e podem reclassificar `status` livremente — exceto
quando o valor já é um veredito manual definitivo. `aresta_falsa` significa PDF obtido
e verificado, e o artigo citante não cita o trabalho auditado em lugar nenhum (nem
corpo, nem bibliografia) — o oposto de "falta evidência": é evidência negativa
completa. Uma rodada anterior do portão 1 sobrescrevia `aresta_falsa` → `tem_texto` nos
dois casos verificados (`airline_s008`, `grains_s001`), apagando o achado; os portões
agora pulam todo status terminal em vez de recalculá-lo.

## §5 — Autocitação e citação de coautor

Marcadas explicitamente e excluídas do indicador de reuso metodológico externo.
Uma citação assinada por coautor do artigo citado não mede alcance independente.

## §6 — Codebook: os casos de fronteira

As definições acima não resolvem sozinhas os casos difíceis. Estes são os julgamentos
reais feitos nesta auditoria, cada um com o exemplo que o motivou. Um segundo
codificador deve conseguir reproduzir as decisões a partir daqui.

**Contraposição sem hostilidade.** *TR-A 2018* agrupa o artigo entre os estudos que só
tratam de atraso de chegada e escreve "In contrast to these studies, this work
investigates…". Não há crítica; há delimitação de escopo com o citante se colocando
acima. Pela regra liberal isso é `contradictory`.

**Verbo de distanciamento não basta.** *JATM 2022* escreve "Still Bendinelli et al.
claim that there is little evidence…". "Claim" distancia, mas o citante relata o achado
com precisão e não o contesta. Fica `supporting`.

**`wrongly_interpreted` versus `weak`.** *JATM 2019* diz que o artigo investiga estrutura
de custo da companhia — o objeto está errado, é `wrongly_interpreted`. Já *Transport
Policy 2019* lê o resultado sobre LCC como positivo, enquanto *JATM 2022* lê o mesmo
resultado como nulo: aqui a leitura é discutível, não demonstravelmente falsa, então é
`weak` e a divergência entre citantes fica registrada na nota.

**`method_adoption` versus `brief_mention` em bloco.** *TR-E 2020* adota o tratamento de
endogeneidade do artigo e instrumenta HHI por causa dele — `method_adoption`. *Economics
of Transportation 2022* cita o artigo no bloco de oito referências que justifica a
escolha de variáveis de controle, sem adotar nada específico — `brief_mention`. A régua
é: o citante mudaria de desenho se o artigo não existisse?

**`drive_by` versus `brief_mention`.** `drive_by` é afirmação genérica que qualquer
fonte da área sustentaria ("cereais são componentes vitais da alimentação"). 
`brief_mention` atribui ao artigo uma afirmação específica ("o nível da estrutura
pós-colheita é um dos determinantes das perdas").

**`bibliography_only` exige o corpo.** Ver o portão 3 acima. Sem corpo comprovado, o
registro é `evidencia_insuficiente`, nunca fantasma.

**Autocitação e coautor.** Marcadas e excluídas do indicador de reuso externo. Não são
falha: são impacto que não mede alcance independente.

## §7 — Provenance

Cada classificação em `data/classify.json` carrega um bloco `prov` com data, quem
codificou, o hash SHA-256 da evidência, o tipo de evidência (passagem literal ou corpo
completo sem menção), a URL ou arquivo de origem, e a versão do codebook.

## §8 — Decisão de escopo: o denominador é "citações com DOI"

O inventário tem 176 registros, mas 29 não têm DOI depositado — são teses,
capítulos de livro, working papers e periódicos não indexados que só o Google
Scholar lista. Eles ficam **no inventário** (documentam alcance, e vários são
substantivos) mas **fora do denominador** das taxas de cobertura, porque não
são necessariamente publicação revisada por pares e porque não há via
sistemática de obtê-los.

Toda taxa de cobertura neste estudo lê-se, portanto, sobre as **147 citações
com DOI**. Reportar sobre as 176 subestimaria a cobertura por incluir material
que nenhum método alcançaria.

## §9 — População do estudo: periódico de editora estabelecida

O objeto do estudo é **impacto em periódico relevante**. A população é definida por
três critérios cumulativos:

1. tem DOI depositado;
2. o prefixo do DOI é de editora estabelecida — os 16 prefixos e nomes estão em
   `config.json › editoras_estabelecidas` (fonte única; a lista não é repetida em
   prosa aqui para não divergir do que o código de fato usa). `10.1155` (Hindawi)
   conta como Wiley desde a aquisição;
3. é artigo de periódico — capítulo de livro, anais de conferência e repositório de
   preprint (SSRN, Zenodo) ficam fora.

Isso dá **87 citações**: 49 do artigo de aviação e 38 do de grãos.

Os demais registros permanecem no inventário e continuam classificados quando houve
evidência, mas não entram nas taxas do estudo. Duas consequências que precisam ser
declaradas ao reportar: as citações de passagem e as citações-fantasma concentram-se
justamente nos veículos menores, então **as taxas sob esta população são mais
favoráveis do que sob o inventário completo**; e "editora estabelecida" é proxy grosso
para relevância — um critério mais defensável seria indexação em Scopus ou Web of
Science com quartil, se a análise final exigir.

## §10 — Tier de periódico: quartil Scimago oficial

`data/journals.json` guarda, para cada um dos 93 periódicos citantes, os metadados do
OpenAlex: ISSN-L, editora, país, tipo, acesso aberto, DOAJ, h-index, contagem de obras
e `2yr_mean_citedness` (proxy de fator de impacto).

O tier vigente é o **SJR Best Quartile do Scimago, edição 2025**, casado por ISSN
(`tools/audit_41_scimago.py`). Casaram **70 dos 93** periódicos: 39 Q1, 15 Q2, 8 Q3, 5
Q4 e 3 sem quartil atribuído.

Os 23 sem correspondência não são falha de casamento — são repositório de preprint
(SSRN, arXiv, RePEc), série de conferência (SHS Web of Conferences, AIAA) e periódico
regional fora do Scopus. Esses mantêm o proxy anterior, marcado em `tier_base` como
`proxy OpenAlex (sem correspondência no Scimago)` para não se confundir com quartil
oficial.

O import também traz **quartil por área** (um periódico pode ser Q1 em Transportation e
Q2 em Management), SJR, h-index, rank, país e a coluna **Overton**, que conta citações
do periódico em documento de política pública.

Três limitações que precisam ser ditas ao usar:

1. **Não é normalizado por área.** Um corte absoluto favorece campos de citação
   rápida. Comparar aviação com agronomia por este tier é comparar réguas diferentes.
2. **Periódico novo distorce.** *Journal of the Air Transport Research Society* sai
   como T1 com citedness 9,0 e h-index 20 — a janela de 2 anos é instável em
   periódico recém-lançado.
3. **Repositório não é periódico.** SSRN, arXiv e RePEc recebem T4 por terem
   citedness baixa, o que não diz nada sobre qualidade. Eles já ficam fora da
   população do estudo pelo filtro de tipo de documento.

## §11 — Citações em documento de política pública

Nenhuma foi detectada. Os tipos de documento citante, pelo OpenAlex, são: 112 artigo,
11 capítulo de livro, 10 preprint, 6 anais, 4 tese, 2 revisão, 1 livro — e 29 sem DOI.
**Zero do tipo `report`**, que é como relatório institucional aparece.

Isso não prova ausência: grafos de citação acadêmicos cobrem mal documento de política.

O CSV do Scimago traz a coluna **Overton**, e ela dá um sinal indireto: **41 dos 70
periódicos casados têm citações em documento de política** — *Scientific Reports* com
122, *Sustainability* com 53, *Communications Earth & Environment* com 38.

**Este sinal é do periódico, não do artigo.** Diz que o trabalho circula em veículos
que alimentam política pública; **não** diz que alguma citação a ele chegou a um
documento de política. Afirmar o segundo a partir do primeiro seria erro. Para o dado
por artigo é preciso a base Overton, que é paga, ou busca dirigida nos repositórios de
FAO, Banco Mundial, OCDE, Embrapa e CONAB.

## §12 — Ausência do Scimago: separar o que é limitação do que é tipo de documento

Das 147 citações com DOI, 49 não têm quartil Scimago. Elas se dividem em dois grupos
com significados opostos, e tratá-las como um bloco só seria erro.

**32 estão corretamente fora**, porque não são artigo de periódico: 11 capítulos ou
livros, 10 registros de repositório de preprint (SSRN, arXiv, RePEc), 6 anais de
conferência (E3S, SHS, IOP, AIP, AIAA), 4 teses e 1 DOI de projeto do CORDIS
(`10.3030/687772`), que não é sequer publicação. O Scimago indexa periódico; a ausência
aqui é comportamento correto da base.

**17 são periódico de verdade** ausentes do Scopus: `Transportes` (BR, duas citações),
`Revista Verde` (BR), `Plant Archives` (IN), `Asian Journal of Agriculture and Food
Sciences` (IN), `Tanzania Journal of Science`, `Siberian Herald of Agricultural
Science` (RU), `Lomonosov Economics Journal` (RU), `Modeling Control and Information
Technologies` (UA), `Naučne publikacije` (RS), `Studia i Prace` (PL), entre outros.
A ausência é limitação de cobertura geográfica do Scopus, não sinal de qualidade.

Removidos os 32, o denominador de artigos de periódico é **115**, dos quais **98 (85%)
têm quartil**. Precisão sobre o que é esse 98: não é "artigo de periódico" no sentido
estrito — é **todo registro com DOI e quartil Scimago, qualquer tipo de documento**
dentro dos 115. Por tipo: 95 `article`, 2 `review` e 1 `book-chapter` (um capítulo cujo
periódico-fonte casou com o Scimago mesmo com o registro tipado como capítulo). Duas
exceções merecem nota entre os que ficam de fora: `Cleaner Food Systems` e `Journal of
the Air Transport Research Society` são periódicos lançados recentemente demais para
constar na edição 2025 — ausência por idade, não por qualidade.

## §13 — Cobertura de evidência dentro da população com quartil

Dos 98 registros com DOI e quartil Scimago (ver §12 para a definição exata desta
população):

| Quartil | Total | Com trecho literal | Só na bibliografia | Aresta falsa | Falta | % com trecho |
|---|---|---|---|---|---|---|
| Q1 | 69 | 58 | 5 | 0 | 6 | 84% |
| Q2 | 16 | 10 | 0 | 1 | 5 | 63% |
| Q3 | 8 | 5 | 1 | 0 | 2 | 63% |
| Q4 | 5 | 1 | 0 | 0 | 4 | 20% |
| **Total** | **98** | **74** | **6** | **1** | **17** | **76%** |

A conta fecha como 74 trecho + 6 fantasma + 1 aresta falsa + 17 pendentes = 98 (a versão anterior desta tabela dizia 73 + 7: a auditoria de fantasmas, `audit_67`, achou o marcador sobrescrito do `grains_024` e ele migrou de fantasma para trecho). A
aresta falsa (`grains_s001`, *Journal of Horticultural Science and Biotechnology*) não
é pendência: o PDF foi obtido e verificado, e o artigo não cita o trabalho em lugar
nenhum. Contá-la como "falta evidência" seria erro — a evidência existe e é negativa.
Por isso ganha coluna própria em vez de ficar embutida em "Falta", como em uma versão
anterior desta tabela.

Somando trecho literal e fantasma verificado — os dois são evidência, apenas de tipos
diferentes — a cobertura é de **80 em 98, 82%** (74 + 6 = 80). Por artigo: aviação 43 de 50 com trecho (86%), grãos 30 de 48 (62%) — o registro
de Q1 que moveu de trecho para fantasma na tabela acima é de grãos, e o registro de Q2
que moveu de pendente para trecho é de aviação.

**A cobertura é maior justamente em Q1.** Isso não foi desenho: é efeito colateral de o
Elsevier, que concentra os Q1 das duas áreas, ter liberado texto completo pelo acesso
institucional, enquanto Emerald e Wiley não liberaram. O viés resultante é favorável à
análise — a evidência é mais densa onde o impacto importa mais — mas precisa ser
declarado, porque significa que as estatísticas de Q4 se apoiam em 1 observação e não
sustentam comparação entre quartis.

Os 17 que faltam: 12 vêm de editoras estabelecidas que o autor tentou baixar sem
sucesso (Emerald 4, Wiley 3, Hindawi 2, Springer 2, De Gruyter 1), e 5 entraram por terem quartil
sem serem de editora estabelecida (Inderscience 3, a Academia Tcheca de Ciências Agrárias 1, ASABE 1). Bloqueio de acesso, não falha de
método. A versão anterior deste parágrafo dizia 18 (11 + 7): somava a aresta falsa
`grains_s001`, que `data/derived/pendencias.csv` lista de propósito com a instrução
"nada a baixar, só registrar"; a contagem agora sai de `audit_70` (§cobertura,
lista `pendentes`), não de uma lista à mão.

## §14 — Deduplicação pode esconder achado

A união multi-fonte deduplica por DOI e por título normalizado. Isso é correto para
contagem — a mesma obra em duas bases não pode virar duas citações — mas apaga um
sinal quando os dois registros são **publicações distintas do mesmo texto**.

Ocorreu uma vez: `10.1051/shsconf/202521601037` e `10.1051/shsconf/202521601068` são o
mesmo trabalho publicado duas vezes no *SHS Web of Conferences*, com o texto reescrito
por sinônimos entre as versões. A deduplicação fundiu os dois; a classificação do
registro absorvido está em `data/classify_orfas.json`, e o achado de duplicata foi
transferido para a nota do registro vivo.

Regra adotada: registro absorvido pela deduplicação vai para o arquivo de órfãs, com o
motivo, em vez de ser descartado — e qualquer achado que só existia nele é transferido
para o registro sobrevivente antes do arquivamento.

## §15 — Registro de afirmações

`data/claims/claims.json` guarda **63 afirmações** dos dois artigos (30 aviação, 33
grãos), extraídas dos próprios PDFs publicados, cada uma com citação literal
verificada contra três extrações independentes. `validated_by_author` é `false` em
todas as 63 — a validação pelo autor está pendente, e até lá o registro vale como
leitura de segundo codificador, não como afirmação confirmada (ver ROADMAP.md).

**16 delas são `status: relayed`** — o que o próprio artigo atribui a terceiros, não
uma afirmação original dele. Importa para esta auditoria porque é exatamente o tipo de
atribuição que um citante pode errar, creditando aos autores algo que o artigo só
repassa (ex.: a faixa "20–35% dos grãos perdidos" é de Gustavsson et al. (2011), não do
artigo de grãos).

`data/claims/README.md` documenta a armadilha de extração do PDF de aviação: o
`pdftotext` cru descarta todo sinal de menos (glifo `0x03`), lendo `−1.4772***` como
`1.4772***` — os sinais são o ponto do artigo, e um script que rode `pdftotext` direto
sobre esse PDF, sem a correção de glifo já aplicada em `source_text/airline.txt`, lê os
coeficientes ao contrário.

## §16 — Taxonomia v2: eixos ortogonais

**Por quê.** O `role` de sete valores do §1 funcionou, mas misturava três perguntas
diferentes num único rótulo: *o artigo aparece no corpo?*, *quanto ele importou?* e
*o citante disse a verdade sobre ele?* — `wrongly_interpreted`, por exemplo, é o
mesmo nível de menção que `brief_mention` mais um erro de exatidão, só que sem
maneira de separar as duas coisas depois de classificado. A literatura de *citation
function analysis* trata essas perguntas como eixos independentes (Moravcsik &
Murugesan, 1975; Teufel, Siddharthan & Tidhar, 2006; Jurgens et al., 2018; Cohan et
al., 2019 — SciCite) e as mede com estatísticas diferentes porque são constructos
diferentes: profundidade é uma escala com ordem, e a literatura de concordância entre
codificadores recomenda o α ordinal de Krippendorff para ela (Krippendorff, 2011);
postura e exatidão são nominais, e usam κ de Cohen (1960) acompanhado de PABAK (Byrt,
Bishop & Carlin, 1993) e da prevalência por categoria, porque κ é sensível a
prevalência e viés — o "paradoxo do kappa" (Feinstein & Cicchetti, 1990). Um único
`role` misto tornava qualquer uma dessas estatísticas mal-definida. O v2 separa os
eixos para que cada um seja julgado, e medido, sozinho — ver §17.

A migração de v1 para v2 é `audit_60_taxonomy_v2.py` (fase 60); a taxonomia completa,
o crosswalk e as regras de migração vivem também em `data/taxonomy_v2.json`, gerado
pelo mesmo script — as tabelas abaixo são a renderização em prosa desse arquivo.

### Eixo 1 — PRESENCE: onde o artigo aparece no citante

| Valor | Significado |
|---|---|
| `in_text` | O artigo é mencionado no corpo do texto — inclusive dentro de um bloco de citações numéricas como `[5,21,22,23]` ou de um parêntese com várias fontes |
| `reference_list_only` | Consta na lista de referências, sem nenhuma menção no corpo. Exige corpo completo verificado (portão 3, §4) |
| `not_cited` | Não aparece nem no corpo nem na lista de referências — aresta falsa do grafo de citações |

### Eixo 2 — DEPTH: quanto o artigo importou para quem citou (ordinal)

Só se aplica quando `presence = in_text`; caso contrário fica `null`.

| Nível | Valor | Significado |
|---|---|---|
| 1 | `drive_by` | Citação em bloco, afirmação genérica, sem uso próprio |
| 2 | `brief_mention` | Uma afirmação específica é atribuída ao artigo |
| 3 | `real_mention` | O artigo é descrito com seu conteúdo real |
| 4 | `supporting` | O artigo sustenta parte do argumento ou do desenho do citante |
| 5 | `foundational` | O citante constrói sobre o artigo, ou o identifica como referência única |

A profundidade é julgada pelo que o citante FAZ com o artigo, não pela exatidão do que
diz dele. Uma citação que atribui ao artigo uma afirmação específica errada continua
sendo `brief_mention` (nível 2) neste eixo e recebe o erro no eixo de exatidão — no v1
esse caso era o `role` `wrongly_interpreted`, que misturava os dois eixos (ver R3
abaixo).

### Eixo 3 — STANCE: postura do citante

`supporting` · `contradictory` · `none` — inalterado em relação ao §1.

### Eixo 4 — ACCURACY: o citante diz o que o artigo diz?

Só se aplica quando `presence = in_text`; caso contrário fica `null`. Compare o que a
passagem atribui ao artigo com o resumo original e com o registro de afirmações
(§15).

| Valor | Significado |
|---|---|
| `accurate` | O que é atribuído ao artigo corresponde ao que ele diz |
| `imprecise` | Leitura discutível, frouxa ou ampliada, mas não demonstravelmente falsa — um dado de outro país, uma generalização além do escopo, um achado lido numa direção que o artigo não afirma com clareza (no v1: flag `weak`) |
| `misrepresented` | O artigo é citado para algo que ele não diz — objeto, método ou achado errado (no v1: `wrongly_interpreted` / `misattribution`) |

**Sub-código DISTORTION** (Greenberg, 2009, *BMJ* 339:b2680), obrigatório quando
`accuracy != accurate` e `null` quando `accurate`:

| Valor | Significado |
|---|---|
| `dead_end` | O artigo é usado para sustentar uma afirmação sobre a qual ele não tem conteúdo relevante |
| `diversion` | O conteúdo do artigo é citado, mas com significado diferente do original |
| `transmutation` | Uma hipótese, conjectura ou limitação do artigo vira fato estabelecido na citação |
| `relayed_attribution` | O citante atribui ao artigo, como achado próprio, algo que o artigo apenas repassa de terceiros (afirmações marcadas REPASSADO em `data/claims/claims.json`, §15) |

Na migração v1 → v2, `distortion` nasce sempre `null` (rule R0) — é atribuído depois,
no mapeamento de passagens contra `data/claims/claims.json` (`audit_63_claim_map.py`,
ROADMAP.md), não pela migração automática.

### Eixo 5 — REUSE: reuso efetivo (multi-rótulo)

`method_adoption` · `result_validated` · `dataset_reuse` · `benchmarking` ·
`work_extended` — inalterado em relação ao §1, exceto que agora convive com `depth`
em vez de substituí-lo: um `method_adoption` normalmente implica `depth >= supporting`
(o citante mudaria de desenho se o artigo não existisse), mas os dois eixos são
julgados em separado.

### Campos auxiliares (fora das estatísticas primárias)

Três campos não são eixos de função de citação — são metadados de registro ou
decisão editorial:

| Campo | Valores | O que é |
|---|---|---|
| `relation` | `independent` · `coauthor` · `self` | Vínculo de autoria entre citante e citado — ver §5. `coauthor`/`self` ficam fora do indicador de reuso metodológico externo |
| `record_flags` | lista ⊆ `{duplicate_publication}` | Sinal do **registro** (mesma obra publicada duas vezes — ver §14), não da citação em si |
| `highlight` | `none` · `good` · `best` | Realce editorial (citação notável para a prosa do relatório) — não entra em nenhuma estatística de concordância ou cobertura |

### Regras de migração (v1 → v2)

`audit_60_taxonomy_v2.py` aplica estas regras, na ordem R1–R9 (R0 é o caso-padrão,
aplicado depois das que casarem); a coluna "Então" descreve só o que a regra muda —
os demais campos seguem R0:

| Regra | Quando (v1) | Então (v2) |
|---|---|---|
| R1 | role == bibliography_only (flag ghost é absorvida) | presence = reference_list_only; depth = null; accuracy = null |
| R2 | role não é bibliography_only nem wrongly_interpreted | presence = in_text; depth = role |
| R3 | role == wrongly_interpreted | presence = in_text; accuracy = misrepresented; depth = brief_mention com prov.depth_basis = migration_rule_R3 |
| R4 | flag == weak | accuracy = imprecise |
| R5 | flag == misattribution | accuracy = misrepresented (conjunto R5 tem de ser igual ao conjunto R3) |
| R6 | flag in {coautor, autocitacao} | relation = coauthor \| self |
| R7 | flag == duplicate | record_flags = [duplicate_publication] |
| R8 | flag in {good, best} | highlight = flag |
| R9 | flag == critical | descartada — 100% redundante com stance == contradictory (verificado na migração) |
| R0 | padrão | accuracy = accurate para in_text não tocado por R3/R4/R5; relation = independent; record_flags = []; highlight = none; distortion = null; claims = [] |

### Garantia de round-trip (sem perda)

A migração só é aceita se for reversível. Para cada entrada, a projeção inversa
`auditlib.role_flag_v1()` reconstrói o par `(role, flag)` do v1 a partir dos eixos v2,
com a mesma prioridade de flag observada nos dados originais quando mais de um eixo
poderia gerar uma flag: `ghost` > `misattribution` > `weak` > `duplicate` >
`coautor`/`autocitacao` > `best` > `good` > `critical` > nenhuma. O script confere essa
reconstrução para todas as entradas — vivas e órfãs — e **aborta antes de gravar** se
qualquer uma divergir. Na migração de 2026-09-04: round-trip OK em 105/105 entradas
(104 vivas de `data/classify.json` + 1 órfã de `data/classify_orfas.json`); duas
verificações de redundância adicionais também bateram 100%: `flag = ghost` ⟺
`role = bibliography_only` (regra R1), e `flag = critical` ⟺ `stance = contradictory`
(regra R9 — por isso `critical` não vira campo v2 próprio, é só a projeção de
`stance` de volta ao v1).

### Crosswalk contra os esquemas publicados

Cada valor de eixo, contra os esquemas de função de citação mais citados na
literatura. "—" é ausência de equivalente (o esquema não distingue esse caso, ou o
eixo é específico desta auditoria — presença, exatidão e vínculo de autoria não
aparecem nos esquemas de função clássicos, que assumem que toda citação está no
corpo e é fiel ao que cita).

| Eixo | Valor | Moravcsik & Murugesan 1975 | Teufel 2006 | Jurgens et al. 2018 | SciCite (Cohan et al. 2019) | Valenzuela et al. 2015 | CiTO | Nota |
|---|---|---|---|---|---|---|---|---|
| `presence` | `in_text` | — | — | — | — | — | — | fora dos esquemas de função; base de comparação: Boyack et al. 2018 (menções no corpo) |
| `presence` | `reference_list_only` | — | — | — | — | — | — | Boyack et al. 2018: referência não mencionada no corpo (1,4% no corpus Elsevier) |
| `presence` | `not_cited` | — | — | — | — | — | — | aresta falsa do grafo de citações; sem equivalente |
| `depth` | `drive_by` | `perfunctory` | `Neut` | `Background` | `background` | `incidental` | `citesForInformation` |  |
| `depth` | `brief_mention` | `perfunctory` | `Neut` · `PMot` | `Background` | `background` | `incidental` | `citesAsAuthority` |  |
| `depth` | `real_mention` | `organic` | `PMot` · `PSim` | `Background` · `Motivation` | `background` | `incidental` | `describes` |  |
| `depth` | `supporting` | `organic` | `PBas` · `PUse` · `PSup` | `Uses` · `Motivation` | `method` · `background` | `important` | `usesMethodIn` · `citesAsEvidence` | SciCite: method quando há reuso metodológico, background quando só sustenta argumento |
| `depth` | `foundational` | `organic` · `evolutionary` | `PBas` · `PModi` | `Extends` · `Uses` | `method` · `result` | `important` | `extends` |  |
| `stance` | `supporting` | `confirmative` | `PSup` | — | `result` | — | `supports` |  |
| `stance` | `contradictory` | `negational` | `CoCo-` · `Weak` | `CompareOrContrast` | `result` | — | `disagreesWith` |  |
| `stance` | `none` | — | `Neut` | — | — | — | — | sem postura declarada; equivale ao Neut de Teufel quando não há PMot/PSup |
| `accuracy` | `accurate` | — | — | — | — | — | — | eixo de veridicidade — fora dos esquemas de função (Jergas & Baethge 2015) |
| `accuracy` | `imprecise` | — | — | — | — | — | — | erro menor de citação (Jergas & Baethge 2015, categoria minor) |
| `accuracy` | `misrepresented` | — | — | — | — | — | — | erro maior de citação; sub-códigos de Greenberg 2009 em `distortion` |
| `distortion` | `dead_end` | — | — | — | — | — | — | Greenberg 2009: dead-end citation — a fonte não tem conteúdo relevante para a afirmação |
| `distortion` | `diversion` | — | — | — | — | — | — | Greenberg 2009: citation diversion — conteúdo citado com significado diferente |
| `distortion` | `transmutation` | — | — | — | — | — | — | Greenberg 2009: citation transmutation — hipótese vira fato pela citação |
| `distortion` | `relayed_attribution` | — | — | — | — | — | — | extensão local: atribui ao artigo, como achado próprio, o que ele repassa de terceiros |
| `reuse` | `method_adoption` | `organic` | `PUse` | `Uses` | `method` | `important` | `usesMethodIn` |  |
| `reuse` | `result_validated` | `organic` · `confirmative` | `PSup` · `CoCoR0` | `CompareOrContrast` | `result` | `important` | `confirms` |  |
| `reuse` | `dataset_reuse` | `organic` | `PUse` | `Uses` | `method` | `important` | `usesDataFrom` |  |
| `reuse` | `benchmarking` | `organic` | `CoCoR0` | `CompareOrContrast` | `result` | `important` | `citesAsRelated` |  |
| `reuse` | `work_extended` | `organic` · `evolutionary` | `PBas` · `PModi` | `Extends` | `method` | `important` | `extends` |  |
| `relation` | `coauthor` | — | — | — | — | — | — | citação de coautor — literatura de autocitação, fora dos esquemas de função |
| `relation` | `self` | — | — | — | — | — | — | autocitação |

Fontes: Moravcsik, M. J. & Murugesan, P. (1975), "Some Results on the Function and
Quality of Citations", *Social Studies of Science* 5(1); Teufel, S., Siddharthan, A. &
Tidhar, D. (2006), "Automatic Classification of Citation Function", *EMNLP*; Jurgens,
D., Kumar, S., Hoover, R., McFarland, D. & Jurafsky, D. (2018), "Measuring the
Evolution of a Scientific Field through Citation Frames", *TACL* 6; Cohan, A., Ammar,
W., van Zuylen, M. & Cady, F. (2019), "Structural Scaffolds for Citation Intent
Classification in Scientific Publications" (SciCite), *NAACL*; Valenzuela, M., Ha, V.
& Etzioni, O. (2015), "Identifying Meaningful Citations", *AAAI Workshop on Scholarly
Big Data*; CiTO — Peroni, S. & Shotton, D. (2012), "FaBiO and CiTO: ontologies for
describing bibliographic resources and citations", *Journal of Web Semantics* 17;
Greenberg, S. A. (2009), "How citation distortions create unfounded authority:
analysis of a citation network", *BMJ* 339:b2680; Jergas, H. & Baethge, C. (2015),
"Quotation accuracy in medical journal articles — a systematic review and
meta-analysis", *PeerJ* 3:e1364; Boyack, K. W. et al. (2018), "Characterizing in-text
citations in scientific articles: A large-scale analysis", *Journal of Informetrics*
12(1).

## §17 — Confiabilidade entre codificadores (protocolo)

O codebook v2 (§16) só serve se codificadores independentes chegarem perto do mesmo
veredito a partir da mesma passagem. Este protocolo descreve o desenho do teste cego;
a seção de resultados abaixo é preenchida por `audit_62_irr_stats.py` depois que a
coleta terminar — nada aqui é resultado, é o desenho do experimento.

### Desenho do pacote cego

`audit_61_irr_pack.py` (fase 60) monta o pacote a partir do `data/classify.json` já
migrado para v2:

- **Cobertura total.** As 104 entradas vivas — não uma amostra — mais 10 delas
  duplicadas sob um segundo `item_id`, como sonda de consistência intra-codificador
  (mesmo item, dois ids diferentes; o codificador não sabe que é repetido).
  114 itens no total.
- **4 lotes**, embaralhados com semente fixa (`20260904`); a duplicata de um item
  cai sempre num lote diferente do original.
- **Identidade apagada.** `item_id` é opaco (`IRR-xxxx`, 4 hex de
  `sha256(semente+doi[+sufixo])`); cada item carrega só `paper` (`airline`/`grains`),
  `citing_title`, as `passages` (com o DOI e o veículo do próprio citante apagados de
  dentro do texto) e o estilo de citação inferido (`numeric`/`author_year`). DOI,
  veículo, ano, nota, e qualquer rótulo v1 ou v2 (`role`, `flag`, `presence` … até
  `highlight`) ficam de fora — a lista completa de campos proibidos é conferida por
  `audit_61_irr_pack.py --audit`, que sai com código 1 se achar padrão de DOI, o
  veículo do próprio citante, ano colado a "et al." no título, ou palavra de rótulo
  (`ghost`, `fantasma`, `misattribution`, `foundational`, `drive_by`) fora das
  passagens.
- **`relation`, `record_flags` e `highlight` não entram no teste cego** — exigem
  metadados de autoria ou são editoriais (§16), não julgamento sobre a passagem.

### Codificadores

- **Codificador 1** é a classificação original já em `data/classify.json`
  (`prov.coded_by`), projetada para o formato de rótulo do pacote — não um novo
  julgamento.
- **Codificador 2** (Claude Opus) e **codificador 3** (Claude Sonnet) codificam cada
  um, cada um em um contexto novo que lê só `data/irr/instructions.md` e o lote — sem
  acesso a este METHOD.md além do que `instructions.md` reproduz, sem a classificação
  original, sem o PDF nem o texto completo do citante, e sem os outros lotes. A
  cegueira é auditada a partir das transcrições dos codificadores (confirma que
  nenhum leu além do que o pacote entrega) e do próprio pacote
  (`audit_61_irr_pack.py --audit`).

### Estatísticas por eixo

`audit_62_irr_stats.py` (fase 60, `numpy`) calcula, por par de codificadores e depois
para os três juntos:

| Eixo | Estatística primária | Leitura secundária |
|---|---|---|
| `presence` | concordância bruta | — (determinado pela construção do pacote nos itens sem passagem, não é julgamento independente — ver `data/irr/instructions.md`) |
| `depth` | α ordinal de Krippendorff | κ quadrático de Cohen; concordância exata; concordância "±1 nível" |
| `depth_substantive` (`supporting`/`foundational` vs. resto — visão binária) | κ de Cohen | PABAK; AC1 de Gwet; concordância bruta |
| `stance` | κ de Cohen | PABAK; AC1 de Gwet; concordância bruta |
| `accuracy` | κ de Cohen | PABAK; AC1 de Gwet; concordância bruta |
| `accuracy_misrepresented` (visão binária) | κ de Cohen | PABAK; AC1 de Gwet; concordância bruta |
| `reuse` (multi-rótulo) | Jaccard médio | κ por tag (`method_adoption`, …) |

IC95% por bootstrap percentílico sobre os itens (B = 2000, semente fixa). Com os três
codificadores presentes, α de Krippendorff multi-codificador é calculado também para
`presence`/`depth`/`stance`/`accuracy` juntos, não só par a par. A concordância
intra-codificador usa os 10 pares duplicados: proporção idêntica em todos os eixos, e
concordância eixo a eixo.

### Exclusão dos exemplares do codebook

Os 7 casos de fronteira nomeados no §6 (e marcados `codebook_exemplar: true` em
`data/classify.json` pela migração) são o material de treino do próprio codebook —
um codificador que já leu o §6 tem vantagem neles que não tem no resto do pacote.
Por isso ficam de fora das estatísticas **primárias** e entram só num bloco
`sensitivity_with_exemplars` à parte, para checar se incluí-los muda o quadro.

### Inferência com poder de predição (PPI)

`audit_62_irr_stats.py` também implementa PPI (Angelopoulos, Bates, Fannjiang, Jordan
& Zrnic, 2023, "Prediction-Powered Inference") para estimar taxas do estudo inteiro
(por exemplo, a proporção de citações `foundational`/`supporting`, ou a proporção
`misrepresented`) combinando um rótulo barato disponível em **todos** os itens
(`f(Ŷ)` — `--c1`, a classificação já existente) com um rótulo independente só num
subconjunto (`--human`), produzindo um intervalo de confiança mais eficiente que
confiar só no subconjunto pequeno e mais válido que confiar ingenuamente no rótulo
barato sobre tudo. O λ de *power tuning* do PPI++ (Angelopoulos, Duchi & Zrnic, 2023)
ajusta o peso do rótulo barato conforme a correlação observada com o independente,
recortado a `[0, 1]`. É recurso geral do script, para quando a relabelagem
independente cobrir menos que o pacote inteiro — nesta rodada, `c2`/`c3` recodificam
os 114 itens completos, então a leitura principal são as estatísticas par a par
acima; o PPI fica disponível para rodadas futuras com cobertura parcial.

### Resultados

*(preenchido por `audit_62_irr_stats.py` quando a coleta dos três codificadores
terminar — ver ROADMAP.md.)*
## §18 — Codebook v2.1: o que o teste cego ensinou

O teste cego (três codificadores; §17) mostrou onde o codebook v2 era reprodutível e onde
não era. Presença (κ ≈ 0,96–1,00), postura (κ 0,71–0,75 entre pares) e profundidade
(α ordinal 0,57–0,77; concordância dentro de um degrau 0,87–0,99) se sustentam. **A acurácia
não se sustentava**: κ 0,14–0,15 entre o codificador original e cada cego, contra 0,60
entre os dois cegos. A diferença não é de quem codifica — é de **com que instrumento**:
o codificador original não tinha o registro de afirmações (§15). Com o registro, dois
modelos diferentes convergem. As regras abaixo tornam explícito o que o registro fez
implicitamente, e valem para toda codificação daqui em diante.

**A1 — Acurácia é avaliada em toda menção em-texto, inclusive citação em bloco.** Um bloco
`[21,22,23,24]` que cola o artigo a uma afirmação que ele não contém é `imprecise` se o tema
é adjacente ao do artigo, e `misrepresented` + `dead_end` se o artigo não tem conteúdo relevante
(Greenberg 2009, *dead-end citation*). Profundidade `drive_by` **não** dispensa a avaliação
de acurácia — os dois eixos são ortogonais.

**A2 — Repasse atribuído como achado próprio é `misrepresented` + `relayed_attribution`.**
O registro de afirmações marca com `status=relayed` o que o artigo atribui a terceiros
(Gustavsson 2011 para "20–35% dos grãos" e "um terço da produção global"; Gustavsson 2013
para a fórmula de %PHL; Molnar 2013 para "dissuasão de entrada em hubs"; FAA OIG para
"sem concorrência, mais atraso"). "Bendinelli et al. reportam que…" seguido de um desses
números é atribuição incorreta, ainda que o número esteja no artigo. Exemplos adjudicados:
*Food Chemistry* 2024 ("25–30% da oferta"), *INMATEH* 2020, *Journal of Aerospace Technology
and Management* 2018.

**A3 — Extensão de escopo é `imprecise` + `diversion`; `misrepresented` exige objeto ou direção errados.**
Generalizar de grãos para frutas e hortaliças, de painel macro por país para comportamento
do produtor, ou do Brasil para Gana ou China, é `diversion`. Só é `misrepresented` quando o
citante atribui ao artigo um objeto que ele não estuda (estrutura de custo, revisão de
precificação, registros de acidente) ou inverte a direção de um achado (*IJIO* 2021: coloca
o artigo entre os que acham concentração de rota **melhorando** a pontualidade; o achado é o
oposto, AIR-F02).

**A4 — Conjectura citada como fato é `transmutation`.** O artigo conjectura, em §4, que LCC
é mais atraente ao passageiro de lazer em horários de vale (AIR-I02). Citar isso como
"Bendinelli et al. mostram que LCCs miram mercados de lazer" converte hipótese em achado
(Greenberg 2009, *citation transmutation*). Dois citantes fazem isso ao justificar a variável
`MarketType`; a citação continua `supporting` em profundidade (sustenta o desenho do citante)
e `imprecise`/`transmutation` em acurácia — mais um caso de ortogonalidade dos eixos.

**D1 — `foundational` é propriedade do documento inteiro, e janela de passagem a subdetecta.**
Nos 26 itens em que o pacote cego mostrou a janela automática de ±700 caracteres em vez do
trecho curado, os cegos não podiam ver que um citante menciona o artigo doze vezes, ou o
identifica como referência única em outra seção. A regra pré-registrada (maioria de três)
foi mantida; o relatório apresenta como sensibilidade a leitura do codificador com texto
completo nesses itens, e declara a direção do viés: a janela rebaixa `foundational` para
`real_mention`, nunca o contrário.

**R1 — A régua de reuso é estrita: "o citante mudaria de desenho se o artigo não existisse?".**
Os cegos aplicaram a régua com mais rigor que o codificador original: `work_extended` e
`result_validated` foram descartados por unanimidade dos cegos; `method_adoption` sobreviveu
onde o citante replica instrumento, tratamento de endogeneidade ou construção de variável
citando o artigo nominalmente. Declarar "estendemos a literatura de X" citando o artigo num
bloco não é reuso.

**P1 — Presença: evidência de texto completo prevalece sobre janela.** Quando a janela
automática mostrou trecho irrelevante (conclusão, bibliografia) e o codificador com texto
completo localizou a menção, a presença é `in_text`. Um caso (IRR-ed51), decidido pelo
colegiado.

### Resultado numérico do teste

Pré-adjudicação, entre pares independentes: c2×c3 profundidade α 0,77, postura κ 0,75,
acurácia κ 0,60, presença κ 1,00. Pós-adjudicação, contra o rótulo final (inflado por
construção para c2 e c3, que formam a maioria): c1 acurácia κ 0,24, c2 0,74, c3 0,85.
Adjudicação: 20 decisões do colegiado em 19 itens (acurácia 8, profundidade 5, distorção 6,
presença 1; `IRR-81e6` recebeu decisão em três eixos, por isso 20 decisões em 19 itens — a versão anterior deste parágrafo dizia 19/19, distorção 5, 91 em-texto, 18% e imprecisão 18, corrigidos por `audit_63`/`audit_70`); todo o resto por unanimidade, maioria ou derivação. Efeito nos totais: má
atribuição de 4 para 16 em 92 em-texto (4% → 17%), imprecisão de 7 para 19, `foundational`
de 7 para 4, `supporting` de 11 para 5, `method_adoption` de 9 para 5.
