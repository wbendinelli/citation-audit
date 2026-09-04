// main.typ: a prosa do relatório de impacto.
//
// Regra dura do repositório: todo número citado aqui é impresso por
// tools/audit_70_numbers.py. Um valor em prosa traz o ponteiro
// "audit_NN §chave" na nota de rodapé da mesma linha; um valor em tabela
// é lido de D (numeros.typ), e aí não há dígito literal no arquivo.
// O teste de aceitação:
//
//   python3 tools/check_numbers.py --prose reports/01-impacto/main.typ \
//       --exempt reports/01-impacto/check_numbers_exempt.txt
//
// tem de terminar em MISS/SEM-PONTEIRO zero, com o arquivo de isenções
// vazio. Compilação, da raiz do repositório:
//
//   typst compile --root . --font-path tools/fonts \
//       reports/01-impacto/main.typ reports/01-impacto/relatorio.pdf

#import "@preview/sapians:0.3.2": *
#import "numeros.typ": *
#import "figuras.typ": *

// `raw` sem família no pacote sapians cai na DejaVu Sans Mono embutida do Typst.
// A regra tem de vir ANTES do `#show: sapians-report` e no nível do documento:
// dentro de estilo-numeros ela alcança corpo e legendas, mas não as entradas de
// nota de rodapé (testado em Typst 0.15).
#show raw: set text(font: "JetBrains Mono")

#show: sapians-report.with(
  title: "Quem citou, e como",
  subtitle: "Inventário da qualidade das citações recebidas por dois artigos",
  author: "William Bendinelli",
  date: "04/09/2026",
  version: "1.0",
  lang: "pt",
  kicker: "SAPIANS · RELATÓRIO TÉCNICO",
  org: "SAPIANS · Pesquisa e Desenvolvimento",
  author-title: "Autor",
  date-title: "Data",
  version-title: "Versão",
)

#show: estilo-numeros

// Corpo com respiro e parágrafo à moda de periódico, como em
// reports/01-metodos-locais/main.typ (interpretable-ml-lectures).
#set text(size: 9pt)
#set par(leading: 0.62em, spacing: 0.62em, first-line-indent: (amount: 1.1em, all: false))

// Auxiliares de formatação: ficam em uma linha só porque check_numbers.py
// descarta a linha inteira de um #let, não o bloco que ela abre.
#let pct(v) = if v == none { [—] } else { text({ let r = calc.round(v * 100.0, digits: 1); let i = calc.floor(r); str(i) + "," + str(calc.round((r - i) * 10.0)) + "%" }) }
#let num(v) = if v == none { [—] } else { text(str(v)) }
#let txt(v) = if v == none { [—] } else { text(v) }
#let cel(v) = if v == none { [—] } else { text(str(v).replace("_", " ")) }
#let lit(v) = if v == none { [—] } else { text(v.replace(regex("(\\d)\\.(\\d)"), m => m.captures.at(0) + "," + m.captures.at(1))) }
#let _regua-grossa = line(length: 100%, stroke: 0.9pt + sapians-text-dark)
#let _cols-funil = (8%, 1fr, 13%, 13%)
#let _cols-periodicos = (1fr, 13%, 12%, 12%, 13%)
#let _cols-anomalias = (23%, 12%, 1fr)
#let _cols-taxa = (20%, 10%, 12%, 17%, 1fr)
#let _cols-inventario = (13%, 1fr, 8%, 14%, 13%, 12%, 12%)
#let _rot-taxa = ("ghost_D_read": "fantasma, todas as lidas", "ghost_D_body": "fantasma, corpo no disco", "ghost_D_pop": "fantasma, população", "misrepresented_major": "má atribuição (erro maior)", "misrepresented_plus_imprecise_total": "má atribuição + imprecisão", "contradictory": "postura contrária", "perfunctory": "citação perfunctória", "important": "citação importante", "background_like": "citação de pano de fundo", "method_reuse": "reuso metodológico", "self_or_coauthor": "autocitação ou coautor", "duplicate_publication": "publicação duplicada")
#let _rotulo(k) = text(_rot-taxa.at(k, default: k.replace("_", " ")))
// Legenda de tabela acima do corpo, como manda a convenção de periódico; a
// figura mantém a legenda embaixo.
#show figure.where(kind: table): set figure.caption(position: top)

#resumo[
  Este relatório mede a *qualidade* das citações recebidas por dois artigos,
  não a contagem delas. O inventário reúne #D.inventario.total citações aos
  dois trabalhos, das quais #D.inventario.com_doi.total têm DOI depositado e
  #D.meta.n_classificados foram lidas com a passagem literal do texto citante
  em mãos. A população do estudo, definida por DOI mais editora estabelecida
  mais artigo de periódico, tem #D.populacao.total registros.
  Quatro achados organizam o texto. O primeiro é de método: a escala única de
  sete papéis misturava três perguntas independentes, e um teste cego com dois
  codificadores adicionais mostrou que, sem o registro de afirmações dos
  artigos, o codificador original não enxergava má atribuição. O segundo é que
  a citação típica é rasa: em #D.eixos.pooled.presence.in_text.n menções no
  corpo do texto, #D.eixos.pooled.perfunctorio.n são citação em bloco ou
  atribuição de uma afirmação específica sem uso próprio. O terceiro é que
  #D.eixos.pooled.accuracy.misrepresented.n citações atribuem aos artigos algo
  que eles não dizem, e boa parte delas repassa como achado dos autores uma
  estimativa que os artigos apenas citam de terceiros. O quarto é que a
  evidência lida não cobre os quartis por igual: ela é densa em Q1 e rala em
  Q4, por bloqueio de acesso de editora, e esse viés precisa ser declarado
  antes de qualquer comparação entre quartis. No antes e depois, o índice de
  disrupção não decide nada sozinho, porque duas variantes do mesmo índice
  discordam de sinal sobre o mesmo grafo, e o sinal que se sustenta é o de
  co-citação: as duas vertentes que o artigo de aviação declara conciliar
  passaram a ser citadas juntas com mais frequência depois dele, e quem faz
  essa ponte cita o artigo dez vezes mais que quem fica de um lado só. Todo
  número em prosa é impresso
  por um script versionado, e a nota de rodapé que o acompanha diz qual seção
  de `numeros.txt` o imprime.
]

= 1. Como cada citação foi lida

O achado desta seção é de instrumento: a régua com que se lê uma citação
determina o que se enxerga nela. A auditoria começou com uma escala única de
sete papéis, herdada do `citation-explorer` do Paperclip, e terminou com três
eixos independentes mais um eixo de exatidão. A troca não foi cosmética. Sob a
escala única, uma citação que atribui ao artigo uma afirmação específica errada
recebia o rótulo `wrongly_interpreted`, que apagava a informação de que ela era,
em profundidade, uma menção breve como qualquer outra. Depois de classificada,
não havia como separar as duas coisas.

A taxonomia v2 separa as perguntas. @fig-taxonomia mostra as três, com a
exatidão à parte, fora da escada de profundidade. *Presença* pergunta onde o
artigo aparece no citante: no corpo, só na lista de referências, ou em lugar
nenhum. *Profundidade* pergunta quanto o artigo importou, numa escala ordinal
de cinco níveis. *Postura* pergunta de que lado o citante se pôs. *Reuso*
pergunta o que ele efetivamente tomou emprestado, e aceita mais de um valor por
citação. *Exatidão* é o eixo à parte: o citante diz o que o artigo diz? Cada
eixo casa com um esquema publicado de função de citação, e o crosswalk completo
está em METHOD.md §16, contra @moravcsik1975, @teufel2006, @jurgens2018,
@cohan2019, @valenzuela2015 e o CiTO de @shotton2010. Quando a exatidão falha,
um sub-código diz de que tipo é a distorção, na tipologia de @greenberg2009.

#figure(
  fig-taxonomia(),
  caption: [Três eixos ortogonais mais um eixo de exatidão: uma citação recebe um valor em cada um, e um eixo não implica o outro. A escala única de sete papéis do codebook v1 misturava profundidade e exatidão num rótulo só.],
) <fig-taxonomia>

== O teste cego

O codebook só serve se codificadores independentes chegarem perto do mesmo
veredito a partir da mesma passagem. O protocolo de METHOD.md §17 monta um
pacote cego a partir das entradas já classificadas: cada item carrega apenas o
artigo auditado, o título do citante e as passagens, com DOI, veículo, ano,
nota e qualquer rótulo apagados. O pacote sai embaralhado em quatro lotes, com
semente fixa, e uma fração dos itens aparece duplicada sob um segundo
identificador opaco, como sonda de consistência interna do próprio codificador.
Três codificadores entram: `c1` é a classificação original, projetada para o
formato do pacote; `c2` é Claude Opus e `c3` é Claude Sonnet, cada um em
contexto novo, lendo só `data/irr/instructions.md` e o seu lote.

O resultado que reorganiza o estudo está no eixo de exatidão. Presença, postura
e profundidade se sustentaram entre os pares independentes: entre `c2` e `c3` a
presença bate κ 1,00, a postura κ 0,75, com IC95% de 0,588 a
0,882.#footnote[audit_70 §irr: `irr / pre / eixos / presence` e `stance`, par `c2_vs_c3`, ponto e IC95% por bootstrap percentílico.]
A profundidade, medida pelo α ordinal de Krippendorff @krippendorff2011, chega
a 0,77, com IC95% de 0,629 a 0,865.#footnote[audit_70 §irr: `irr / pre / eixos / depth`, par `c2_vs_c3`, `alpha_ordinal`.]
A exatidão não se sustentou. Entre `c2` e `c3` o κ de Cohen @cohen1960 é 0,60,
com IC95% de 0,447 a 0,736; entre o codificador original e cada cego ele cai
para 0,14 e 0,15.#footnote[audit_70 §irr: `irr / pre / eixos / accuracy`, pares `c2_vs_c3`, `c1_vs_c2` e `c1_vs_c3`, `kappa`.]
Pela régua de @landis1977 a mesma tarefa passa de concordância moderada para
concordância leve, dependendo apenas de quem é o par.

A diferença não é de quem codifica, é de com que instrumento. Os dois cegos
tinham em mãos o registro de afirmações dos artigos, o codificador original
não. Sem o registro, uma citação que credita aos autores uma estimativa que o
artigo apenas repassa de outra fonte parece correta, porque o número está mesmo
no artigo. Com o registro, os dois modelos convergem. O codebook v2.1, em
METHOD.md §18, torna explícita cada regra que o registro fazia implicitamente:
acurácia se avalia em toda menção no corpo, inclusive citação em bloco; repasse
atribuído como achado próprio é má atribuição com sub-código
`relayed_attribution`; extensão de escopo é imprecisão com sub-código
`diversion`; e conjectura citada como fato é `transmutation`.

== Adjudicação e o preço da correção

A regra de decisão foi pré-registrada: maioria de três por eixo, distorção
derivada da exatidão, união dos identificadores de afirmação. Onde a maioria
não fechava, um colegiado leu o caso com a régua do codebook na mão e escreveu
a justificativa em `data/irr/panel.json`. O colegiado decidiu oito casos de
exatidão, seis de distorção, cinco de profundidade e um de
presença.#footnote[audit_70 §irr: `irr / adjudication / stats`, sufixo `:colegiado` em cada eixo.]

Depois da adjudicação, o rótulo final é comparado com cada codificador. O
resultado é inflado por construção para `c2` e `c3`, que formam a maioria, mas
a ordem entre os três é informativa: em exatidão, `c1` fica em κ 0,24, com
IC95% de 0,094 a 0,388, contra 0,74 para `c2` e 0,85 para
`c3`.#footnote[audit_70 §irr: `irr / post / c1`, `c2` e `c3`, eixo `accuracy`, `kappa` e IC95%.]
@fig-irr põe os três eixos lado a lado, antes e depois. A leitura honesta é que
o codificador original sub-detectava má atribuição de forma sistemática, e não
por ruído: a matriz de confusão pré-adjudicação não tem nenhuma célula em que
ele marque erro onde os cegos veem acerto.

#figure(
  image("/reports/01-impacto/figuras/fig11_irr.png", width: 92%),
  caption: [A exatidão é o único eixo que não se sustenta entre o codificador original e os cegos: κ 0,14 e 0,15 contra 0,60 entre os dois cegos, enquanto presença, postura e profundidade ficam acima de 0,74 em todos os pares.#footnote[audit_70 §irr: `irr / pre / eixos`, pares `c1_vs_c2`, `c1_vs_c3` e `c2_vs_c3`.]],
) <fig-irr>

= 2. A população: do Scholar à evidência lida

O achado desta seção é que o funil perde mais da metade do caminho entre a
contagem do Google Scholar e a citação lida, e perde por motivos declarados, um
por etapa. O Scholar lista 95 citações ao artigo de aviação e 76 ao de grãos; a
união de quatro APIs, deduplicada por DOI e por título normalizado, deixa 93 e
83.#footnote[audit_70 §funil: `funil / airline / steps / 0` e `1`, `funil / grains / steps / 0` e `1`.]
O inventário completo soma #D.inventario.total registros, dos quais
#D.inventario.com_doi.total têm DOI e #D.inventario.sem_doi.total não têm. Os
sem DOI ficam no inventário, porque documentam alcance, e fora do denominador
de toda taxa de cobertura, porque não são necessariamente publicação revisada
por pares e não há via sistemática de obtê-los.

#tabela(
  [O funil por artigo, com a perda de cada etapa e o motivo dela. A queda maior é sempre a mesma: o prefixo do DOI precisa ser de editora estabelecida.],
  "tab-funil",
  _cols-funil,
  [*Etapa*], [*Critério*], [*Aviação*], [*Grãos*],
  ..range(D.funil.airline.steps.len()).map(i => (
    [#(i + 1)],
    text(size: 6.9pt)[#D.funil.airline.steps.at(i).rotulo],
    [#num(D.funil.airline.steps.at(i).valor)],
    [#num(D.funil.grains.steps.at(i).valor)],
  )).flatten(),
  fonte: [`reports/01-impacto/dados.json`, bloco `funil`, gerado por `tools/audit_70_numbers.py`.],
)

== A decisão de população

O objeto do estudo é impacto em periódico relevante, e a população é definida
por três critérios cumulativos: DOI depositado, prefixo de editora estabelecida
na lista de `config.json`, e artigo de periódico. Capítulo de livro, anais de
conferência e repositório de preprint ficam fora. Isso dá #D.populacao.total
citações, #D.populacao.airline do artigo de aviação e #D.populacao.grains do de
grãos. Dessas, #D.populacao.classificados_dentro_da_populacao.total têm
classificação com evidência.

Duas consequências precisam ser ditas junto com o número. A primeira é que
citação de passagem e citação-fantasma se concentram justamente nos veículos
menores, então as taxas medidas sob esta população são mais favoráveis do que
seriam sob o inventário inteiro. A segunda é que editora estabelecida é proxy
grosso para relevância. Um critério mais defensável seria indexação em Scopus
com quartil, e a análise final deveria migrar para ele.

#figure(
  image("/reports/01-impacto/figuras/fig01_funil.png", width: 88%),
  caption: [Do que o Scholar lista ao que foi lido com passagem literal: o artigo de aviação retém 45 dos 95 registros iniciais e o de grãos 29 dos 76.#footnote[audit_70 §funil: `funil / airline / steps` e `funil / grains / steps`, primeiro e último passo. À direita, quem saiu no corte de editora, por editora, e o quartil Scimago de quem ficou com evidência; a linha tracejada marca a população do estudo.]],
) <fig-funil>

== Os três portões de integridade

Três verificações automáticas impedem que a auditoria produza conclusão falsa,
e as três entraram no pipeline depois de detectarem erro real. @fig-portoes
mostra as cinco estações do caminho e as três barreiras. O primeiro portão
exige que o arquivo baixado contenha o próprio título do registro; ele pegou
cinco arquivos que eram de outro artigo, por colisão de nome no
re-arquivamento.#footnote[audit_70 §inventario: `inventario / por_status / texto_incorreto`.]
O segundo recusa página de rosto como texto completo. O terceiro é o mais
importante para a leitura dos resultados: encontrar o sobrenome só na
bibliografia de uma página de rosto de editora não prova citação-fantasma,
prova apenas que o corpo não foi obtido.

Uma barreira não descarta o registro. Ela reclassifica o status e devolve o
registro para a próxima coleta poder relê-lo. A exceção é o veredito terminal
`aresta_falsa`, que significa PDF obtido, corpo verificado, e nenhuma menção ao
trabalho auditado em lugar nenhum. Isso é o oposto de falta de evidência: é
evidência negativa completa, e uma rodada anterior do primeiro portão chegou a
sobrescrevê-la, apagando o achado. Os portões agora pulam todo status terminal
em vez de recalculá-lo.

#figure(
  scale(x: 76%, y: 76%, reflow: true, box(width: 210mm, fig-portoes())),
  caption: [Cinco estações e três barreiras. Uma barreira reclassifica o status e devolve o registro ao pipeline; só a aresta falsa é veredito terminal, porque é evidência negativa completa.],
) <fig-portoes>

== Cobertura por quartil, e o viés que ela carrega

Dentro dos registros com DOI cujo periódico tem quartil Scimago oficial, a
cobertura de evidência é desigual, e a desigualdade tem direção. São 98
registros ao todo: 69 em Q1, 16 em Q2, 8 em Q3 e 5 em
Q4.#footnote[audit_70 §cobertura: `cobertura_quartil / Q1`…`Q4 / total` e `cobertura_quartil / total / total`.]
Em Q1, 58 têm trecho literal recuperado, ou 84%; em Q4, apenas 1 de 5, ou
20%.#footnote[audit_70 §cobertura: `cobertura_quartil / Q1 / pct_trecho` e `cobertura_quartil / Q4 / pct_trecho`.]
Somando trecho literal e fantasma verificado, que são dois tipos de evidência e
não um tipo de falta, a cobertura total é de 80 em 98, ou
82%.#footnote[audit_70 §cobertura: `cobertura_quartil / total / pct_evidencia`.]
Restam 17 registros sem evidência.#footnote[audit_70 §cobertura: `cobertura_quartil / total / pendente`.]

Isso não foi desenho. É efeito colateral de a Elsevier, que concentra os Q1 das
duas áreas, ter liberado texto completo pelo acesso institucional, enquanto
Emerald e Wiley não liberaram. O viés é favorável à análise, porque a evidência
é mais densa onde o impacto importa mais, mas precisa ser declarado por uma
razão prática: a estatística de Q4 se apoia em uma observação e não sustenta
comparação entre quartis. Por artigo, o desequilíbrio é o mesmo em outra
escala: aviação tem 43 de 50 com trecho, ou 86%, e grãos 31 de 48, ou
65%.#footnote[audit_70 §cobertura: `cobertura_quartil / por_artigo / airline / total / pct_trecho` e o mesmo para `grains`.]

#figure(
  image("/reports/01-impacto/figuras/fig02_cobertura_quartil.png", width: 88%),
  caption: [A cobertura de evidência cai monotonicamente do Q1 ao Q4, de 84% a 20% de trechos literais, por bloqueio de acesso de editora e não por desenho amostral.#footnote[audit_70 §cobertura: `cobertura_quartil / Q1 / pct_trecho` e `cobertura_quartil / Q4 / pct_trecho`.]],
) <fig-cobertura>

= 3. Onde as citações caem

O achado desta seção é que os dois artigos são citados em veículos de topo, e
que o topo é mais concentrado do que a contagem bruta sugere. Entre as citações
com DOI e quartil atribuído, 69 estão em Q1, contra 16 em Q2, 8 em Q3 e 5 em
Q4.#footnote[audit_70 §quartil: `quartil / todas_citacoes / pooled`.]
Outros 35 registros ficam fora do Scimago e 43 não têm métrica
alguma.#footnote[audit_70 §quartil: `quartil / todas_citacoes / pooled / fora_do_scimago` e `sem_metrica`.]
A ausência do Scimago não é um bloco só. De 49 decisões de ausência, 32 estão
corretamente fora, porque não são artigo de periódico, e 17 são periódico de
verdade ausente do Scopus, quase todos regionais.#footnote[audit_70 §quartil: `quartil / ausencia / correto`, `periodico` e `total_decisoes`.]
Tratar os dois grupos como um só seria erro: o primeiro é comportamento correto
da base, o segundo é limitação de cobertura geográfica.

#figure(
  image("/reports/01-impacto/figuras/fig03_quartis.png", width: 84%),
  caption: [A citação está majoritariamente em Q1: 69 dos 98 registros com quartil atribuído, contra 5 em Q4.#footnote[audit_70 §quartil: `quartil / todas_citacoes / pooled / Q1` e `Q4`; audit_70 §cobertura: `cobertura_quartil / total / total` para o denominador.]],
) <fig-quartis>

== Periódicos e editoras

A distribuição por periódico é de cauda longa com uma cabeça clara. O
_Journal of Air Transport Management_ concentra 10 citações classificadas, e
_Transport Policy_ vem em seguida com 5.#footnote[audit_70 §periodicos: `periodicos / pooled / 0 / n` e `periodicos / pooled / 1 / n`.]
Depois disso a cauda cai para três, duas e uma citação por veículo. A tabela
abaixo lista os principais, com quartil, SJR e a coluna Overton do Scimago, que
conta citações do periódico em documento de política pública.

#tabela(
  [Os periódicos que mais citam, com o SJR e a contagem Overton do veículo. Overton é sinal do periódico, não do artigo: diz que o trabalho circula onde política pública bebe, não que alguma citação chegou a um documento de política.],
  "tab-periodicos",
  _cols-periodicos,
  [*Periódico*], [*Citações*], [*Quartil*], [*SJR*], [*Overton*],
  ..D.periodicos.pooled.slice(0, 8).map(j => (
    text(size: 6.9pt)[#txt(j.nome_norm)],
    [#num(j.n)],
    [#txt(j.quartil)],
    [#txt(if j.sjr == none { none } else { j.sjr.txt })],
    [#txt(if j.overton == none { none } else { j.overton.txt })],
  )).flatten(),
  fonte: [`reports/01-impacto/dados.json`, bloco `periodicos`; SJR e Overton do Scimago 2025 @scimago2025.],
)

Por editora, a concentração é ainda maior e explica o viés de cobertura da
seção anterior. A Elsevier responde por 49 das citações classificadas, a
Springer por 15, a Taylor & Francis por 7, e Emerald e MDPI por 6
cada.#footnote[audit_70 §editoras: `editoras / pooled`.]
Outras 54 estão em veículos que não constam da lista de editoras estabelecidas
de `config.json`.#footnote[audit_70 §editoras: `editoras / pooled / não listada em config.editoras_estabelecidas`.]
A leitura prática: quem liberou o texto foi quem publica o Q1 das duas áreas, e
por isso a evidência é boa justamente onde interessa e ruim onde não se
conseguiu entrar.

#figure(
  image("/reports/01-impacto/figuras/fig04_periodicos.png", width: 88%),
  caption: [Cauda longa com cabeça curta: o periódico mais citante concentra 10 das citações lidas e o segundo, 5; do quarto em diante o veículo aparece uma ou duas vezes.#footnote[audit_70 §periodicos: `periodicos / pooled`, campos `n`.]],
) <fig-periodicos>

== A linha do tempo

As duas curvas têm formas diferentes porque os artigos têm idades diferentes. O
de aviação, de 2016, acumula citação de passagem desde 2017 e só passa a
receber citação de conteúdo com regularidade a partir de 2021. O de grãos, de
2019, entra em regime mais rápido e concentra o volume entre 2022 e 2025. Em
nenhum dos dois há sinal de queda: os dois anos mais recentes ainda estão em
formação, porque o grafo de citações leva meses para registrar publicação nova.

#figure(
  image("/reports/01-impacto/figuras/fig09_linha_do_tempo.png", width: 88%),
  caption: [Citação de passagem domina os dois artigos em todos os anos; a citação de conteúdo aparece tarde no artigo de aviação e é rara no de grãos.#footnote[audit_70 §linha-do-tempo: `linha_do_tempo / airline` e `linha_do_tempo / grains`, séries `passagem`, `conteudo`, `fundo` e `fantasma`.]],
) <fig-linha-do-tempo>

= 4. Como cada artigo é citado

O achado desta seção é o mais direto do relatório: a citação típica é rasa e
elogiosa, e o erro, quando aparece, quase nunca é hostil. Dos
#D.meta.n_classificados registros lidos, 92 mencionam o artigo no corpo do
texto e 12 constam só na lista de referências.#footnote[audit_70 §eixos: `eixos / pooled / presence / in_text / n` e `reference_list_only / n`.]
Tudo o que segue nesta seção se lê sobre as 92 menções no corpo, porque
profundidade, postura e exatidão só se aplicam quando há texto para julgar.

== Profundidade

A escala ordinal de cinco níveis se concentra no segundo degrau. São 53
citações de menção breve, ou 57,6% do total, mais 15 de passagem em bloco, ou
16,3%.#footnote[audit_70 §eixos: `eixos / pooled / depth / brief_mention` e `drive_by`.]
Somados, os dois níveis rasos dão 68 citações, ou
73,9%.#footnote[audit_70 §eixos: `eixos / pooled / perfunctorio`.]
No outro extremo, 5 citações sustentam parte do argumento do citante e 4 o
tomam como fundacional, ou 9,8% dos casos ao
todo.#footnote[audit_70 §eixos: `eixos / pooled / depth / supporting`, `foundational` e `eixos / pooled / substantivo`.]
A distância entre os dois patamares é o resultado central do eixo: nove
citações em cada dez são pano de fundo.

Um exemplo de citação em bloco, do `grains_057`, no
_Journal of Stored Products Research_:

#quote(block: true)[
  "Cereals, oilseeds and legumes are vital components of human food and animal
  feeds (Bendinelli et al., 2020)."
]

A frase é verdadeira e o artigo a sustenta, mas qualquer fonte da área também
sustentaria. É o caso-limite que separa passagem em bloco de menção breve: a
menção breve atribui ao artigo uma afirmação *específica*, e a passagem em
bloco não. Compare com `airline_026`, no _Transport Policy_, classificada como
citação que sustenta o desenho do citante:

#quote(block: true)[
  "Following Bendinelli et al. (2016), our study includes variables to control
  for concentration both at airport and market levels."
]

A régua aqui é a de METHOD.md §6: o citante mudaria de desenho se o artigo não
existisse? Nesse caso mudaria, e a classificação vem acompanhada da marca de
reuso `method_adoption`.

#figure(
  image("/reports/01-impacto/figuras/fig05_profundidade.png", width: 88%),
  caption: [A profundidade se concentra no segundo degrau da escala: 53 menções breves contra 4 citações fundacionais, num total de 92 menções no corpo.#footnote[audit_70 §eixos: `eixos / pooled / depth`, todos os níveis.]],
) <fig-profundidade>

== Postura e exatidão

A postura é quase sempre de apoio: 81 citações, ou 88,0%, com 9 sem postura
declarada e apenas 2 contrapondo.#footnote[audit_70 §eixos: `eixos / pooled / stance / supporting`, `none` e `contradictory`.]
Vale lembrar que a regra de postura é deliberadamente liberal: qualquer
contraponto conta, mesmo sem linguagem hostil, mesmo quando o citante também
usa o artigo como referência de comparação. Sob uma régua tão frouxa, duas
contraposições em #D.eixos.pooled.presence.in_text.n citações são um número
muito baixo, e a leitura correta
não é que os artigos são incontestáveis, e sim que quase ninguém os discute.

A exatidão conta outra história. São 57 citações fiéis, ou 62,0%; 19 imprecisas,
ou 20,7%; e 16 com má atribuição, ou 17,4%.#footnote[audit_70 §eixos: `eixos / pooled / accuracy / accurate`, `imprecise` e `misrepresented`.]
Os dois artigos se comportam de modo diferente. No de aviação, 71,2% das
citações são fiéis e 13,5% são má atribuição; no de grãos, 50,0% e
22,5%.#footnote[audit_70 §eixos: `eixos / airline / accuracy` e `eixos / grains / accuracy`.]
A explicação não é misteriosa: o artigo de grãos abre com definições e
estimativas repassadas de terceiros, e é exatamente esse material que os
citantes creditam aos autores.

#figure(
  image("/reports/01-impacto/figuras/fig06_postura_acuracia.png", width: 88%),
  caption: [Postura e exatidão andam em direções opostas: 88,0% das citações apoiam, mas só 62,0% dizem o que o artigo de fato diz.#footnote[audit_70 §eixos: `eixos / pooled / stance / supporting` e `eixos / pooled / accuracy / accurate`.]],
) <fig-postura>

== Distorção

Quando a exatidão falha, o sub-código diz de que tipo é a falha, na tipologia
de @greenberg2009. O tipo mais comum é `diversion`, com 16 casos: o conteúdo do
artigo é citado com significado diferente do original.#footnote[audit_70 §eixos: `eixos / pooled / distortion`, todos os sub-códigos.]
Vêm depois `dead_end`, com 11, em que o artigo é usado para sustentar afirmação
sobre a qual não tem conteúdo relevante; `relayed_attribution`, com 5; e
`transmutation`, com 3.

O caso de `diversion` mais nítido é o `airline_032`, no
_Journal of Air Transport Management_:

#quote(block: true)[
  "Bendinelli, Bettini and Oliveira (2016) investigate the impact of
  operational performance on airline cost structure and show that flight
  activity outside schedule windows, delay and schedule buffers impact airline
  costs substantially."
]

O artigo não trata de estrutura de custo. Trata de atraso, internalização de
congestionamento e entrada de companhia de baixo custo. O objeto está errado, e
o erro se propaga: quem lê essa frase e cita a partir dela cita um artigo que
não existe.

#figure(
  image("/reports/01-impacto/figuras/fig07_distorcao.png", width: 84%),
  caption: [Entre as citações inexatas, o desvio de significado domina com 16 casos, seguido pelo uso do artigo para afirmação sobre a qual ele nada diz, com 11.#footnote[audit_70 §eixos: `eixos / pooled / distortion / diversion` e `dead_end`.]],
) <fig-distorcao>

== Profundidade cruzada com quartil

O cruzamento responde a uma pergunta prática: citação de periódico melhor é
citação melhor? A resposta é não, ou pelo menos não neste corpus. Em Q1 há 29
menções breves contra 3 citações fundacionais, e 7 casos de má
atribuição.#footnote[audit_70 §papel-quartil: `papel_quartil / pooled / matriz / Q1`.]
A proporção de citação rasa em Q1 é praticamente a mesma do resto. O que muda
com o quartil não é a profundidade da citação, é a chance de conseguir lê-la.

#figure(
  image("/reports/01-impacto/figuras/fig08_profundidade_quartil.png", width: 88%),
  caption: [O quartil do periódico citante não prevê profundidade: o Q1 tem 29 menções breves para 3 citações fundacionais, a mesma proporção rasa dos demais quartis.#footnote[audit_70 §papel-quartil: `papel_quartil / pooled / matriz`.]],
) <fig-profundidade-quartil>

= 5. O que os artigos de fato aportaram

O achado desta seção é que a literatura usa uma fatia estreita de cada artigo,
e que a fatia mais citada nem sempre é uma contribuição própria. Para medir
isso, o registro de afirmações extrai dos PDFs publicados
#D.alegacoes.total afirmações verificáveis, cada uma com citação literal
conferida contra três extrações independentes. São 30 do artigo de aviação e 33
do de grãos.#footnote[audit_70 §alegacoes: `alegacoes / por_artigo / airline / total` e `alegacoes / por_artigo / grains / total`.]
Por tipo: 27 achados, 14 afirmações sobre dados, 13 sobre método, 6 definições e
3 de política.#footnote[audit_70 §alegacoes: `alegacoes / por_type`.]
Por status, 41 são originais, #D.alegacoes.por_status.relayed são repassadas de
terceiros, 4 são limitações declaradas e 2 são interpretações dos próprios
autores.#footnote[audit_70 §alegacoes: `alegacoes / por_status`.]
Das #D.alegacoes.total, #D.alegacoes.claims.values().filter(c => c.n_citations > 0).len()
são sustentadas por ao menos uma citação mapeada; o restante nunca foi citado.

== O que os citantes tomam do artigo de aviação

A afirmação mais citada do artigo de aviação é o primeiro achado: concentração
no nível do aeroporto reduz o atraso, evidência de internalização de
congestionamento. Ela aparece em 18 citações, 17 delas
fiéis.#footnote[audit_70 §alegacoes: `alegacoes / claims / AIR-F01`.]
Em seguida vem o segundo achado, o de sinal oposto no nível da rota, com 9
citações e 2 más atribuições, e o arcabouço unificador que testa as duas
hipóteses num modelo econométrico só, com 8
citações.#footnote[audit_70 §alegacoes: `alegacoes / claims / AIR-F02` e `AIR-M01`.]
O efeito de spillover não-tarifário da entrada de companhia de baixo custo, que
dá título ao artigo, recebe 4 citações, todas
fiéis.#footnote[audit_70 §alegacoes: `alegacoes / claims / AIR-F05`.]

A leitura é clara. A literatura absorveu bem o par de resultados sobre
concentração, que é o núcleo empírico do artigo, e absorveu o desenho
econométrico que permite testá-los juntos. O achado que nomeia o trabalho, o
spillover não-preço para rotas não entradas, circula bem menos, apesar de ser a
novidade declarada. O artigo é lido como evidência sobre internalização de
congestionamento, não como evidência sobre efeito de transbordamento.

== O que os citantes tomam do artigo de grãos

No artigo de grãos a afirmação mais citada é a de síntese: há um trade-off
difícil entre ampliar a oferta de alimentos e o nível de perdas pós-colheita,
porque sem infraestrutura adequada, sobretudo armazenagem e comercialização, o
esforço para aumentar a oferta eleva a perda. Ela aparece em 11 citações, 10
delas fiéis.#footnote[audit_70 §alegacoes: `alegacoes / claims / GR-F09`.]
A recomendação de política que decorre dela recebe 7 citações, 6
fiéis.#footnote[audit_70 §alegacoes: `alegacoes / claims / GR-P01`.]
A definição de perda pós-colheita adotada no artigo também recebe 7 citações,
mas com desempenho muito pior: só 2 fiéis, contra 4 imprecisas e 1 má
atribuição.#footnote[audit_70 §alegacoes: `alegacoes / claims / GR-DEF01`.]

O contraste entre as duas linhas é o achado. O que o artigo aporta de próprio,
o painel global que estima os determinantes macroeconômicos da perda de grãos,
com o produto por habitante como determinante de maior impacto, a relação
não-linear entre desenvolvimento e perda, e o efeito do excedente alimentar
sobre a perda, é citado com fidelidade. O que ele apenas organiza da
literatura, a definição de perda e as estimativas de magnitude, é citado com
erro.

== Repasse virando achado próprio

Cinco citações atribuem aos autores, como achado próprio, algo que o artigo
apenas repassa de terceiros.#footnote[audit_70 §eixos: `eixos / pooled / distortion / relayed_attribution`.]
No artigo de grãos, a faixa de perda de grãos por região e a fração da produção
global perdida vêm de Gustavsson et al. (2011), e a fórmula da variável
dependente vem de Gustavsson et al. (2013). No artigo de aviação, a dissuasão
estratégica de entrada em hubs vem de Molnar (2013), e a relação entre ausência
de concorrência e atraso vem de um relatório do inspetor-geral da autoridade de
aviação civil norte-americana. Um exemplo, do `grains_040`, publicado no mesmo
periódico do artigo citado:

#quote(block: true)[
  "Food loss and waste (FLW) sums one-third of the total food produced globally
  for human consumption, about 1.3 billion tons of food (Priefer et al., 2016;
  Bendinelli et al., 2020)."
]

O número está no artigo. Não é do artigo. Essa é a distinção que o registro de
afirmações torna operacional, e é ela que o codificador original não conseguia
ver sem o registro, como mostra a §1.

== Reuso efetivo

O sinal mais forte de impacto real é o reuso, e ele é raro. Cinco citações
adotam método do artigo, e nenhuma valida resultado, reusa dado, usa o trabalho
como referência de comparação ou o
estende.#footnote[audit_70 §eixos: `eixos / pooled / reuse`, todas as tags.]
As cinco se dividem entre os dois trabalhos: 3 no artigo de aviação e 2 no de
grãos.#footnote[audit_70 §eixos: `eixos / airline / reuse / method_adoption` e `eixos / grains / reuse / method_adoption`.]
A régua aqui é estrita, e ficou mais estrita depois do teste cego: declarar
"estendemos a literatura de X" citando o artigo num bloco não é reuso; replicar
o tratamento de endogeneidade, o instrumento ou a construção de variável é.

#figure(
  image("/reports/01-impacto/figuras/fig10_alegacoes.png", width: 88%),
  caption: [Poucas afirmações concentram quase todas as citações: o achado de internalização de congestionamento aparece em 18 citações e o trade-off entre oferta e perda em 11, enquanto a maioria das afirmações nunca é citada.#footnote[audit_70 §alegacoes: `alegacoes / claims / AIR-F01` e `GR-F09`.]],
) <fig-alegacoes>

= 6. Antes e depois: deslocou ou consolidou?

O achado desta seção vem antes de qualquer leitura substantiva, e é sobre a
régua. Dois índices de disrupção calculados sobre o mesmo grafo, com os mesmos
dados e na mesma janela, apontam em direções opostas para o artigo de aviação.
O índice CD padrão fica praticamente em zero, com CD5 de −0,011 e IC95% de
−0,020 a −0,001.#footnote[audit_70 §cd: `cd / airline / cd_index / windows / 5`, campos `CD` e `ci_95 / CD`.]
O DI5, que só conta como antecessor compartilhado o citante que traz cinco
referências em comum, lê o mesmo artigo como deslocador, com 0,600 e IC95% de
0,395 a 0,781.#footnote[audit_70 §cd: `cd / airline / cd_index / windows / 5`, campos `DI5 / value` e `ci_95 / DI5`.]
Não é erro de cálculo. É a dependência de variante que @leibel2024 descrevem
como um multiverso de indicadores, e que @bornmann2020 já haviam exposto ao
testar DI1 contra DI5 diante de avaliação por pares.

== Por que os dois índices discordam

@fig-cd-mecanismo mostra o desenho. Quem publica depois do artigo pode citar o
artigo sem citar os antecessores dele, citar os dois, ou citar só os
antecessores. O índice é a diferença entre os dois primeiros grupos dividida
pelo total, e vale mais um quando todo trabalho posterior cita o artigo e
ignora os antecessores.

#figure(
  fig-cd(),
  caption: [O índice de disrupção lido como grafo: quem publica depois cita o artigo sozinho, o artigo com os antecessores, ou só os antecessores. O terceiro grupo domina o denominador e comprime o índice perto de zero.],
) <fig-cd-mecanismo>

O terceiro grupo é o problema. Na janela de cinco anos do artigo de aviação
existem 7 citantes do primeiro tipo e 18 do segundo, contra 1.016 do
terceiro.#footnote[audit_70 §cd: `cd / airline / cd_index / windows / 5`, campos `n_i`, `n_j` e `n_k`.]
O numerador tem dezenas, o denominador tem milhares, e o resultado é
aritmeticamente obrigado a ficar perto de zero, qualquer que seja o conteúdo
das citações. É a compressão que @wu2019b apontaram, e a variante que descarta
o terceiro grupo devolve, para os mesmos dados, um valor de −0,440, isto é, o
lado consolidador da escala.#footnote[audit_70 §cd: `cd / airline / cd_index / windows / 5 / CD_nok`.]

O DI5 responde a outra pergunta. Ele só admite no grupo dos absorvidos o
citante que compartilha cinco ou mais referências com o artigo, e joga fora do
universo inteiro quem compartilha entre uma e quatro. Sobram 23 citantes do
primeiro tipo, 2 do segundo e 10 do
terceiro.#footnote[audit_70 §cd: `cd / airline / cd_index / windows / 5 / DI5`, campos `n_i`, `n_j` e `n_k`.]
O índice sobe para 0,600 na janela de cinco anos e 0,661 na de dez, com IC95%
de 0,509 a 0,804.#footnote[audit_70 §cd: `cd / airline / cd_index / windows / 5 / DI5` e `windows / 10 / DI5`, com `ci_95 / DI5`.]
Lido como está, o DI5 diz que quem cita o artigo de aviação em profundidade
raramente cita junto o bloco de antecessores dele. Lido com cuidado, diz que
sobraram poucos casos para julgar.

O artigo de grãos não produz sinal em nenhuma das duas leituras. O CD5 é 0,001,
com IC95% de −0,001 a 0,003, e o DI5 é 0,306, com IC95% de 0,207 a
0,412.#footnote[audit_70 §cd: `cd / grains / cd_index / windows / 5`, campos `CD`, `DI5 / value` e `ci_95`.]
A compressão é ainda mais severa que na aviação, com 7.114 obras no terceiro
grupo, e a janela de dez anos não existe: o artigo é de 2019, e o script
trunca o slot em sete anos e marca a
truncagem.#footnote[audit_70 §cd: `cd / grains / cd_index / windows / 5 / n_k` e `windows / 10 / t` contra `t_nominal`.]
Ler qualquer um dos dois valores como veredito sobre a contribuição do artigo
seria confundir uma propriedade da vizinhança de citação com uma propriedade do
trabalho.

#figure(
  image("/reports/01-impacto/figuras/fig13_cd.png", width: 100%),
  caption: [O índice CD do artigo de aviação fica colado em zero nas quatro janelas enquanto o DI5 o lê como deslocador: −0,011 contra 0,600 na janela de cinco anos, sobre exatamente o mesmo grafo.#footnote[audit_70 §cd: `cd / airline / cd_index / windows`, campos `CD` e `DI5 / value` em cada janela.]],
) <fig-cd>

== O que a leitura de passagem acrescenta ao índice

O índice separa os citantes em grupos sem olhar para o que eles dizem. Como
esta auditoria leu as passagens, dá para perguntar se os dois grupos citam de
maneira diferente. Cruzando o status na janela de cinco anos com a
profundidade, o artigo de aviação tem cinco citantes classificados no grupo que
o cita sem citar os antecessores, e nenhum deles é substantivo; as citações
fundacionais e as que sustentam o desenho do citante estão todas no grupo que
cita os dois lados. O teste exato de Fisher sobre essa tabela não rejeita
independência.#footnote[`data/cd/cd_airline.json`, bloco `crosstab_t5`, campos `n_classified`, `role` e `fisher_substantive`. O bloco ainda não é exportado para `numeros.txt`.]

O resultado é pequeno, e por isso mesmo instrutivo. A crítica corrente ao
índice, resumida por @leibel2024, é que ele mede prática de citação e não
conteúdo. Um repositório com passagem literal pode responder a isso de forma
empírica, cruzando o grupo do índice com o papel da citação, e aqui a resposta
é que o grupo não prevê o papel. Eclipsar os antecessores, neste corpus, é o
que fazem as citações rasas.

== Deixando uma referência de fora por vez

A outra maneira de sondar a fragilidade do índice é removê-lo peça por peça. O
procedimento recalcula o CD5 tirando uma referência do conjunto de cada vez.
Nenhuma remoção move o resultado além da terceira casa decimal, nos dois
artigos. As duas que mais pesam no artigo de aviação puxam para lados opostos:
tirar a referência metodológica sobre valoração de bens novos empurra o CD5
para baixo, e tirar o estudo sobre congestionamento aeroportuário com poder de
mercado o empurra para
cima.#footnote[`data/cd/cd_airline.json` e `cd_grains.json`, bloco `loo_cd5`, campo `top5_abs_delta`. O bloco ainda não é exportado para `numeros.txt`.]
No artigo de grãos, todas as cinco remoções mais influentes movem o valor na
mesma direção, o que é coerente com um índice já colado em zero. A conclusão
prática é que a instabilidade do CD aqui não vem de uma referência específica.
Vem do denominador.

== Co-citação: o campo passou a ler as duas vertentes juntas?

A segunda medida é a co-citação de @small1973, e responde a outra pergunta. O
artigo de aviação declara conciliar duas vertentes da literatura de atrasos: a
da internalização de congestionamento no aeroporto e a da relação entre
competição e qualidade na rota. As sementes das duas vertentes saem das
próprias seções de revisão do artigo, dez referências de um lado e oito do
outro, e o universo é o conjunto de obras que citam ao menos uma
semente.#footnote[`data/cocit/seeds_airline.json` para a partição, com o cabeçalho de seção e a citação literal que a justificam; `data/cocit/cocit_airline.json` para o universo.]
Só a co-citação dá um antes e um depois genuínos, porque é definida pelo
comportamento posterior da comunidade e não pela lista de referências do
próprio artigo, que é o que o acoplamento bibliográfico de @kessler1963 mede.

A fração de obras que citam as duas vertentes sobe de 0,053, ou 29 de 543 antes
de 2016, para 0,085, ou 48 de 565 depois, uma diferença de
0,032.#footnote[audit_70 §cocitacao: `cocitacao / periods / main`, campos `pre` e `post`, `share_AB` e `N_union`, e `delta_share_AB`.]
O cosseno de Salton acompanha, de 0,104 para 0,157. O teste exato de Fisher
sobre período contra citar as duas vertentes dá p de 0,044, e uma permutação
com 10.000 embaralhamentos do ano dentro do universo dá p de
0,043.#footnote[audit_70 §cocitacao: `cocitacao / tests`, blocos `fisher_period_x_cocites_both` e `permutation_delta_share_AB_main`.]

Os placebos ajudam a localizar o salto no tempo. Movendo o corte para 2011, a
diferença some e fica em −0,001; movendo para 2020, ela cai para 0,011; e a
variante que trata 2016 como zona de exclusão preserva o efeito, com
0,029.#footnote[audit_70 §cocitacao: `cocitacao / periods`, blocos `placebo_2011`, `placebo_2020` e `sensitivity`, campo `delta_share_AB`.]
O deslocamento está no ano do artigo, e não em qualquer corte arbitrário da
série.

#figure(
  image("/reports/01-impacto/figuras/fig14_cocitacao.png", width: 100%),
  caption: [A fração de obras que co-citam as duas vertentes sobe de 0,053 para 0,085 no corte de 2016, e nenhum dos dois placebos reproduz o salto.#footnote[audit_70 §cocitacao: `cocitacao / periods / main` e os blocos `placebo_2011` e `placebo_2020`.]],
) <fig-cocit>

== Quem faz a ponte

A pergunta seguinte é se o artigo está no caminho. Entre as obras que citam as
duas vertentes depois de 2016, a fração que também cita o artigo é de 0,292, ou
14 de 48; entre as que citam uma vertente só, é de 0,035, ou 18 de
517.#footnote[audit_70 §cocitacao: `cocitacao / brokerage`, blocos `AB` e `single_strand`, campos `rate`, `k_cites_focal` e `n`.]
A razão de chances é de 11,4, e o teste binomial exato contra a taxa de
vertente única rejeita a igualdade com p abaixo de
0,001.#footnote[audit_70 §cocitacao: `cocitacao / brokerage`, campos `odds_ratio_AB_vs_single` e `binom_test_AB_vs_single_p0`.]
Visto do outro lado, dos 49 citantes do artigo na janela, 14 citam as duas
vertentes.#footnote[audit_70 §cocitacao: `cocitacao / brokerage`, campos `n_focal_citers_in_window` e `AB / k_cites_focal`.]

A confirmação mais direta não é estatística, é textual. Dois citantes dizem
literalmente que o artigo concilia as duas vertentes, e os dois são registros
já classificados nesta auditoria: `10.1016/j.tra.2018.10.012` e
`10.1016/j.tre.2022.103000`.#footnote[audit_70 §cocitacao: `cocitacao / passage_confirmation / n_hits`; as passagens estão em `data/classify.json`, registros `airline_039` e `airline_016`.]
O segundo, no _Transportation Research Part E_, é a descrição mais precisa que
qualquer citante fez do trabalho:

#quote(block: true)[
  "Bendinelli et al. (2016) try to conciliate these two strands of the
  literature by presenting a single econometric model to test both the
  “congestion internalization effect” and the “competition-quality effect”."
]

A ressalva de METHOD.md vale inteira, e não foi levantada pelos resultados:
sem contrafactual pareado, isto é descritivo. Não há um par de vertentes de
tamanho, idade e densidade comparáveis, sem artigo focal equivalente, contra o
qual comparar a subida. A área pode estar integrando as duas literaturas por
conta própria, e o artigo pode ser um sintoma dessa integração em vez de causa
dela. O que os números sustentam é mais modesto e ainda assim útil: as duas
vertentes passaram a ser citadas juntas com mais frequência depois de 2016, o
salto não aparece em cortes placebo, e quem faz a ponte cita o artigo dez vezes
mais que quem fica de um lado só.

== Limites de base

Os dois cálculos rodaram com o Semantic Scholar como backend, porque a cota
diária do OpenAlex tinha zerado. A troca deixa marca. O `s2_citation_count` do
artigo de aviação e o do de grãos ficam abaixo do `cited_by_count` do OpenAlex,
entre 8% e 10% menos citantes nos dois
casos.#footnote[`data/cd/cd_airline.json` e `cd_grains.json`, bloco `checks_global`, campos `cited_by_count`, `s2_citation_count` e `n_p_citers_all_time`. O bloco ainda não é exportado para `numeros.txt`.]
O mapeamento de identificadores também perde peças: 6 das 26 referências
válidas do artigo de aviação e 5 das 35 do de grãos não encontraram par no
Semantic Scholar.#footnote[audit_70 §cd: `cd / airline / refs_audit / n_valid` e `cd / grains / refs_audit / n_valid`; o detalhe do que não mapeou está em `data/cd/id_map_airline.json` e `id_map_grains.json`.]
Elas ficaram fora do conjunto de referências que alimenta o índice.

Isso não é ruído a ser escondido no rodapé. A dependência de base é um
resultado da literatura de índices de disrupção, documentado por @leibel2024, e
um valor de CD só significa alguma coisa acompanhado da base, da janela, da
variante e do conjunto de referências que o produziu. Este relatório reporta os
quatro.

= 7. Anomalias

O achado desta seção é que quase toda anomalia detectada é, na verdade, um
limite de acesso disfarçado de achado. A auditoria dedicada de citações-fantasma
reexaminou cada entrada marcada como presente apenas na lista de referências,
com uma régua mais dura que a original: exige corpo real comprovado no disco,
não a leitura do codificador via acesso institucional. Das entradas
reexaminadas, apenas 1 sobrevive como fantasma genuíno e 11 viram corpo
indisponível; nenhuma é falha de extração e nenhuma é aresta
falsa.#footnote[audit_70 §fantasmas: `fantasmas_auditados / summary / counts_by_category`.]

Isso não refuta o achado original. É um pedido de reverificação. A limitação de
proveniência é explícita: os corpos lidos por acesso institucional não foram
persistidos, então a auditoria não consegue reproduzir a leitura que o
codificador fez. O único fantasma que sobrevive à régua dura tem corpo real no
disco, com mais de vinte mil caracteres antes da seção de referências, e zero
menções ao trabalho auditado no texto.

Um caso mudou de veredito na direção oposta, e é o mais instrutivo. O registro
`grains_024` estava classificado como fantasma; a auditoria localizou o
marcador sobrescrito da citação no corpo e o reclassificou como menção no
texto. Quer dizer: a extração de passagem não reconhecia marcador sobrescrito,
e o que parecia ausência era falha de leitura do extrator. Um portão que só olha
para o sobrenome do autor não vê citação numérica.

== Arestas falsas, autocitação e duplicata

Duas arestas do grafo de citações são falsas: `airline_s008`, em
_The Economics of Airport Operations_, e `grains_s001`, no
_Journal of Horticultural Science and Biotechnology_. Nos dois casos o PDF
completo foi obtido, passou no portão de título, e o sobrenome não aparece nem
no corpo nem na bibliografia. São os únicos registros com evidência negativa
completa, e por isso ganham veredito terminal em vez de voltar ao pipeline.

O vínculo de autoria é quase todo independente: 100 registros sem vínculo, 3 de
coautor e 1 autocitação.#footnote[audit_70 §eixos: `eixos / pooled / relation`.]
Autocitação e citação de coautor não são falha, mas não medem alcance
independente, e por isso ficam fora do indicador de reuso metodológico externo.
Há ainda 3 registros marcados como publicação duplicada, todos do artigo de
grãos: o mesmo trabalho publicado duas vezes na mesma série de anais, com o
texto reescrito por sinônimos entre as
versões.#footnote[audit_70 §eixos: `eixos / grains / record_flags / duplicate_publication`.]
A deduplicação por DOI e título normalizado fundiu os registros, o que é
correto para contagem e apagaria o sinal se o registro absorvido tivesse sido
descartado. A regra adotada manda arquivá-lo em `data/classify_orfas.json` com
o motivo, e transferir para o registro sobrevivente qualquer achado que só
existia nele.

#tabela(
  [O inventário de anomalias por tipo. As duas maiores categorias são de exatidão, não de integridade do grafo: imprecisão e má atribuição somam mais que todo o resto junto.],
  "tab-anomalias",
  _cols-anomalias,
  [*Tipo*], [*Registros*], [*O que é*],
  [imprecisão], [#num(D.anomalias.por_tipo.imprecise)], text(size: 6.9pt)[leitura discutível ou ampliada, não demonstravelmente falsa],
  [má atribuição], [#num(D.anomalias.por_tipo.misrepresented)], text(size: 6.9pt)[objeto, método ou achado errado atribuído ao artigo],
  [fantasma], [#num(D.anomalias.por_tipo.fantasma)], text(size: 6.9pt)[presente só na lista de referências, sem menção no corpo],
  [coautor], [#num(D.anomalias.por_tipo.coauthor)], text(size: 6.9pt)[citação assinada por coautor do artigo citado],
  [publicação duplicada], [#num(D.anomalias.por_tipo.duplicate_publication)], text(size: 6.9pt)[mesmo texto publicado duas vezes, fundido na deduplicação],
  [aresta falsa], [#num(D.anomalias.por_tipo.aresta_falsa)], text(size: 6.9pt)[corpo verificado, nenhuma menção: evidência negativa completa],
  [autocitação], [#num(D.anomalias.por_tipo.self)], text(size: 6.9pt)[citação assinada por autor do artigo citado],
  fonte: [`reports/01-impacto/dados.json`, bloco `anomalias`; o detalhe registro a registro está em `anomalias.registro`.],
)

= 8. Taxa-base: este estudo contra a literatura

O achado desta seção é que os números deste estudo só significam alguma coisa
contra uma taxa-base publicada, e que a comparação exige cuidado com o
denominador. A tabela abaixo põe cada indicador ao lado do comparador mais
próximo na literatura, com o denominador explícito e o intervalo de confiança
de Wilson. Quatro denominadores diferentes aparecem, e confundi-los inverte
conclusões: `D_read` são todas as entradas classificadas, `D_text` são as
menções no corpo, `D_ind` são as menções no corpo com vínculo independente, e
`D_pop` é a população de METHOD.md
§9.#footnote[audit_70 §taxa-base: `taxa_base / denominators`.]

#tabela(
  [Cada indicador contra o comparador publicado mais próximo, com denominador explícito e IC95% de Wilson. Nenhum valor publicado foi reverificado nesta rodada: os doze estão marcados como pendentes no bloco de origem.],
  "tab-taxa-base",
  _cols-taxa,
  [*Indicador*], [*Denom.*], [*Este estudo*], [*IC95%*], [*Literatura*],
  ..D.taxa_base.rows.map(r => (
    text(size: 6.9pt)[#_rotulo(r.indicator)],
    text(size: 6.9pt)[#raw(r.denominator_label)],
    [#pct(r.results.pooled.at("rate", default: none))],
    text(size: 6.6pt)[#pct(r.results.pooled.ci95_wilson.at(0)) a #pct(r.results.pooled.ci95_wilson.at(1))],
    text(size: 6.6pt)[#lit(r.published)],
  )).flatten(),
  fonte: [`data/base_rates.json` via `tools/audit_68_base_rates.py`; comparadores de @boyack2018, @jergas2015, @catalini2015, @moravcsik1975, @valenzuela2015, @cohan2019 e @bornmann2025.],
)

Três leituras merecem destaque, e as três dependem de o denominador estar
certo. A primeira: a citação-fantasma deste estudo é 1 em 104 sob a régua
dura.#footnote[audit_70 §fantasmas: `fantasmas_auditados / summary / ghost_rate / D_read`.]
É praticamente a taxa-base publicada, e não as várias vezes ela que a contagem
bruta sugeria antes da auditoria da §7. A segunda: a citação perfunctória bate
68 em 92, bem acima dos comparadores de função de
citação.#footnote[audit_70 §taxa-base: `taxa_base / rows`, linha `perfunctory`, `results / pooled`.]
Isso é esperado num corpus de dois artigos de método aplicado. A terceira: a má
atribuição, na categoria maior, é 16 em
92.#footnote[audit_70 §taxa-base: `taxa_base / rows`, linha `misrepresented_major`, `results / pooled`.]
O comparador direto para essa categoria isolada não existe na literatura
consultada, porque os estudos de erro de citação em geral somam erro menor e
erro maior num total só.

Uma ressalva de integridade fecha a seção. Os doze valores de literatura da
tabela estão todos com `verification_status` igual a `pendente`. Eles vieram da
revisão em `docs/revisao-literatura.md` e ainda não foram reconferidos contra o
texto original de cada fonte. Enquanto isso não acontecer, a coluna da
literatura é orientação, não resultado.

#figure(
  image("/reports/01-impacto/figuras/fig12_taxa_base.png", width: 88%),
  caption: [Cada indicador com seu IC95% de Wilson contra o valor publicado. A citação perfunctória fica acima do comparador; a citação-fantasma, sob a régua dura da auditoria, fica na mesma ordem de grandeza dele.#footnote[audit_70 §taxa-base: `taxa_base / rows`, campos `results / pooled / rate` e `ci95_wilson`.]],
) <fig-taxa-base>

= 9. Limitações

Esta seção lista o que ainda não está validado. Ela existe porque um inventário
de qualidade de citação que esconde as próprias falhas não serve para nada.

*As afirmações não foram validadas pelo autor.* As #D.alegacoes.total
afirmações do registro têm `validated_by_author` igual a falso. Elas foram
extraídas dos PDFs publicados e conferidas contra três extrações independentes,
mas nenhuma passou pelo crivo de quem escreveu os artigos. Até que passem, o
registro vale como leitura de um segundo codificador, não como afirmação
confirmada. Como a §1 mostra, o registro é o instrumento que faz o eixo de
exatidão funcionar, então uma correção aqui muda rótulos lá.

*A codificação é de modelo, não de humano.* Os três codificadores são modelos
de linguagem. O protocolo de METHOD.md §17 prevê codificação humana em duas
frentes, e nenhuma delas rodou. Sem ela, a concordância medida diz que dois
modelos com o mesmo codebook convergem, o que é menos do que dizer que o
codebook é reprodutível por qualquer leitor treinado.

*A cobertura é desigual por editora.* Como mostra a §2, a evidência é densa em
Q1 porque a Elsevier liberou texto e rala em Q4 porque Emerald e Wiley não
liberaram. A soma por editora de METHOD.md §13 e a tabela de cobertura desta
auditoria divergiam por um registro; a diferença era a aresta falsa `grains_s001`,
que a lista de pendências carrega de propósito com a instrução de nada baixar, e
o METHOD passou a contar a partir de `audit_70`. Nenhuma comparação entre quartis deste relatório deve ser lida
como comparação de qualidade de citação por tier de periódico.

*A janela de passagem subdetecta profundidade.* Nos itens em que o pacote cego
mostrou uma janela automática em torno da menção, em vez do trecho curado, os
codificadores cegos não podiam ver que um citante menciona o artigo várias
vezes ao longo do texto, ou o identifica como referência única em outra seção.
O viés tem direção conhecida: a janela rebaixa citação fundacional para menção
de conteúdo, nunca o contrário.

*O estudo depende de bases que estão mudando.* O grafo de citações vem da união
de quatro APIs gratuitas, e a cobertura de referências do OpenAlex é incompleta
e não aleatória, como registra a própria documentação da base @openalex2022 e
como discute a literatura de índices de disrupção. A cota diária do OpenAlex
zerou no meio da §6, e o Semantic Scholar entrou como segundo caminho para a
mesma pergunta: conta menos citantes que o OpenAlex nos dois artigos, e deixa
de fora as referências que não encontram par entre as bases. Qualquer
reexecução deste relatório pode obter um inventário diferente, e é por isso que
`data/` é versionado junto com o código que o gera.

*O índice de disrupção depende da variante escolhida.* Como mostra a §6, o CD
padrão e o DI5 dão sinais opostos para o artigo de aviação sobre exatamente o
mesmo grafo, e o valor do CD é dominado pelo tamanho do terceiro grupo, não
pelo conteúdo das citações. Nenhum número de disrupção deste relatório deve ser
lido sozinho: ele só significa alguma coisa junto da base, da janela, da
variante e do conjunto de referências que o produziram. A co-citação é menos
frágil nesse aspecto, mas carrega a limitação declarada em METHOD.md de não ter
contrafactual pareado, então também é descritiva.

*Os comparadores de literatura estão pendentes.* Como diz a §8, os doze valores
publicados da tabela de taxa-base ainda não foram reconferidos contra a fonte.

#bibliography("referencias.bib", style: "apa", title: "Referências")


= Anexo A. Inventário das citações lidas

A tabela abaixo lista cada registro classificado, com os eixos da taxonomia v2.
Um traço na coluna de profundidade, postura ou exatidão indica registro presente
apenas na lista de referências, em que esses eixos não se aplicam. A coluna de
quartil traz traço quando o periódico citante não casou com o Scimago.

#show figure.where(kind: table): set block(breakable: true)

#figure(
  kind: table,
  supplement: [Tabela],
  caption: [Inventário completo das citações lidas, com identificador, veículo, quartil e os quatro eixos da taxonomia v2.],
  block(width: 100%)[
    #set text(size: 6.4pt)
    #set par(leading: 0.5em, justify: false)
    #table(
      columns: _cols-inventario,
      stroke: (x, y) => (top: if y == 1 { 0.4pt + sapians-muted-dark } else if y == 0 { 0.9pt + sapians-text-dark } else { 0pt }),
      fill: none,
      inset: (x: 1.4mm, y: 1.0mm),
      align: left,
      table.header(
        text(weight: "bold")[Id],
        text(weight: "bold")[Periódico],
        text(weight: "bold")[Quartil],
        text(weight: "bold")[Presença],
        text(weight: "bold")[Profundidade],
        text(weight: "bold")[Postura],
        text(weight: "bold")[Exatidão],
      ),
      ..D.inventario_classificados.map(r => (
        raw(r.id),
        cel((if r.veiculo_norm == "" { "—" } else { r.veiculo_norm })),
        cel(r.quartil),
        cel(r.presence),
        cel(r.depth),
        cel(r.stance),
        cel(r.accuracy),
      )).flatten(),
    )
    #_regua-grossa
    #v(1mm)
    #text(size: 6.6pt, fill: sapians-muted-dark)[Fonte: `reports/01-impacto/dados.json`, bloco `inventario_classificados`, gerado por `tools/audit_70_numbers.py` a partir de `data/classify.json`.]
  ],
) <tab-inventario>
