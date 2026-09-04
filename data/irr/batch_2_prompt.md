# Instruções para o segundo codificador — teste cego de confiabilidade

## 1. Seu papel

Você é o **segundo codificador independente** de uma auditoria da qualidade das citações
recebidas por dois artigos. O primeiro codificador já classificou os mesmos itens; você
não verá essa classificação, e ela não verá a sua até o cálculo da concordância. Regras:

- Codifique **só a partir do que está no item**: as passagens e o título do trabalho
  citante. Não procure o artigo citante na internet, não abra o PDF, não use o título
  para inferir veículo, ano ou autores. A identificação foi retirada de propósito.
- Não discuta itens com o primeiro codificador antes de entregar.
- Use este documento como único codebook. Se um item não couber em nenhuma regra,
  decida mesmo assim, registre `confidence = 1` e explique na `rationale`.
- Alguns itens aparecem duas vezes sob ids diferentes. Isso é intencional (sonda de
  consistência). Não procure os pares; codifique cada item como se fosse novo.
- Os dois artigos avaliados são sempre os mesmos (abaixo). A passagem cita um deles —
  o campo `paper` diz qual — por sobrenome e ano (`Bendinelli et al., 2016` ou
  `2020`, às vezes `2019`), por número (`[12]`) ou por sobrescrito.

## 2. O que há no pacote

`pack_blind.json` é uma lista de 4 lotes (28, 30, 28, 28 itens; 114 no total). Cada item:

| Campo | Conteúdo |
|---|---|
| `item_id` | identificador opaco (`IRR-xxxx`) — copie-o exatamente na saída |
| `paper` | `airline` ou `grains`: qual dos dois artigos é o citado |
| `citing_title` | título do trabalho citante |
| `passages` | trechos do texto citante onde o artigo aparece. Origem `auto`: janelas automáticas de ±700 caracteres em torno do sobrenome, cortadas no meio de frase e às vezes com sujeira de tabela ou cabeçalho — leia o miolo; origem `curated`: o trecho exato selecionado na leitura |
| `n_passages` | número de trechos |
| `passage_source` | `auto` ou `curated` |
| `citation_style` | `numeric` (o artigo é um número entre colchetes ou sobrescrito) ou `author_year` |

**Item sem passagem (`n_passages = 0`)**: o corpo completo do citante foi obtido e
verificado, e a busca pelo sobrenome não encontrou menção no corpo — o artigo consta só
na lista de referências. Codifique `presence = reference_list_only`; os demais eixos
ficam `null`/vazios e `stance = none`. Alguns itens trazem como passagem um trecho da
própria lista de referências (entradas bibliográficas em sequência): a decisão é a
mesma. Registre isso na `rationale`. Como nesses itens o eixo de presença é determinado
pela construção do pacote e não por julgamento independente, a concordância em
`presence` é reportada só como concordância bruta.

**Passagem em bloco numérico** (`[5,21,22,23]`, `[17] [18]`): o artigo é um dos números.
Isso é `in_text`; a profundidade costuma ser `drive_by` ou `brief_mention`, conforme a
afirmação seja genérica ou específica.

## Codebook v2 — taxonomia em eixos ortogonais

A versão 1 do codebook usava um único `role` de sete valores mais uma `flag`. A versão 2
separa o que ali estava misturado em três eixos independentes — **presença**,
**profundidade** e **exatidão** — e mantém **postura** (stance) e **reuso** como eixos
próprios. Cada eixo é julgado sozinho: uma citação pode ser profunda e errada, rasa e
exata, contrária e exata. Nunca deixe um eixo "puxar" o outro.

### Eixo 1 — PRESENCE: onde o artigo aparece no citante

| Valor | Significado |
|---|---|
| `in_text` | O artigo é mencionado no corpo do texto — inclusive dentro de um bloco de citações numéricas como `[5,21,22,23]` ou de um parêntese com várias fontes |
| `reference_list_only` | Consta na lista de referências, sem nenhuma menção no corpo. Exige corpo completo verificado (portão 3 de METHOD.md) |
| `not_cited` | Não aparece nem no corpo nem na lista de referências — aresta falsa do grafo de citações. Não ocorre neste pacote |

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
sendo `brief_mention` (nível 2) neste eixo e recebe o erro no eixo de exatidão. (No v1
esse caso era o `role` `wrongly_interpreted`, que misturava os dois eixos.)

### Eixo 3 — STANCE: postura do citante

`supporting` · `contradictory` · `none`

Regra deliberadamente liberal, como no original: qualquer contraponto conta como
`contradictory`, mesmo sem linguagem hostil e mesmo quando o citante também usa o
artigo como baseline. "Unlike X", "X não considera", "X é limitado a" — todos contam.
`supporting` é o citante que se apoia no artigo ou relata seu achado como válido;
`none` é a menção sem postura (bloco genérico, referência só na bibliografia).

### Eixo 4 — ACCURACY: o citante diz o que o artigo diz?

Só se aplica quando `presence = in_text`; caso contrário fica `null`. Compare o que a
passagem atribui ao artigo com o resumo e o registro de afirmações abaixo.

| Valor | Significado |
|---|---|
| `accurate` | O que é atribuído ao artigo corresponde ao que ele diz |
| `imprecise` | Leitura discutível, frouxa ou ampliada, mas não demonstravelmente falsa — um dado de outro país, uma generalização além do escopo, um achado lido numa direção que o artigo não afirma com clareza (no v1: flag `weak`) |
| `misrepresented` | O artigo é citado para algo que ele não diz — objeto, método ou achado errado (no v1: `wrongly_interpreted` / `misattribution`) |

**Sub-código DISTORTION** (Greenberg, 2009, *BMJ* 339:b2680), obrigatório quando
`accuracy != accurate` e `null` quando `accurate`:

| Valor | Significado |
|---|---|
| `dead_end` | O artigo é usado para sustentar uma afirmação sobre a qual ele não tem conteúdo relevante (política de concorrência nos Bálcãs; um dado sobre Gana) |
| `diversion` | O conteúdo do artigo é citado, mas com significado diferente do original ("investiga a estrutura de custo da companhia") |
| `transmutation` | Uma hipótese, conjectura ou limitação do artigo vira fato estabelecido na citação |
| `relayed_attribution` | O citante atribui ao artigo, como achado próprio, algo que o artigo apenas repassa de terceiros (afirmações marcadas REPASSADO no registro: "20–35% dos grãos perdidos" é Gustavsson et al., 2011) |

### Eixo 5 — REUSE: reuso efetivo (multi-rótulo)

`method_adoption` · `result_validated` · `dataset_reuse` · `benchmarking` · `work_extended`

Só marcado quando o citante **usa** o trabalho, não quando apenas o menciona. É o sinal
mais forte de impacto real. A régua é: **o citante mudaria de desenho se o artigo não
existisse?** Se a resposta é não, a lista fica vazia.

| Tag | Quando marcar |
|---|---|
| `method_adoption` | Adota do artigo um método, especificação, variável, instrumento, teste ou definição operacional como base do próprio desenho |
| `result_validated` | Usa o achado do artigo para validar ou confrontar o próprio resultado ("encontramos o mesmo que…") |
| `dataset_reuse` | Usa a mesma fonte de dados por causa do artigo |
| `benchmarking` | Compara quantitativamente os próprios números com os do artigo |
| `work_extended` | Declara estender o modelo, a pergunta ou o desenho do artigo |

### Eixos que NÃO entram no teste cego

`relation` (independent / coauthor / self), `record_flags` (duplicate_publication) e
`highlight` (none / good / best) exigem metadados de autoria ou são editoriais. Não os
codifique.

### CLAIM_IDS: que afirmações do artigo a passagem invoca

Escolha no registro de afirmações (abaixo) os ids do que a passagem atribui ao artigo —
o que o citante diz que o artigo diz, independentemente de estar certo. Lista vazia
quando `presence != in_text` ou quando a menção é genérica demais para apontar uma
afirmação. Uma afirmação REPASSADO escolhida junto com `accuracy = accurate` significa
que o citante atribuiu corretamente a terceiros; escolhida com `relayed_attribution`
significa que atribuiu ao artigo o que era de terceiros.

## Codebook: os casos de fronteira (METHOD.md, literal)

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

### Tradução dos termos v1 usados nos casos acima

| Termo no caso de fronteira (v1) | Codificação v2 |
|---|---|
| `contradictory` / `supporting` (stance) | `stance = contradictory` / `stance = supporting` — inalterado |
| `wrongly_interpreted` | `presence = in_text`, `depth` pelo que o citante faz (em geral `brief_mention`), `accuracy = misrepresented` + `distortion` |
| `weak` | `accuracy = imprecise` + `distortion` |
| `method_adoption` | `reuse` contém `method_adoption` (e `depth >= supporting`, porque sustenta o desenho) |
| `brief_mention`, `drive_by` | `depth = brief_mention` (2), `depth = drive_by` (1) |
| `bibliography_only` | `presence = reference_list_only`, `depth = null`, `accuracy = null` |
| `evidencia_insuficiente` | não ocorre no pacote — todo item tem corpo verificado ou passagem literal |
| autocitação / coautor | não codificado no teste cego (eixo `relation`) |

## 3. Ordem de decisão

Decida os eixos nesta ordem, um de cada vez, sem voltar atrás para "acertar" o conjunto:

1. **presence** — há menção no corpo? (`in_text` / `reference_list_only`). Se não há,
   pare aqui: `depth = null`, `accuracy = null`, `distortion = null`, `reuse = []`,
   `claim_ids = []`, `stance = none`.
2. **depth** — o que o citante faz com o artigo (1 a 5), ignorando se está certo.
3. **stance** — postura, pela regra liberal.
4. **accuracy** — compare o que é atribuído ao artigo com o resumo e o registro de
   afirmações; se `imprecise` ou `misrepresented`, escolha o **distortion**.
5. **reuse** — aplique a régua: o citante mudaria de desenho se o artigo não existisse?
6. **claim_ids** — ids do registro de afirmações que a passagem invoca.

Depois, `confidence` (1 = chute informado, 2 = razoável, 3 = seguro) e `rationale`
(até 30 palavras, em português, citando as palavras da passagem que decidiram).

## 4. Os dois artigos avaliados

### `airline` — Airline delays, congestion internalization and non-price spillover effects of low cost carrier entry

*Bendinelli et al., Transportation Research Part A: Policy and Practice (2016)*

**Resumo (abstract original):** This paper develops an econometric model of flight delays to investigate the influence of competition and dominance on the incentives of carriers to maintain on-time performance. We consider both the route and the airport levels to inspect the local and global effects of competition, with a unifying framework to test the hypotheses of 1. airport congestion internalization and 2. the market competition-quality relationship in a single econometric model. In particular, we examine the impacts of the entry of low cost carriers (LCC) on the flight delays of incumbent full service carriers in the Brazilian airline industry. The main results indicate a highly significant effect of airport congestion self-internalization in parallel with route-level quality competition. Additionally, the potential competition caused by LCC presence provokes a global effect that suggests the existence of non-price spillovers of the LCC entry to non-entered routes.

### `grains` — What are the main factors that determine post-harvest losses of grains?

*Bendinelli et al., Sustainable Production and Consumption (2019)*

**Resumo (abstract original):** Reducing post-harvest losses (PHL) permits the improvement of food security and food safety, reduction of unnecessary resource use and increase of food supply chain actors’ profits. Most published studies have addressed the problem qualitatively, mainly due to difficulty obtaining necessary data. This paper seeks to understand how macroeconomic conditions influence PHL of grains (rice, maize, soybeans and wheat), which are the main source of food for humans and animals, through the construction of an econometric model using global level panel data from publicly available databases. Results suggest that increasing production to feed the increasing population often involves a difficult trade-off. Some countries seeking on-farm production gains lack post-harvest infrastructure, especially in food storage and food marketing, which contribute to a sharp increase in the PHL level. There is also evidence that economic development non-linearly reduces grains’ PHL in all dimensions.

## 5. Registro de afirmações (claims.json)

Cada afirmação tem um id. `AIR-*` pertence ao artigo `airline`, `GR-*` ao artigo
`grains`. As marcadas REPASSADO são o que o próprio artigo atribui a terceiros — se o
citante as atribui ao artigo como achado próprio, é `relayed_attribution`.

### Artigo `airline`

- **AIR-M01** — Arcabouço unificador: testa em um ÚNICO modelo econométrico a hipótese de internalização do congestionamento aeroportuário e a de relação competição-qualidade no mercado, dispensando a hipótese de simetria de rotas da literatura de internalização.
- **AIR-M02** — O modelo não impõe a hipótese de simetria de rotas e admite internalização de congestionamento EM PARALELO à gestão de qualidade de serviço, o que permite pôr concentração de rota e de cidade na mesma equação.
- **AIR-M03** — A endogeneidade do HHI de rota e do HHI máximo das cidades-extremo é tratada por variáveis instrumentais estimadas por GMM eficiente factível em dois passos (2SGMM), com erros-padrão robustos a heterocedasticidade e autocorrelação (Newey-West, kernel de Bartlett).
- **AIR-M04** — Identificação por instrumentos do tipo Hausman: a concentração de outras rotas instrumenta a concentração de uma dada rota, descartando cidades próximas segundo três limiares (150, 300 e 500 km); validade e relevância checadas por Hansen J e Kleibergen-Paap.
- **AIR-M05** — Duas famílias de regressandos: ODDS (log-odds da proporção de voos atrasados = PREVALÊNCIA) e MINS (diferença média em minutos entre chegada programada e efetiva = DURAÇÃO), além de versões truncadas (MINS>15, MINS>30) e de partida (ODDSD, MINSD).
- **AIR-D01** — Painel de 209 rotas brasileiras de janeiro de 2002 a dezembro de 2013, agregado ao nível rota-mês, restrito a rotas entre capitais estaduais e Brasília; a rota é definida como par-de-cidades doméstico e direcional.
- **AIR-D02** — Fonte primária: o relatório Voo Regular Ativo (VRA) da ANAC, base online com dados no nível do voo — empresa, par-de-aeroportos, número do voo e horários programados e efetivos — desde 2000, com código de justificativa de cada atraso.
- **AIR-D03** — A base bruta tem 10 milhões de voos do VRA. As incumbentes full-service analisadas são Tam, Varig, Transbrasil e Vasp; as low cost carriers da amostra são Gol e Azul.
- **AIR-D04** — Aplicação a uma economia emergente: o Brasil é caso em que os atrasos são longamente debatidos e em que pedágios de congestionamento nunca foram implementados; a aviação comercial foi plenamente desregulamentada em 2001.
- **AIR-D05** — Descritivo (Tabela 1): a proporção de voos atrasados caiu 33,5% de 2006-2010 para 2011-2013 e 5,3% frente a 2002-2005; no mesmo confronto o hubbing caiu 11,0%, o HHI de cidade subiu 4,3% e o de par-de-cidades caiu 0,4%.
- **AIR-DEF01** — Atraso é medido pelo padrão de 15 minutos do BTS/DOT norte-americano — e NÃO pelo padrão brasileiro de 30 minutos da ANAC — computado sobre a diferença entre a chegada programada e a efetiva.
- **AIR-DEF02** — 'Hora congestionada' é a hora cheia em que o número de operações (pousos mais decolagens) supera a capacidade oficial declarada do aeroporto, conforme estudo de capacidade encomendado pelo governo brasileiro.
- **AIR-F01** — Achado 1: a concentração no nível do AEROPORTO/CIDADE REDUZ os atrasos. O coeficiente de HHI max endpoint cities é negativo e significante em todas as especificações de ODDS e MINS — evidência de internalização do congestionamento (H1).
- **AIR-F02** — Achado 2: a concentração no nível da ROTA/MERCADO AUMENTA os atrasos. O coeficiente de HHI city-pair é positivo e significante ao menos a 5% em todos os casos — evidência da relação competição-qualidade (H2).
- **AIR-F03** — Achado 3: a presença de LCC nas CIDADES-EXTREMO reduz a PREVALÊNCIA dos atrasos (coeficiente negativo e significante em ODDS) mas NÃO a sua DURAÇÃO (não significante em MINS) — internalização extra induzida pela entrada.
- **AIR-F04** — Achado 4: NÃO há efeito robusto da presença de LCC na PRÓPRIA ROTA — as respostas locais à entrada são não significantes ou significantes só a 10%, sem apoio à hipótese de corte de custos/preços de Prince e Simon (2015).
- **AIR-F05** — Achado 5 (título do artigo): spillover não-tarifário — a entrada de LCC em uma rota gera competição potencial nas demais rotas da cidade, com efeito positivo sobre a pontualidade das rotas NÃO entradas.
- **AIR-F06** — Omitir o HHI de cidade enviesa negativamente a estimativa do HHI de rota (correlação de 0,48 entre as duas): qualquer subespecificação das variáveis de concentração pode gerar estimação inconsistente e falso negativo.
- **AIR-F07** — Ignorar a endogeneidade inverte os sinais: sob OLS os sinais dos HHI mudam, o que sustenta a recomendação de estimação por variáveis instrumentais. Resultados estáveis sob LIML e com atrasos de partida.
- **AIR-I01** — Interpretação dos autores: há um aparente paradoxo — as incumbentes auto-internalizam congestionamento quando sua dominância aeroportuária aumenta e TAMBÉM mantêm alguma internalização quando essa dominância é desafiada pela entrada de uma LCC.
- **AIR-I02** — Mecanismo CONJECTURADO, não testado: depeaking, com voos realocados para horários fora de pico em que a LCC é mais atrativa a passageiros de lazer, permitiria manter a internalização mesmo com queda da concentração aeroportuária.
- **AIR-P01** — Implicação de política: enquanto a competição por qualidade é observada localmente no mercado, a emergência e o crescimento das LCCs podem ser um fator adicional de melhoria da pontualidade do setor aéreo.
- **AIR-L01** — Limitação: os atrasos são medidos estritamente contra o horário programado, sem controlar o padding estratégico de malha; o recorte par-de-cidades também impede observar realocações estratégicas entre pares de aeroportos adjacentes.
- **AIR-R01** — REPASSADO de Molnar (2013): a internalização depende dos incentivos estratégicos das empresas ao equilibrar benefícios de conexões e horários preferidos com custos de congestionamento, havendo evidência de que a DISSUASÃO ESTRATÉGICA DE ENTRADA PREVALECE NOS HUBS.
- **AIR-R02** — REPASSADO de Daniel (1995) e Brueckner (2002): a companhia dominante de um aeroporto teria incentivos mais fortes que as menores para enfrentar o congestionamento e internalizaria naturalmente os custos dos atrasos que ela própria impõe.
- **AIR-R03** — REPASSADO de relatório de 2014 do Office of Inspector General da FAA: a ausência de competição em muitas rotas pode ser fonte de aumento das taxas de atrasos e cancelamentos de voos.
- **AIR-R04** — REPASSADO de Rupp e Sayanak (2008) e Castillo-Manzano e Lopez-Valpuesta (2014): as LCCs apresentam melhor desempenho de pontualidade do que as full-service carriers. Não é resultado próprio deste artigo.
- **AIR-R05** — REPASSADO: Prince e Simon (2015) acham que a entrada de LCC AUMENTA os atrasos das incumbentes via corte de custos sob competição de preços; Bubalo e Gaggero (2015) acham o contrário. A literatura carece de consenso.
- **AIR-R06** — REPASSADO de Daniel e Harback (2008), Rupp (2009) e, em certa medida, Bilotkach e Lakew (2014): há evidência de AUSÊNCIA de auto-internalização, o que sugeriria papel para a tarifação de congestionamento.
- **AIR-R07** — REPASSADO de Brueckner, Lee e Singer (2014): pares de CIDADES, e não pares de aeroportos, são a definição de mercado apropriada em muitas análises de transporte aéreo — justificativa do recorte adotado.

### Artigo `grains`

- **GR-DEF01** — PHL são definidas como a redução NÃO INTENCIONAL da quantidade de alimento produzido para consumo humano em todas as etapas da cadeia de suprimentos, independentemente de causa ou destino, EXCLUÍDAS as etapas de varejo e consumo final.
- **GR-DEF02** — REPASSADO da literatura: distingue-se food loss, que ocorre nas etapas iniciais da cadeia, de food waste, que ocorre no varejo ou depois de chegar ao consumidor e está ligado a comportamento — ato intencional de uma pessoa.
- **GR-DEF03** — A variável dependente %PHL segue a fórmula de Gustavsson et al. (2013): perdas divididas pela oferta, sendo oferta = produção + importação + variação de estoques. A fórmula NÃO é dos autores.
- **GR-D01** — Painel de 82 países entre 2000 e 2011, selecionados por deterem ao menos 1% da oferta doméstica de grãos de sua região geográfica; dados de oferta doméstica das Food Balance Sheets da FAO (FAOSTAT).
- **GR-D02** — Os grãos analisados são arroz, milho, soja e trigo — principal fonte de alimento para humanos e animais; dados independentes vêm de FAOSTAT, Banco Mundial e UNESCO.
- **GR-D03** — ATENÇÃO: os 82 países são a base bruta. Após excluir dados faltantes e outliers (acima de 3 desvios-padrão), o painel desbalanceado efetivamente estimado tem 546 observações/69 países, e 534 observações/68 países nos modelos-base.
- **GR-M01** — Especificação log-log (Eq. 2) da variável dependente e das explicativas, adotada para capturar as não-linearidades do problema e ler os parâmetros estimados diretamente como elasticidades, evitando uma etapa extra de estimação.
- **GR-M02** — Estimação por mínimos quadrados generalizados factíveis (FGLS) em painel, com efeitos fixos de grupo e de tempo e estatísticas robustas a heterocedasticidade e correlação serial, com parâmetro de correlação único por painel.
- **GR-M03** — Diagnósticos: raiz unitária tipo Fisher (Choi, 2001) com médias transversais subtraídas, Wald modificado para heterocedasticidade entre grupos e teste de Wooldridge para autocorrelação de 1ª ordem, corrigida por Newey-West.
- **GR-M04** — Tratamento da endogeneidade: ln_supply é excluído das especificações com %PHL e o PIB per capita é convertido em quatro dummies de faixa de renda, o que permite manter ln_price e ln_trade no modelo.
- **GR-M05** — Novidade declarada: é o PRIMEIRO trabalho a estimar determinantes de PHL com painel de dados mundial e correções para reduzir viés de parâmetros; os únicos dois antecedentes globais (KC et al., 2016; Rosegrant et al., 2015) teriam viés maior.
- **GR-F01** — Achado principal: o PIB per capita é o determinante de MAIOR impacto sobre as PHL nos modelos-base (colunas 4 e 6 da Tabela 3), reduzindo-as intensamente.
- **GR-F02** — A relação entre desenvolvimento econômico e PHL é NÃO-LINEAR e compatível com uma curva de Kuznets: ln_income entra positivo (2,017 e 2,899) e ln_square_income negativo (-0,135 e -0,184), ambos a 1%.
- **GR-F03** — Lacunas por faixa de renda, com high_income como grupo-base (Tabela 3, col. 6): low_income +0,731; low_middle_income +0,706; upper_middle_income +0,534 em log de %PHL, todos significantes a 1%.
- **GR-F04** — A urbanização REDUZ as PHL com efeito moderado: países pouco urbanizados apresentam 29,9% mais PHL e os de urbanização média 23,6% mais PHL do que os altamente urbanizados.
- **GR-F05** — A abertura ao comércio internacional REDUZ as PHL (ln_trade -0,204 a -0,216): países com baixo nível de comércio global têm 23,9% mais PHL do que os de alto nível, por padronização de operações e embalagens.
- **GR-F06** — A crise de 2008-2011 AUMENTOU as PHL (dummy crisis positiva e significante a 1% nos modelos-base, +0,138 e +0,292), por afetar o poder de compra do consumidor e suspender investimentos, por exemplo em armazenagem fora da fazenda.
- **GR-F07** — Efeitos de BAIXA magnitude para tamanho do setor de alimentos, volatilidade do preço de alimentos (positiva sobre PHL, +0,059 a +0,087) e densidade ferroviária (negativa); a densidade rodoviária NÃO é significante nos modelos-base.
- **GR-F08** — O excedente alimentar (ln_supply) AUMENTA fortemente as PHL (coeficientes de 0,95 a 1,56): onde a oferta supera a demanda há baixo incentivo econômico para evitar perdas e pode faltar infraestrutura para lidar com o excedente.
- **GR-F09** — Achado-síntese: há um TRADE-OFF difícil entre ampliar a oferta de alimentos e o nível de PHL — sem infraestrutura pós-colheita adequada, sobretudo armazenagem e comercialização, o esforço para aumentar a oferta eleva as PHL.
- **GR-F10** — Robustez: trocar a dependente de %PHL para toneladas inverte os sinais de rodovia, ferrovia e urbanização — esperado, pois a variável não é ponderada; ponderando pela população, só setor de alimentos e ferrovia trocam de sinal.
- **GR-P01** — Política: esforços para aumentar a produção de alimentos não podem se restringir à produção na fazenda, pois geram excedente e PHL muito maiores; devem ser complementados por investimentos em infraestrutura pós-colheita, em especial armazenagem e comercialização.
- **GR-P02** — Política: a construção de infraestrutura como instalações de armazenagem em países em desenvolvimento, somada à transferência de conhecimento e tecnologias de países industrializados, tem levado à redução das PHL.
- **GR-R01** — REPASSADO de Gustavsson et al. (2011): estima-se que as PHL de grãos variem de 20% a 35% entre as diferentes regiões geográficas do mundo. NÃO é estimativa dos autores deste artigo.
- **GR-R02** — REPASSADO de Gustavsson et al. (2011): quase um terço da produção global de alimentos, em peso, é perdido. NÃO é estimativa dos autores deste artigo.
- **GR-R03** — REPASSADO de Kummu et al. (2012): cerca de um quarto da água, terra agricultável e fertilizante consumidos para produzir alimentos é desperdiçado.
- **GR-R04** — REPASSADO de Hodges et al. (2011): espera-se que a população mundial alcance 9 bilhões de pessoas até 2050, o que exigirá 70% mais alimentos.
- **GR-R05** — REPASSADO de Cardoen et al. (2015a) e Gustavsson et al. (2011): em países em desenvolvimento e em transição a perda nas etapas iniciais da cadeia supera o desperdício; em países desenvolvidos e industrializados ocorre o inverso.
- **GR-R06** — REPASSADO: a Tabela 1, que caracteriza as PHL por estágio de desenvolvimento tecnológico/econômico do país, é ADAPTADA de Parfitt et al. (2010) e Hodges et al. (2011), não construída pelos autores.
- **GR-R07** — REPASSADO: dados sobre PHL são escassos, antigos, majoritariamente pouco confiáveis e frequentemente não comparáveis — justificativa dos autores para recorrer a bases secundárias globais.
- **GR-L01** — Limitação: não existe variável de armazenagem de alimentos publicamente disponível em painel global; densidade de rodovias e de ferrovias foram usadas como PROXY da infraestrutura do país.
- **GR-L02** — Limitação de escopo: como PHL aqui NÃO inclui food waste (varejo e consumidor), variáveis explicativas de comportamento do consumidor não entraram no modelo, embora devessem entrar num modelo de desperdício.
- **GR-L03** — Limitação de generalização: culturas perecíveis como frutas e hortaliças têm requisitos de cadeia distintos dos grãos, de modo que as conclusões deste trabalho não podem ser extrapoladas diretamente para esse grupo.

## 6. Contrato de saída (estrito)

Entregue **um único arquivo JSON**, `irr_c2_<seu_nome>.json`, um objeto cujas chaves são
os `item_id` de todos os lotes e cujos valores seguem exatamente este formato:

```json
{
 "IRR-a1b2": {
  "presence": "in_text",
  "depth": "brief_mention",
  "stance": "supporting",
  "accuracy": "imprecise",
  "distortion": "dead_end",
  "reuse": [],
  "claim_ids": ["GR-R01"],
  "confidence": 2,
  "rationale": "Atribui ao artigo um dado sobre Gana que ele não contém."
 }
}
```

Regras de validação (o script de estatística rejeita o que não cumprir):

| Campo | Valores |
|---|---|
| `presence` | `in_text` · `reference_list_only` · `not_cited` |
| `depth` | `drive_by` · `brief_mention` · `real_mention` · `supporting` · `foundational`; **`null` se `presence != in_text`** |
| `stance` | `supporting` · `contradictory` · `none` |
| `accuracy` | `accurate` · `imprecise` · `misrepresented`; **`null` se `presence != in_text`** |
| `distortion` | `dead_end` · `diversion` · `transmutation` · `relayed_attribution`; **`null` se `accuracy` é `accurate` ou `null`** |
| `reuse` | lista (pode ser vazia) de `method_adoption` · `result_validated` · `dataset_reuse` · `benchmarking` · `work_extended`; vazia se `presence != in_text` |
| `claim_ids` | lista (pode ser vazia) de ids do registro; vazia se `presence != in_text` |
| `confidence` | inteiro 1, 2 ou 3 |
| `rationale` | texto de até 30 palavras |

Todos os `item_id` do pacote devem aparecer. Não acrescente campos. Não altere os ids.


---

# LOTE 2 DE 4 — 30 ITENS

Codifique CADA item abaixo. Responda com UM ÚNICO bloco JSON (lista), um objeto por item, seguindo estritamente o contrato de saída acima. Não omita nenhum item_id. Não inclua comentários fora do JSON.

```json
[
 {
  "citation_style": "author_year",
  "citing_title": "Pest and Disease Related Post-Harvest Losses in Rice: A Review",
  "item_id": "IRR-b097",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "auto",
  "passages": [
   "s significant financial hardship for farmers and supply chain participants globally. In India, post-harvest loss (PHL) in rice is a serious problem that affects farmer earnings, food security and overall economic effectiveness. Key words: Disease, Pest, Post harvest losses, Rice. In rice, post-harvest losses (PHL) are the quantitative and qualitative decreases in rice grain that occur in between the harvest and human consumption (Qu et al., 2021). This encompasses any reduction in the quantity of consumable rice grain that is the result of factors that impede its utilization by humans, such as a decrease in nutritional value, a decrease in its marketability, or a decrease in its edibility (Bendinelli et al., 2020 and Mahendran et al., 2024). PHL should be distinguished from intentional reductions, such as the removal of bran or husk during milling, which are essential processing stages (Muller et al., 2022). Globally, post-harvest losses in rice can range from 10% to 40% of total production, depending on the region and the techniques employed. In developing countries, losses are generally higher due to traditional methods and less advanced infrastructure. The post-harvest losses for grains, including rice, are typically estimated to be between 10% and 20% at the pre-processing stage (Nath et al., 2024). The quantitative harvest and post-harvest losses for cereals, which encompass paddy/"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Are on-time performance statistics worthless? An empirical study of the flight scheduling strategies of Brazilian airlines",
  "item_id": "IRR-ea18",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "motivated by the previous literature—Greenfield (2014) and Bendinelli, Bettini, and Oliveira (2016)—we assume that the unobserved components of the flight delays on city-pair market k at time t are correlated with the status of competition in that market. As a result, we must treat the market concentration and LCC share of flights—namely, HHI and LCCS—as endogenous."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "An Analysis of Flight Delays at Taoyuan Airport",
  "item_id": "IRR-4fd3",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "auto",
  "passages": [
   "ork carriers and low cost carriers in Turkish Airline market. Procedia Soc. Behav. Sci. 207 , 642–651 (2015) Article Google Scholar M. Ball, C. Barnhart, M. Dresner, M. Hansen, K. Neels, A. Odoni, et al., Total Delay Impact Study: A Comprehensive Assessment of the Costs and Impacts of Flight Delay in the United States (Institute of Transportation Studies, University of California, Berkeley, Berkeley, 2010) Google Scholar P. Baumgarten, R. Malina, A. Lange, The impact of hubbing concentration on flight delays within airline networks: An empirical analysis of the US domestic market. Transp. Res. Part E Logistics Transp. Rev. 66 , 103–114 (2014) Article Google Scholar W.E. Bendinelli, H.F. Bettini, A.V. Oliveira, Airline delays, congestion internalization and non-price spillover effects of low cost carrier entry. Transp. Res. A Policy Pract. 85 , 39–52 (2016) Article Google Scholar P. Berster, M.C. Gelhausen, D. Wilken, Is increasing aircraft size common practice of airlines at congested airports? J. Air Transp. Manag. 46 , 40–48 (2015) Article Google Scholar C.F. Bien, Y.F. Low, Taoyuan airport vows to improve on-time performance. Central News Agency (2016, January 14) . Retrieved from http://www.taiwannews.com.tw/en/news/2868374 S. Borenstein, J. Netz, Why do all the flights leave at 8 am?: Competition and departure-time differentiation in airline ma"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Gendering post-harvest loss research: responsibilities of women and men to manage maize after harvest in southwestern Ethiopia",
  "item_id": "IRR-8c05",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "ther post-harvest loss reduction or in gender equality. However, potentially more problematic is the scenario in which progress on post-harvest loss reduction is achieved but that “food loss reduction does not address or even exacerbates gender inequalities” (2018, p. 19). Despite this increased awareness among development actors, most scientific research on post-harvest losses does not consider gender. In a literature review of fruit and vegetable post-harvest loss research by Gardas et al. (2018), none of the studies included brought up the issue of gender. A few journal articles on PHL that do bring up the term ‘gender’, do not actually go beyond sex disaggregation of household headship (Bendinelli et al., 2020; Chegere, 2018) For example, Chegere (2018), only separates the data by female and male household heads in a study about the economic trade-offs of adopting measures recommended to reduce post-harvest losses with no inclusion of other post-harvest management roles conducted by women and men. These studies do not make an effort to untangle any of the other gendered dynamics, for example at the household level, that relate to post-harvest management. 3 \u0007Research context and methods Jimma Zone, one of twenty in Oromia Regional State, was selected from the southwestern part of Ethiopia. Over 90% of the population of Jimma Zone is Oromo. Gender differences among the Jimma Oromo are"
  ]
 },
 {
  "citation_style": null,
  "citing_title": "Analysis of the Factors Influencing the Stability of Stored Grains: Implications for Agricultural Sustainability and Food Security",
  "item_id": "IRR-6cdf",
  "n_passages": 0,
  "paper": "grains",
  "passage_source": "curated",
  "passages": []
 },
 {
  "citation_style": "author_year",
  "citing_title": "Determinants of flight delays at East Asian airports from an airport, route and network perspective",
  "item_id": "IRR-7860",
  "n_passages": 2,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "previous studies explored the hypotheses of congestion internalization and hubness effect from an airport perspective and competition and quality from a route perspective (Bendinelli et al., 2016; Brueckner, 2002; Greenfield, 2014; Mayer and Sinai, 2003).",
   "Only few studies are based on intra-European flights (Santos and Robin, 2010) and domestic flights in Brazil (Bendinelli et al., 2016)."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Lipoxygenases (LOXs): Will turning off this genetic switch help safeguard the flavor and nutritional quality of stored lipid-rich staple foods?",
  "item_id": "IRR-73f8",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "Bendinelli et al. (2020) reported that estimates of post-harvest losses for food grains range from 25 % to 30 % of the total supply, which includes production, imports, and stock variations."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Food Waste: Farms, distributors, retailers, and households",
  "item_id": "IRR-a299",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "whereas higher-income countries typically face few systematic challenges in limiting waste for storable commodities (e.g., grains, see Bendinelli, Su, Péra, & Caixeta Filho, 2020), lower-income countries often face gaps in the quantity and quality of farm-level storage and infrastructure."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "The uneven geography of US air traffic delays: Quantifying the impact of connecting passengers on delay propagation",
  "item_id": "IRR-05b4",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "Several studies argue that if dominant carriers internalise such costs, congestion pricing for Full Service Network Carriers should be adapted to account for internalised costs (Bendinelli et al., 2016; Brueckner and Van Dender, 2008; Miranda and Oliveira, 2018; Pels and Verhoef, 2004; Rupp, 2009)."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Airport airside congestion pricing considering price discrimination between aircraft type under a Stackelberg game",
  "item_id": "IRR-648f",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "auto",
  "passages": [
   "rport congestion and road congestion operate diﬀerently. Road users are atomistic while airlines are not. In other words, while road users have no incentive to take account of the congestion they impose on other drivers (Teodorovic et al. (2008)), an airline that schedules an extra ﬂight at a crowded airport congests other airlines but also imposes congestion costs on the other ﬂights it operates. Airport congestion tolls apparently need not be as large as the atomistic tolls implied by road-pricing theory because some congestion is then internalized. Pels and Verhoef (2004), Triantis et al. (2011) and Basso and Zhang (2007) provided further elaboration on the internalization of congestion. Bendinelli, Bettini, and Oliveira CONTACT Baocheng Zhang bczhang@cauc.edu.cn College of Air Traﬃc Management, Civil Aviation University of China, Tianjin 300300, People’s Republic of China; Lab of Air Traﬃc Management and Optimization, Civil Aviation University of China, Tianjin 300300, People’s Republic of China © 2019 Informa UK Limited, trading as Taylor & Francis Group 2 B. ZHANG ET AL. (2016), Czerny and Zhang (2014b) and Zhang and Czerny (2012) have reviewed recent work about airport congestion pricing. Price discrimination between diﬀerent types of passenger has received considerable attention (Czerny and Zhang 2015, 2011, 2014a; Koopmans and Lieshout 2016). However, little eﬀort has been s"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Ryzyko biznesowe w pasażerskim lotnictwie cywilnym – w poszukiwaniu źródeł niestabilności sektora",
  "item_id": "IRR-ed73",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "auto",
  "passages": [
   "wewnętrznych (z perspektywy przedsiębiorstw) można przede wszystkim wymienić operacyjne i finansowe. Natomiast z perspektywy sektora również konkurencja między podmiotami oraz konieczność współpracy mogą być źródłem wystąpienia ryzyka czy stanów niepewności co do dalszego rozwoju sytuacji w sektorze. Przykładami zdarzeń, które mogą się zrealizować w obszarze operacyjnym, są np. opóźnienia wynikające z przyczyn technicznych lub czynników pogodowych [Borsky, Unterberger, 2019], strajki, których skutki mogą być odczuwane nie tylko przez podmioty, w których występują, np. strajk kontrolerów ruchu lotniczego będzie mieć również konsekwencje dla działalności operacyjnej linii i portów lotniczych [Bendinelli, Bettini, Oliveira, 2016]. Większość czynników ryzyka operacyjnego jest stosunkowo niewielkim zagrożeniem z perspektywy całego sektora czy też w ujęciu długoterminowym ze względu na ich zwykle lokalny (odnoszący się do danego rynku lub nawet podmiotu) i ograniczony w czasie charakter, a także wypracowane na przestrzeni wielu lat działalności sposoby zarządzania nimi i ich mitygacji, na przykład poprzez odpowiednie planowanie siatki lotów [Şimşek, Aktürk, 2022]. Ryzyko finansowe związane jest nie tylko z działalnością finansową przedsiębiorstw funkcjonujących na rynku lotniczym, polegającą na przykład na wykorzystywaniu instrumentów finansowych do zabezpieczenia przed wahaniami cen paliwa lo"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Low-Cost Carriers and Airports: A Complex Relationship",
  "item_id": "IRR-74f7",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "auto",
  "passages": [
   "ns such as small islands can count on small catchment areas, but travelers have no real alternatives; neither inter-modal nor intra-modal. In this case, the limitedness of the market may leave space for only a few and monopolistic routes, typically toward the hub or the main base of the operating carrier. This situation may differ during holiday periods, when additional supplies provide services to tourists (by either charter or seasonal LCCs). Secondary airports, totally or partially competing with major airports, lay on the other side of the range of the market structure spectrum. They may have a marginal role unless some conditions appear, such as congestion problems at the main airport (Bendinelli, Bettini, & Oliveira, 2016) or if they allow airlines to serve the captive market without bearing the higher costs of primary airports (as Rome Ciampino/Fiumicino, Girona/Barcelona El Prat, London Luton or Stansted/Heathrow). Many air markets have expanded toward secondary airports to search for extra capacity, given congestion and delay problems that affect major airports all over the world, particularly in Europe, where increasing traffic and lack of both airport development/expansion and strong regulatory policies have worsened the problem (Madas & Zografos, 2008). Even more frequently, LCCs have used secondary airports to serve the otherwise impenetrable markets of former flag carriers,"
  ]
 },
 {
  "citation_style": "numeric",
  "citing_title": "Modeling and Control of an Indirect Solar Dryer in Forced Convection Mode Using System Identification and Model Predictive Control",
  "item_id": "IRR-d82e",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "auto",
  "passages": [
   "mplementation process HUMAN AND ANIMAL RIGHTS 6. CONCLUSION In conclusion, the proposed system successfully demonstrated the superior efficiency of an indirect solar dryer with forced convection mode, substantiated by compelling numerical results. The comparative assessment of three No violation of Human and Animal Rights is involved. FUNDING No funding is involved in this work. Rafiq et al.: Modeling and Control of an Indirect Solar Dryer in Forced Convection Mode Using System Identification and Model Predictive Control 827 DATA AVAILABILITY STATEMENT Data sharing not applicable to this article as no datasets were generated or analyzed during the current study. REFERENCES 0[1] W. E. Bendinelli, C. T. Su, T. G. P�era, and J. V. Caixeta Filho, “What are the main factors that determine post-harvest losses of grains,” Sustain. Prod. Consump., vol. 21, pp. 228–238, 2020. DOI: 10.1016/j.spc.2019.09.002. 0[2] G. V. Barbosa-C�anovas and P. Juliano, “Desorption phenomena in food dehydration processes,” in Water Activity Foods: fundamentals Applications. Ames, IA: Blackwell Publishing, 2020, pp. 425–452. 0[3] N. A. Safri et al., “Current status of solar-assisted greenhouse drying systems for drying industry (food materials and agricultural crops),” Trends Food Sci. Technol., vol. 114, pp. 633–657, 2021. DOI: 10.1016/j.tifs.2021.05.035. 0[4] V. K. Chauhan, S. K. Shukla, J. V. Tirkey, and P."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Causes and Mitigation Strategies of Food Loss and Waste: A Systematic Literature Review and Framework Development",
  "item_id": "IRR-4cc0",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "Food loss and waste (FLW) sums one-third of the total food produced globally for human consumption, about 1.3 billion tons of food (Priefer et al., 2016; Bendinelli et al., 2020)."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Modelo de identificação do impacto futuro de chuvas extremas nos atrasos/cancelamentos de voos",
  "item_id": "IRR-cc5f",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "exas e difı́ceis de serem mensuradas e gerenciadas, como eventos de situaçõ es meteoroló gicas extremas. Entre esses eventos, ı́ndices pluviomé tricos oscilantes podem ser considerados como de alto impacto nas operaçõ es de transporte aé reo. Estudos sobre eventos meteoroló gicos impactantes na aviaçã o, como incidê ncias de tempestades formadoras de rajadas de vento, podem ser identi icados em Metchko e Monteiro (2014), bem como estudos sobre ocorrê ncia de cancelamentos de voos devido à chuva extrema, como em Koetse e Rietveld (2009). Alé m desses, há també m estudos que buscam mensurar os impactos dos atrasos dos voos nos custos e na dinâ mica do transporte aé reo, como em Bendinelli, Bettini e Oliveira (2016), que consideram em suas aná lises, entre outras, variá veis relacionadas à proporçã o de atrasos de voos devido ao mau tempo. Já em Santos e Robin (2010), em que se analisam as principais causas para os atrasos de voos em aeroportos europeus, os autores demonstram que a concentraçã o de mercado em determinados aeroportos e companhias aé reas estã o entre as principais causas para os atrasos. Sendo assim, nota-se que tais estudos nã o consideram as situaçõ es climá ticas em acontecimento, mais incisivamente o clima futuro e como esse provocará alteraçõ es nas operaçõ es dos aeroportos. Trata-se, portanto, de uma lista de estudos que analisam o passado"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Nearly half of the world is suitable for diversified farming for sustainable intensification",
  "item_id": "IRR-8576",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "47. Li, S. & Kallas, Z. Meta-analysis of consumers’ willingness to pay for sustainable food products. Appetite 163, 105239 (2021). 48. Kumar, A. et al. Adoption and diffusion of improved technologies and production practices in agriculture: insights from a donor-led intervention in Nepal. Land Use Policy 95, 104621 (2020). 49. Weiss, D. J. et al. A global map of travel time to cities to assess inequalities in accessibility in 2015. Nature 553, 333–336 (2018). 50. Mukoro, V., Sharmina, M. & Gallego-Schmid, A. A review of business models for access to affordable and clean energy in Africa: Do they deliver social, economic, and environmental value? Energy Res. Soc. Sci. 88, 102530 (2022). 51. Bendinelli, W. E., Su, C. T., Péra, T. G. & Caixeta Filho, J. V. What are the main factors that determine post-harvest losses of grains? Sustain. Prod. Consum. 21, 228–238 (2020). 52. Irungu, K. R. G., Mbugua, D. & Muia, J. Information and communication technologies (ICTs) attract youth into proﬁtable agriculture in Kenya. New Pub. KARLO 81, 24–33 (2015). 53. Jolex, A. & Tufa, A. The effect of ICT use on the proﬁtability of young agripreneurs in Malawi. Sustainability 14, 2536 (2022). 54. Warr, P. Roads and poverty in rural laos: an econometric analysis. Paciﬁc Econ. Rev. 15, 152–169 (2010). 55. Amador-Jimenez, L. & Willis, C. J. Demonstrating a correlation between infrastructure and national developm"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Impact of COVID-19 on Airlines’ Financial Performance and Innovation Strategy",
  "item_id": "IRR-cc69",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "auto",
  "passages": [
   "019 is 64.6% of global passenger traffic. In addition, the AsiaPacific region has a loss of 2,148 million passengers, representing a decrease of 61.3% from all regions. The International Civil Aviation Organization (ICAO) (2021) reported that during the COVID-19 outbreak, the number of worldwide passengers decreased by 60% in 2020, 49% in 2021, and 27% to 32% in 2022 compared with the year 2019. Moreover, the Airports Council International World (ACI) (2021) said that airlines’ revenue dropped by around $380 billion compared to 2019. Due to the pandemic, travel restrictions grounded global aircraft by 64% in April 2020. Several studies have focused on factors impacting the airline industry. Bendinelli et al. (2016), Kalemba and Campa-Planas (2019), Fardnia et al. (2021), Chang et al. (2018) examine the relationship between accident records or safety and financial performance. Kiracı (2019) and Goh and Rasli (2014) explore the impact of the global financial crisis on the airline industry. Additionally, some studies have investigated the impacts of COVID-19 on corporate performance, for example, stock return (Maneenop & Kotcharin, 2020; Richardson et al., 2014), ROE and ROA (Achim et al., 2022; Anh & Gan, 2021), and return on ROI (Barros & Couto, 2013). However, studies on the impacts of nonfinancial factors, the number of passengers, available seat kilometers, revenue passenger kilometers"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Financial conditions and incumbent quality responses to entry: Evidence from airlines' on-time performance",
  "item_id": "IRR-27d7",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "while Prince and Simon [2015] uncover that LCC entry increases flight delays, Bubalo and Gaggero [2015] conclude just the opposite. Still Bendinelli et al., [2016] claim that there is little evidence to support either a moderating or accentuation effect of LCC entry on delays."
  ]
 },
 {
  "citation_style": "numeric",
  "citing_title": "Flight-Based Congestion Pricing Considering Equilibrium Flights in Airport Airside",
  "item_id": "IRR-3b60",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "auto",
  "passages": [
   "ical evidence in support of the internalization hypothesis was offered by Ref. [11], which showed that flight delays are lower at highly concentrated airports, where the dominant carrier is likely to internalize much of the congestion it creates, thus limiting its extent. Reference [12] presented a modeling framework for evaluating the sensitivity of airline schedules to the congestion pricing of airports. Reference [13] held that a significant part of the impact of congestion pricing cannot be accounted for by using models in the literature, which were based on the assumptions of constant load factors and constant aircraft sizes. References [14–16] provided a review of recent work about airport congesting pricing. Most of the above works did not give equilibrium flights and equilibrium prices either under aiming to joint profit maximization or under aiming to self-profit maximization. Equilibrium solutions are totally different under these two different scenarios. Furthermore, most of the above works are passenger-based method of congestion pricing, which took price difference under these two different scenarios as congestion price. Few of them are flight-based method of congestion pricing. Airport operations can be separated into airside and landside operations. These two components o"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Network development and excess travel time",
  "item_id": "IRR-1016",
  "n_passages": 2,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "Following Bendinelli et al. (2016), our study includes variables to control for concentration both at airport and market levels.",
   "Following Bendinelli et al. (2016), our study includes variables to control for con-"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "TESTING THE EFFECT OF HERBAL POWDERS ON GRAIN PARAMETERS IN STORED WHEAT IN THE PRESENCE OF SITOPHILUS ORYZAE UNDER FREE CHOICE",
  "item_id": "IRR-81e6",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "auto",
  "passages": [
   "the insects that infest grains that have been stored, and the genera Sitophilus and Tribolium are the most destructive species of storage insects (Khan and Selman 1988). The rice weevil, Sitophilus oryzae (L.), is one of the most destructive pests of cereal grains and their products. (Yan et al., 2014; Rita Devi et al., 2017). It is a major pest that feeds on whole grain kernels. Significant loss in grain weight, secondary pest infestation, and contamination due to growth of fungus are all results of adult feeding and larval activity inside kernels (Athanassiou et al., 2017). Grain production in many developing nations mainly depends on Small-scale farmers and postharvest processing mills (Bendinelli et al., 2020). When grains are stored, synthetic insecticides are used to control rice weevil pest. Chemical insecticides and fumigants were frequently used to treat insect storage pests, but this practice led to serious issues like the emergence of insect species that are resistant to insecticides (Zettler and Cuperus, 1990; Ribeiro et al., 2003; Lorini et al., 2007; Mehta and Kumar, 2020) and also recent laboratory studies indicated that many cultivars have developed some resistance to S. oryzae (Swamynarayana et al., 2014).Although inexpensive and feasible, fumigation has many drawbacks when compared to other methods of pest control. Insect populations are becoming more and more resistan"
  ]
 },
 {
  "citation_style": null,
  "citing_title": "An early assessment of the impact of COVID-19 on air transport: Just another crisis or the end of aviation as we know it?",
  "item_id": "IRR-8cba",
  "n_passages": 0,
  "paper": "airline",
  "passage_source": "curated",
  "passages": []
 },
 {
  "citation_style": "author_year",
  "citing_title": "Market shares on the rise, academic attention on the decline? A comprehensive review on low-cost airlines and their research challenges",
  "item_id": "IRR-ae39",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "Operationally, LCCs shape airport dynamics, influencing flight delays and capacity utilization (Bendinelli et al., 2016, Coto-Millán et al., 2014, Lee and Worthington, 2014)."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Institutional quality and green economic growth in West African economic and monetary union",
  "item_id": "IRR-3847",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "The trade openness is measured as the exports and imports of goods and services sum divided by GDP. The variable choice is supported by Bendinelli et al. (2020) and the expected sign is mixed."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Estratégias para reduzir o desperdício de frutas e hortaliças: a busca por sistemas atacadistas sustentáveis",
  "item_id": "IRR-a164",
  "n_passages": 2,
  "paper": "grains",
  "passage_source": "auto",
  "passages": [
   "food, but also to lower levels of losses and food waste (FAO, 2019). This Brazilian case study explores this gap and proposes efficient procedures to mitigate food waste, focusing on wholesale. This study aims to evaluate whether the combination of operational and management practices in the fruits and vegetables logistics and commercialization stages are associated with lower levels of wasting in the wholesale sector. This research contributes to the proposition of strategies that allow the establishment of fruit and vegetables sustainable supply chains identifying different ways to reduce food waste. MATERIAL AND METHODS Data description From the definitions of food loss and food wastes (Bendinelli et al., 2020; Gao et al., 2021), intentional losses are associated with the initial stages of the food supply chain, from agricultural production to agro-industrial processing (Figure 1), while intentional waste is associated with those occurring from the wholesale market to the consumer market (Figure 1). The research focused on the wholesale market in one of the main Wholesale Food Markets in Brazil, CEASA Campinas (Figure 1). Fresh foods of different perishability characteristics were evaluated, i.e.: lettuce (Lactuca sativa), potato (Solanum tuberosum), orange (Citrus sinensis), papaya (Carica papaya) and tomato (Lycopersicon esculentum). These are among the most consumed and commercia",
   "the practice by wholesale merchants that are associated with low waste of products and a rule for not performing practices that are associated with high waste of horticultural products (Box 2). The practices that contribute to greater logistics chain efficiency are: monitoring price movement, use of cold chain with regards to transport and storage, and the provision of services in accordance with the specificity of the customer. These were the variables associated with low levels of waste. Countries that have been reducing food waste rates have invested in building infrastructure, such as storage facilities, coupled with the transfer of knowledge and technology along the food supply chain (Bendinelli et al., 2020). Strengthening relations between government, industry and rural producers can contribute to reducing post-harvest losses (Gardas et al., 2017). [veículo removido] 40 (3) July - September, 2022 338 Strategies for reducing the waste of fruit and vegetable supply chains: the search for sustainable wholesale systems The frequencies of the variables were identified in the association rules (Box 2) related to low waste. Of the 17 possible practices carried out by the wholesale merchants in the chain, eight of them stood out (Box 2). Three practices are common for all nine rules associated with low waste. The practices perform services for clients, practice promotional pric"
  ]
 },
 {
  "citation_style": "numeric",
  "citing_title": "Revealing a Significant Latent Loss of Dry Matter in Rice Based on Accurate Measurement of Grain Growth Curve",
  "item_id": "IRR-70aa",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "In developing countries, the main causes of food loss are related to outdated harvest techniques and limited postharvest handling and infrastructure [6]."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Spillover delay effects of damaging wildlife strike events at U.S. airports",
  "item_id": "IRR-2ad1",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "we include three control variables that attempt to control for potential congestion and competition effects, which are studied determinants of on-time flight performance (Brueckner 2002a, 2002b, Mayer and Sinai 2003, Mazzeo 2003, Greenfield 2014, Bubalo and Gaggero 2015, Bendinelli et al. 2016, Fageda and Flores-Fillol 2016)."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "FOOD LOSSES IN PRIMARY CEREAL PRODUCTION. A REVIEW",
  "item_id": "IRR-0e5b",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "According to a recent definition food waste is the difference between the amount of food produced and the sum of all food employed in any kind of productive use, whether food or nonfood (Bendinelli et al., 2020)."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Robust Scheduling: An Empirical Study of Its Impact on Air Traffic Delays",
  "item_id": "IRR-1531",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "Bendinelli et al. (2016) address airline delays by separating the market-based level of competition and the airport-based dominance of an airline. They equally find a decrease in delays as competition on an origin-destination-market increases, whereas delays decrease as competition at an airport decreases."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Occupational hazards at grain pre-processing and storage facilities: A review",
  "item_id": "IRR-73e0",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "One of the main factors that determine postharvest losses of grains is the postharvest level of structure (Bendinelli et al., 2020)."
  ]
 }
]
```
