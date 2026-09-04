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

# LOTE 3 DE 4 — 28 ITENS

Codifique CADA item abaixo. Responda com UM ÚNICO bloco JSON (lista), um objeto por item, seguindo estritamente o contrato de saída acima. Não omita nenhum item_id. Não inclua comentários fora do JSON.

```json
[
 {
  "citation_style": "author_year",
  "citing_title": "Multi-airport privatization in a Japanese region with trip-chain formation",
  "item_id": "IRR-870d",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "According to some analytical inferences and empirical evidences (e.g. Brueckner, 2002; Bendinelli et al., 2016), dominant airlines have an incentive in internalizing congestion."
  ]
 },
 {
  "citation_style": null,
  "citing_title": "Use of Artificial Intelligence in post-harvest losses management: a current insight",
  "item_id": "IRR-0776",
  "n_passages": 0,
  "paper": "grains",
  "passage_source": "curated",
  "passages": []
 },
 {
  "citation_style": "author_year",
  "citing_title": "Antecipação de mudança de regime na fatia diária de voos atrasados e cancelados no aeroporto internacional de São Paulo/Guarulhos",
  "item_id": "IRR-f02e",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "orais (dia e hora), congestionamentos, redes de aeroportos e o clima. Yu et al. (2019) utilizaram um mé todo de aprendizado nã o supervisionado combinado com um algoritmo de aprendizado supervisionado de regressã o e classi;icaçã o para realizar aná lises de prevençã o de atrasos de voos. No Brasil, Scarpel e Pecicioni (2018) empregaram uma abordagem de aná lise de dados para construir um modelo de alerta com a ;inalidade de prever a ocorrê ncia de dias congestionados no GRU. A combinaçã o de abordagens de modelagem que se baseiam em diferentes premissas permitiu gerar um modelo com maior ;lexibilidade e trouxe melhorias na precisã o das previsõ es. Por uma concepçã o diferente, Bendinelli et al. (2016) analisaram se a ausê ncia de concorrê ncia favorecia o aumento das taxas de atrasos e cancelamento de voos, relaçã o que foi con;irmada pelos autores. Na literatura, há a criaçã o de modelos para prever atraso mé dio no dia ou a fatia de voos atrasados, considerando apenas informaçõ es relativas ao dia. Nesse tipo de modelo as observaçõ es sã o independentes, nã o se busca identi;icar associaçõ es entre dias diferentes. Este estudo tratou os atrasos em aeroportos por meio da identi;icaçã o de padrõ es de dias, de forma dependente em que se buscou identi;icar regimes que pudessem ser caracterizados utilizando uma distribuiçã o de probabilidade, ou seja, mé dia e"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "The blurring lines between full-service network carriers and low-cost carriers: A financial perspective on business model convergence",
  "item_id": "IRR-dd24",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "Bubalo and Gaggero (2015) showed that the presence of the LCC even could positively impact airport operations and foster improvement in service quality. A similar result has been reported by Bendinelli et al., (2016)."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Post-harvest losses in Indian maize amid increasing food insecurity Analysis using TOPSIS method",
  "item_id": "IRR-d073",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "ronment.\" Journal of Manufacturing Systems 37 (2015): 599-615. Cengiz Toklu, Merve. \"Interval type-2 fuzzy TOPSIS method for calibration supplier selection problem: A case study in an automotive company.\" Arabian Journal of Geosciences 11, no. 13 (2018): 1-7. Hengsdijk, H., and W. J. De Boer. \"Post-harvest management and post-harvest losses of cereals in Ethiopia.\" Food Security 9, no. 5 (2017): 945-958. Tefera, Tadele. \"Post-harvest losses in African maize in the face of increasing food shortage.\" Food security 4, no. 2 (2012): 267-277. Kaminski, Jonathan, and Luc Christiaensen. \"Post-harvest loss in sub-Saharan Africa—what do farmers say?.\" Global Food Security 3, no. 3-4 (2014): 149-158. Bendinelli, William Eduardo, Connie Tenin Su, Thiago Guilherme Péra, and José Vicente Caixeta Filho. \"What are the main factors that determine post-harvest losses of grains?.\" Sustainable production and consumption 21 (2020): 228238. Raut, Rakesh D., Bhaskar B. Gardas, Manoj Kharat, and Balkrishna Narkhede. \"Modeling the drivers of post-harvest losses–MCDM approach.\" Computers and Electronics in Agriculture 154 (2018): 426-433. Mogale, D. G., Sri Krishna Kumar, and Manoj Kumar Tiwari. \"Green food supply chain design considering risk and post-harvest losses: A case study.\" Annals of Operations Research 295, no. 1 (2020): 257-284. Kasso, Mohammed, and Afework Bekele. \"Post-harvest loss and quality deter"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Schedule creep – In search of an uncongested baseline block time by examining scheduled flight block times worldwide 1986–2016",
  "item_id": "IRR-bf00",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "As a rare exception, a flight is considered on time if it arrives later than 30min from its scheduled arrival time in Brazil (Bendinelli et al., 2016). Under the On-Time Disclosure Rule (OTDR) promulgated by the U.S. Department of Transportation in 1987, airlines accounting for at least one percent of U.S. domestic passenger revenue are required to report their on-time performance, which in turn is published monthly since 1995. With the increased prevalence of publicized aircraft-to-ground data communication since the late 1990s, numerous private organizations have been tracking on-time statistics linked to unique airline flight numbers. Flight-specific on-time statistics have been reported on airfare booking websites worldwide, potentially influencing passengers’ future travel decisions. As a result, individual airlines can and have been observed to adjust their scheduled block times to engineer better on-time performance to potentially make their schedule offers more attractive (Prince and Simon, 2009). Prior studies have linked higher percentages of flights arriving on time (i.e., within 15min of scheduled arrival time) to fewer customer complaints, which in turn leads to higher operating profits for airlines (Dresner and Xu, 1995; Steven et al., 2012). Under European Union Regulation 261/2004, compensation owed by airlines to passengers on a delayed flight is also calculated based on the difference between actual and scheduled arrival times, along with flight distance. It is therefore in the interest of airlines as profit-maximizing entities to increase scheduled block times to improve their so-called on-time arrival performance if they operate in the European Union. While anecdotal evidence has pointed to increasing scheduled block times over the years, evidence has concentrated in the U.S., T.P.C. Fan Transportation Research Part A 121 (2019) 192–217"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "An econometric study of the effects of airport privatization on airfares in Brazil",
  "item_id": "IRR-c3c8",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "Finally, airport congestion internalization pricing behavior by carriers may arise (Brueckner, 2002; Wan et al., 2015; Bendinelli et al., 2016; Guo et al., 2018; Miranda and Oliveira, 2018)."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Causal language intensity in performance commentary and financial analyst behaviour",
  "item_id": "IRR-d1c4",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "auto",
  "passages": [
   "trument variable, we ran a number of tests (Harford et al., 2014). Table 5 reveals that correcting for potential simultaneity bias in this way does not affect our prior findings on the association between causal reasoning intensity and properties of analyst behaviour. Predicted causal reasoning on performance is still significantly and positively associated with analyst following and negatively with analysts’ earnings forecast dispersion. The positive association between causal reasoning intensity and forecast accuracy also remains significant14. These results indicate that the instrument is significant in explaining the endogenous variables. Secondly, we ran the weak identification test (Bendinelli et al., 2016; Docquier et al., 2008) - the Cragg-Donald Wald F statistic value in Model I, II, and III, are 111.31, 82.08, and 80.72. The null hypothesis is rejected for all three models. Therefore, we conclude that our instrument variable is not a weak instrument. Finally, we ran the Sargan test for all three Models and found that our instrument does not suffer from the overidentification problem (chi-square p-value < 0.05 in all Models). 14 The magnitude of the coefficient increases substantially. As the first stage regression only captures a portion of the variation of the explanatory variable, its This article is protected by copyright. All rights reserved. 41 6. Supplementary tests"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Sustainable farming with machine learning solutions for minimizing food waste",
  "item_id": "IRR-eef4",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "ndal et al., 2024; Li et al., 2024a). This work aims to delineate these terms, employing precise definitions to anchor our discussion and analysis. Additionally, we explore the burgeoning role of Artificial Intelligence (AI) and Machine Learning (ML) in addressing these issues, demonstrating how technology can transform traditional practices in the agricultural sector (Taş et al., 2024; Li et al., 2024b; Han et al., 2024) (see Figs. 3 and 4). \"Post-harvest losses\" are defined as the quantitative and qualitative losses of food between harvest and sale, encompassing factors like spoilage during storage, degradation during transportation, and inefficiencies in processing (Minten et al., 2021; Bendinelli et al., 2020; Ma et al., 2022). These losses are predominantly seen within the supply chain and are influenced by technical, logistical, and managerial shortcomings (Cardoen et al., 2015; An and Ouyang, 2016; Jiang et al., * Corresponding author. E-mail addresses: olawaleabisola365@gmail.com (R.A. Olawale), olawumisola13@gmail.com (M.A. Olawumi), bioladapo@abuad.edu.ng (B.I. Oladapo). [DOI do citante removido] Received 31 October 2024; Received in revised form 27 February 2025; Accepted 28 February 2025 Available online 3 March 2025 0022-474X/© 2025 The Authors. Published by Elsevier Ltd. This is an open access article under the CC BY license (http://creativecommons.org/li"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Application of structural topic modeling in a literature review of air transport",
  "item_id": "IRR-fee5",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "studies have been conducted to compare airfares, service quality, and cooperation among air carriers (Bubalo and Gaggero, 2015; Bendinelli et al., 2016)."
  ]
 },
 {
  "citation_style": null,
  "citing_title": "Interaction of vehicles with the grain pre-treatment point",
  "item_id": "IRR-a050",
  "n_passages": 0,
  "paper": "grains",
  "passage_source": "curated",
  "passages": []
 },
 {
  "citation_style": "author_year",
  "citing_title": "Aircraft routing clusters and their impact on airline delays",
  "item_id": "IRR-3173",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "Bendinelli et al. (2016), for instance, investigated the incentives of an airline to increase on-time performance with the existence of market competition. They found delays to decrease with increasing competition on an origin destination market, but also concluded delays to decrease with decreasing competition at an airport."
  ]
 },
 {
  "citation_style": "numeric",
  "citing_title": "Finite Element and Applied Models of the Stem with Spike Deformation",
  "item_id": "IRR-0029",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "Injured grain has reduced germination, and pathogens develop in the resulting cracks during storage. This often makes it impossible to obtain quality seed material… the grain is unsuitable not only for the production of baked goods, but also for animal feed [5,21,22,23]."
  ]
 },
 {
  "citation_style": "numeric",
  "citing_title": "Grain Hermetic Storage Adoption in Northern Uganda: Awareness, Use, and the Constraints to Technology Adoption",
  "item_id": "IRR-7fe9",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "auto",
  "passages": [
   "pests and mycotoxin contamination [8] [9] [10]. These pose a substantial food security threat as they cause significant quantitative and qualitative losses of otherwise edible grains [11] [12] [13]. Globally, approximately one-third of the food produced for human consumption is lost or wasted annually post-harvest [14]. This quantity of food loss equates to the annual worth of cereal imports to SSA and exceeds the value of food aid supplied to SSA in a decade [15] [16]. Food that is lost or squandered on its way to consumption signifies a waste of resources in terms of land, labor, water, and other resources used to produce the food in vain [17] [18]. Because of the criticality of post-harvest food loss reduction, the 2030 Sustainable Development Goals (SDGs) emphasize raising global awareness of the issue. Target 12.3 of the SDGs calls for halving the global per capita food waste by 2030 and reducing food losses in the production and supply chains [19]. Grain PHLs during storage are estimated to be high, with dry weight losses reaching up to 30% [20] [21], but can be higher when considered together with DOI: [DOI do citante removido] 990 [veículo removido] F. Okori et al. quality losses [22] [23]. Insects, rodents, and molds are the leading causes of grain storage losses [23]"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Airline baggage fees and airport congestion",
  "item_id": "IRR-6be4",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "Empirical studies on this topic are less conclusive though, as some supporting the theoretical prediction (e.g., Brueckner 2002, Mayer and Sinai 2003, Rupp 2009, Ater 2012, Bilotkach et al. 2013, Bendinelli et al. 2016) while others providing evidences against it."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Grain Hermetic Storage and Post-Harvest Loss Reduction in Sub-Saharan Africa: Effects on Grain Damage, Weight Loss, Germination, Insect Infestation, and Mold and Mycotoxin Contamination",
  "item_id": "IRR-6caf",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "HS of grains also contributes to improved food price stability due to an increase in the amount of stored food, even during the crop off-seasons(Bendinelli et al., 2020)."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Day-ahead Flight Retiming and Aircraft Rerouting Considering Airport Congestion",
  "item_id": "IRR-edd4",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "The prior studies suggested that the hub-and-spoke carriers are more likely to internalize the delay costs caused by their own operations, i.e., “congestion internalization hypothesis” (Brueckner, 2005; Bendinelli et al., 2016)."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "The evaluation of the Balkan countries results relative to establishing effective market competition",
  "item_id": "IRR-327a",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "te, 1993; Lin et al., 2000; Gilbert, 2018), as well as in any other economic system such as Serbia (Begović & Mijatović, 2002; Begović & Pavić, 2010; Protić & Lazarević, 2015; Radivojević, 2018). Competition policy based on effective market competition eliminates the possibility of creating restrictive agreements, abuse of dominant position, and a merger between market participants that could have negative effects on competition. There are numerous empirical studies that examine the level of market competition in various industries worldwide. For example, Grzybowski (2008) and Whalley & Curwen (2012) explore market competition in the mobile telecommunications industry in European countries. Bendinelli, Bettini & Oliveira, (2016) and Oliveira & Oliveira (2018) analyse the level of market concentration and competition intensity in the airline industry. There is also a large body of similar studies in the banking industry (Bikker & Haaf, 2002; Michis, 2016), automobile industry (Levinsohn, 1994; Berry, Levinsohn & Pakes, 1999; Tansey & Raju, 2017), coal industry (Chen, 2013; Yang, Zhang & Wang, 2017), etc. 2. Research methodology, the hypothesis, and database As mentioned in the introduction section, the goal of this paper is to explore the results of the Balkan countries (with special emphasis on Serbia) in the process of establishing effective market competition and determine the existenc"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Subsidy strategies of grain supply chain considering stakeholder efforts on post-harvest loss reduction and pollution emission reduction",
  "item_id": "IRR-c6eb",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "At the same time, some focused on the whole supply chain of post-harvest loss (Bendinelli et al., 2019)."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Domestic code-sharing agreements and on-time performance: Evidence from the US airline industry",
  "item_id": "IRR-135c",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "Bendinelli et al. (2016) investigated the impact and behavior of low-cost carriers (LCCs) in airline markets. They are particularly interested in how the entry of LCCs affects airline flight delays in the Brazilian industry. In their analysis, they control for the effects of code-sharing and found no statistically significant effect."
  ]
 },
 {
  "citation_style": "numeric",
  "citing_title": "Adoption Dynamics of Hermetic Storage Technology and Post Harvest Quality Outcomes in Maize Production",
  "item_id": "IRR-54a4",
  "n_passages": 2,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "in food waste up to 98%. According to Bradford et al. [8], it is important to counter abiotic factors especially moisture content and climatic conditions to minimize storage losses. Commodities in the agricultural sector are also sensitive to moisture hence when they are stored enough, they have to be dried to attain an appropriate moisture content. Based on this, it is advised that the moisture value should be kept to less than 13% extended storage, and below 15% when the time to be stored is not more than six months (see Table 1). Furthermore, moving grain out of small farms to large, well monitored consolidated storage facilities is an effective approach of reducing PHL. As described by Bendinelli et al. [14], post-harvest grain losses refer to all the losses incurred after the grain has been harvested until the grain is eventually used either to be utilized as food or otherwise. The productivity of agriculture in most of the developing countries, mostly in SSA (sub-Saharan Africa) is still lower than that of wealthy countries. The low crop yield is further aggravated by PHL of legumes and cereals that usually amount to 20- 30% in many low-income nations around the globe. Tong et al. [15] describes that these losses may be in the quality or quantity of the grain thus majorly reducing the value of the grain. Losses would be quantitative due to scattering and spillage of grain, immedia",
   "un. 2006, doi: 10.1016/j.ijrefrig.2006.03.011. G. J. Daglish, M. K. Nayak, F. H. Arthur, and C. G. Athanassiou, “Insect Pest Management in Stored Grain,” in Recent Advances in Stored Product Protection, 2018, pp. 45–63. doi: 10.1007/978-3-662-56125-6_3. B. Nath, G. Chen, C. M. O’Sullivan, and D. Zare, “Research and Technologies to Reduce Grain Postharvest Losses: a review,” Foods, vol. 13, no. 12, p. 1875, Jun. 2024, doi: 10.3390/foods13121875. S. B. Williams, L. L. Murdock, and D. Baributsa, “Sorghum seed storage in Purdue Improved Crop Storage (PICS) bags and improvised containers,” Journal of Stored Products Research, vol. 72, pp. 138–142, May 2017, doi: 10.1016/j.jspr.2017.04.004. W. E. Bendinelli, C. T. Su, T. G. Péra, and J. V. C. Filho, “What are the main factors that determine post-harvest losses of grains?,” Sustainable Production and Consumption, vol. 21, pp. 228–238, Oct. 2019, doi: 10.1016/j.spc.2019.09.002. C. Tong, H. Gao, S. Luo, L. Liu, and J. Bao, “Impact of postharvest operations on rice grain quality: A review,” Comprehensive Reviews in Food Science and Food Safety, vol. 18, no. 3, pp. 626–640, Mar. 2019, doi: 10.1111/1541-4337.12439. J. MacPherson et al., “Future agricultural systems and the role of digitalization for achieving sustainability goals. A review,” Agronomy for Sustainable Development, vol. 42, no. 4, p. 70, Jul. 2022, doi: 10.1007/s13593-022-00792-6. A. O"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Design of a Cooling System Integrated with Ultraviolet Light for Preservation of Fruits and Vegetables at Variable Tropical Weather Conditions: A Case Study of Arusha, Tanzania",
  "item_id": "IRR-a1e3",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "auto",
  "passages": [
   "onditions (Gall and Benkeblia 2022, Freimoser et al. (Arah et al. 2016, Dhakulkar et al. 2018, 2019, Pétriacq et al. 2018). The challenge in Sibomana et al. 2016). Perishability of fruits minimizing fruits and vegetables post-harvest and vegetables is directly linked to rapid losses is largely hinged on how to come up quality losses immediately after harvest when with reliable and sustainable storage systems subjected to poor handling and storage for perishable produce at the minimum initial 741 http://tjs.udsm.ac.tz/index.php/tjs www.ajol.info/index.php/tjs/ Gunda et al. - Design of a Cooling System Integrated with Ultraviolet Light for Preservation and running costs (Ambuko et al. 2017, Bendinelli et al. 2020, Bustos and Moors 2018). Evaporative cooling systems are one of the options for horticultural post-harvest storage because of their environmental friendliness and energy-saving features (Verploegen et al. 2018, Elik et al. 2019, Rajapaksha et al. 2021). Evaporative cooling systems enable lowcost high-quality preservation of perishable products. These systems use less energy and have the potential to reduce post-harvest losses for small-scale farmers who do not have the means to invest in expensive systems that also demand a large amount of energy (Chopra and Kumar 2017, Lal Basediya et al. 2013, Zakari et al. 2016, AlZubaydi and Dartnall 2014). Chopra and Kumar proposed a semici"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "The impact of dust on Kuwait International Airport operations: a case study",
  "item_id": "IRR-a77b",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "The causes for delays are numerous and interconnected, but it can be summarized that delays happen when air transport operators interact with external factors which then leads to congestion (Bendinelli et al. 2016)."
  ]
 },
 {
  "citation_style": null,
  "citing_title": "Food Waste Biorefineries: Developments, Current Advances and Future Outlook",
  "item_id": "IRR-87ab",
  "n_passages": 0,
  "paper": "grains",
  "passage_source": "curated",
  "passages": []
 },
 {
  "citation_style": "author_year",
  "citing_title": "Post-harvest Management Strategies for Quality Preservation in Crops",
  "item_id": "IRR-1c64",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "Lack of infrastructure, and proper handling knowledge for post-harvest management result in high post-harvest loss in developing countries (Bendinelli et al., 2020)."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Does cargo matter? The impact of air cargo operations on departure on-time performance for combination carriers",
  "item_id": "IRR-2c1b",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "Most studies on airline delays address arrival delay instead of departure delay (e.g. Mayer and Sinai, 2003, Deshpande and Arikan, 2012, Bubalo and Gaggero, 2015, Prince and Simon, 2015, Bendinelli et al., 2016). In contrast to these studies, this work investigates delays resulting from handling not only passengers but also cargo."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Does competition increase quality? Evidence from the US airline industry",
  "item_id": "IRR-aa83",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "Some papers have found that airport and route concentration lead to better OTP levels (Mayer and Sinai, 2003; Rupp et al., 2006; Bendinelli et al., 2016; Prince and Simon, 2015), while others have found that more concentration in routes and airports is associated with worse OTP levels."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "The Impact of Delays on Customers’ Satisfaction: an Empirical Analysis of the British Airways On-Time Performance at Heathrow Airport",
  "item_id": "IRR-5c00",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "auto",
  "passages": [
   "ncentives to address congestion problems than smaller carriers and would therefore naturally internalize the costs associated with its self-imposed flight delays ( Daniel 1995 ; Brueckner 2002 ). This argument focuses on the role of peak/off-peak allocation of flights and passengers at an airport to inspect the incentives to manage congestion and avoid flight delays by dominant carriers, such as BA ( Mayer and Sinai 2003 ; Ater 2012 ). The internalization of costs of delays is determined by the strategic incentives of carriers when balancing the benefits from connections and passenger preferred times with the congestion costs, with evidence that strategic entry deterrence prevails at hubs ( Bendinelli et al. 2016 ). The average delay per flight on arrival from all causes decreased to 9 min per flight in 2013 in Europe. The average delay per delayed flight was 28.3 min. The percentage of delayed flights decreased by 0.8 percentage points to 33.7% in comparison to 2012 according to Central Office for Delay Analysis (CODA) of EUROCONTROL (2014) . London Heathrow Airport as a departure airport had a 14.6 min average delay per departure in 2013. The Average Delay per Delayed Departure was 26.5 min and the Percentage Delayed Departures was 49.5% in 2013. London Heathrow Airport ranked the highest affected airport on arrivals with an average delay per flight delay of 14.1 min, with weather an"
  ]
 }
]
```
