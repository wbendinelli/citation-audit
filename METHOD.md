# Método de auditoria de citações

Avaliar **a qualidade de cada citação recebida**, não a contagem. A pergunta não é
"quantos me citaram", é "quem me usou de verdade, quem me citou de passagem, e quem
me citou errado".

## Taxonomia

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

## Regra de evidência

**Nenhuma classificação sem a passagem literal.** Toda entrada classificada guarda o
trecho exato do texto citante. Citação sem passagem recuperada fica fora de todas as
contagens — não é classificada como "ruim", é classificada como "não lida".

Isso torna as métricas honestas: elas são sempre "entre as citações que deu para ler".

## Fontes

| Camada | Fonte |
|---|---|
| Grafo de citações | OpenAlex (`filter=cites:`) |
| Texto completo | Unpaywall, Europe PMC, arXiv, repositórios institucionais |
| Trechos de citação | Semantic Scholar (`/citations?fields=contexts,intents,isInfluential`) |
| Metadados | OpenAlex, Crossref |

Todas gratuitas e sem autenticação.

## Portões de integridade

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

## Autocitação e citação de coautor

Marcadas explicitamente e excluídas do indicador de reuso metodológico externo.
Uma citação assinada por coautor do artigo citado não mede alcance independente.

## Codebook: os casos de fronteira

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

## Provenance

Cada classificação em `data/classify.json` carrega um bloco `prov` com data, quem
codificou, o hash SHA-256 da evidência, o tipo de evidência (passagem literal ou corpo
completo sem menção), a URL ou arquivo de origem, e a versão do codebook.

## Decisão de escopo: o denominador é "citações com DOI"

O inventário tem 176 registros, mas 29 não têm DOI depositado — são teses,
capítulos de livro, working papers e periódicos não indexados que só o Google
Scholar lista. Eles ficam **no inventário** (documentam alcance, e vários são
substantivos) mas **fora do denominador** das taxas de cobertura, porque não
são necessariamente publicação revisada por pares e porque não há via
sistemática de obtê-los.

Toda taxa de cobertura neste estudo lê-se, portanto, sobre as **147 citações
com DOI**. Reportar sobre as 176 subestimaria a cobertura por incluir material
que nenhum método alcançaria.

## População do estudo: periódico de editora estabelecida

O objeto do estudo é **impacto em periódico relevante**. A população é definida por
três critérios cumulativos:

1. tem DOI depositado;
2. o prefixo do DOI é de editora estabelecida (Elsevier, Springer, Wiley, Taylor &
   Francis, Emerald, MDPI, SAGE, Cambridge, Oxford, De Gruyter, Nature Portfolio,
   PLOS, BMC, Palgrave);
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

## Tier de periódico: quartil Scimago oficial

`data/journals.json` guarda, para cada um dos 93 periódicos citantes, os metadados do
OpenAlex: ISSN-L, editora, país, tipo, acesso aberto, DOAJ, h-index, contagem de obras
e `2yr_mean_citedness` (proxy de fator de impacto).

O tier vigente é o **SJR Best Quartile do Scimago, edição 2025**, casado por ISSN
(`pipeline/15_scimago.py`). Casaram **70 dos 93** periódicos: 39 Q1, 15 Q2, 8 Q3, 5 Q4
e 3 sem quartil atribuído.

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

## Citações em documento de política pública

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

## Ausência do Scimago: separar o que é limitação do que é tipo de documento

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
têm quartil**. Duas exceções merecem nota: `Cleaner Food Systems` e `Journal of the Air
Transport Research Society` são periódicos lançados recentemente demais para constar na
edição 2025 — ausência por idade, não por qualidade.
