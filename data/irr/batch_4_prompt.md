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

# LOTE 4 DE 4 — 28 ITENS

Codifique CADA item abaixo. Responda com UM ÚNICO bloco JSON (lista), um objeto por item, seguindo estritamente o contrato de saída acima. Não omita nenhum item_id. Não inclua comentários fora do JSON.

```json
[
 {
  "citation_style": "author_year",
  "citing_title": "Ensuring food security: Strategies for insect pest detection in storage - A review",
  "item_id": "IRR-acf0",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "auto",
  "passages": [
   "arious abiotic and biotic factors. Biotic factors include insects, weeds, 380 Keerthana, B., et al./IFRJ 32(2): 379 - 399 pathogens, and other nematodes. They cause approximately 20 - 40% crop loss. It is estimated that only 18 - 20% of the crops produced worldwide are destroyed by insects, which leads to quantitative and qualitative food loss (FAO, 2019). Approximately, 33% of the globally produced food, equivalent to approximately 1.3 billion tons and valued at approximately US $1 trillion, is lost each year during postharvest operations. Addressing postharvest losses (PHL) is essential for improving food security, reducing waste, and enhancing the efficiency of the food supply chain (Bendinelli et al., 2020). The PHL remains a critical concern, as in field and storage godowns. Globally, it is quite common for plants to experience PHL of grains ranging from 10 - 15% (Hassan et al., 2023). In India, the storage loss of cereals is estimated to be approximately 0.75 to 1.21%, and for pulses and oilseeds, it varies from 1.18 to 1.67% and 0.22 to 1.61%, respectively (Ahmad et al., 2021). Stored grain insect pests pose a major threat to food security and economic stability. In food grain storage, insect infestations result in quantitative and qualitative losses, diminishing the overall value of the food grain. Storage grain pests not only feed on stored food grains, but also introduce co"
  ]
 },
 {
  "citation_style": "numeric",
  "citing_title": "Modeling and Control of an Indirect Solar Dryer in Forced Convection Mode Using System Identification and Model Predictive Control",
  "item_id": "IRR-ed51",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "auto",
  "passages": [
   "mplementation process HUMAN AND ANIMAL RIGHTS 6. CONCLUSION In conclusion, the proposed system successfully demonstrated the superior efficiency of an indirect solar dryer with forced convection mode, substantiated by compelling numerical results. The comparative assessment of three No violation of Human and Animal Rights is involved. FUNDING No funding is involved in this work. Rafiq et al.: Modeling and Control of an Indirect Solar Dryer in Forced Convection Mode Using System Identification and Model Predictive Control 827 DATA AVAILABILITY STATEMENT Data sharing not applicable to this article as no datasets were generated or analyzed during the current study. REFERENCES 0[1] W. E. Bendinelli, C. T. Su, T. G. P�era, and J. V. Caixeta Filho, “What are the main factors that determine post-harvest losses of grains,” Sustain. Prod. Consump., vol. 21, pp. 228–238, 2020. DOI: 10.1016/j.spc.2019.09.002. 0[2] G. V. Barbosa-C�anovas and P. Juliano, “Desorption phenomena in food dehydration processes,” in Water Activity Foods: fundamentals Applications. Ames, IA: Blackwell Publishing, 2020, pp. 425–452. 0[3] N. A. Safri et al., “Current status of solar-assisted greenhouse drying systems for drying industry (food materials and agricultural crops),” Trends Food Sci. Technol., vol. 114, pp. 633–657, 2021. DOI: 10.1016/j.tifs.2021.05.035. 0[4] V. K. Chauhan, S. K. Shukla, J. V. Tirkey, and P."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "The uneven geography of US air traffic delays: Quantifying the impact of connecting passengers on delay propagation",
  "item_id": "IRR-321e",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "Several studies argue that if dominant carriers internalise such costs, congestion pricing for Full Service Network Carriers should be adapted to account for internalised costs (Bendinelli et al., 2016; Brueckner and Van Dender, 2008; Miranda and Oliveira, 2018; Pels and Verhoef, 2004; Rupp, 2009)."
  ]
 },
 {
  "citation_style": null,
  "citing_title": "The Breeze Effect: Evidence on Demand Stimulation and Fare Impacts of An Emerging Low-Cost Carrier",
  "item_id": "IRR-a5c7",
  "n_passages": 0,
  "paper": "airline",
  "passage_source": "curated",
  "passages": []
 },
 {
  "citation_style": "author_year",
  "citing_title": "An Analysis of Flight Delays at Taoyuan Airport",
  "item_id": "IRR-1c51",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "auto",
  "passages": [
   "ork carriers and low cost carriers in Turkish Airline market. Procedia Soc. Behav. Sci. 207 , 642–651 (2015) Article Google Scholar M. Ball, C. Barnhart, M. Dresner, M. Hansen, K. Neels, A. Odoni, et al., Total Delay Impact Study: A Comprehensive Assessment of the Costs and Impacts of Flight Delay in the United States (Institute of Transportation Studies, University of California, Berkeley, Berkeley, 2010) Google Scholar P. Baumgarten, R. Malina, A. Lange, The impact of hubbing concentration on flight delays within airline networks: An empirical analysis of the US domestic market. Transp. Res. Part E Logistics Transp. Rev. 66 , 103–114 (2014) Article Google Scholar W.E. Bendinelli, H.F. Bettini, A.V. Oliveira, Airline delays, congestion internalization and non-price spillover effects of low cost carrier entry. Transp. Res. A Policy Pract. 85 , 39–52 (2016) Article Google Scholar P. Berster, M.C. Gelhausen, D. Wilken, Is increasing aircraft size common practice of airlines at congested airports? J. Air Transp. Manag. 46 , 40–48 (2015) Article Google Scholar C.F. Bien, Y.F. Low, Taoyuan airport vows to improve on-time performance. Central News Agency (2016, January 14) . Retrieved from http://www.taiwannews.com.tw/en/news/2868374 S. Borenstein, J. Netz, Why do all the flights leave at 8 am?: Competition and departure-time differentiation in airline ma"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Grain Trade: A Literature Review and Research Outlook",
  "item_id": "IRR-6a4c",
  "n_passages": 2,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "ng fair distribution of benefits between grain producing and consuming countries (Sotelo, 2020). In particular, in developing countries, the expansion of grain trade should benefit small farmers and vulnerable groups locally, contributing to socially inclusive development. Fair trade mechanisms can ensure that grain producers receive more reasonable income, improving their production conditions and living standards (Kathiresan et al., 2020). Furthermore, governments and NGOs can support small farmers by providing financial assistance, technical training, and market access, helping them better participate in the international grain market, improving their income levels, and reducing poverty (Bendinelli et al., 2020). Future grain trade policies should focus on achieving a balanced coordination of economic benefits, environmental protection, and social fairness. Lastly, the development of grain trade faces unpredictable challenges, such as extreme weather due to global warming, supply chain disruptions caused by political conflicts, and logistical issues related to pandemics. Addressing these challenges requires joint efforts from governments, international organizations, businesses, and academia (Maiyar & Thakkar, 2019). Future research should delve deeper into risk management in grain trade, such as establishing an international grain risk management platform to monitor and assess global",
   "Furthermore, governments and NGOs can support small farmers by providing financial assistance, technical training, and market access, helping them better participate in the international grain market, improving their income levels, and reducing poverty (Bendinelli et al., 2020)."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Evaluating Physical and Chemical Quality of Corn Kernel as Poultry Feed Ingredient in the Procurement of Feed Mill Raw Material",
  "item_id": "IRR-b03f",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "auto",
  "passages": [
   "classified into three quality levels: Premium, Medium I, and Medium II (BSN, 2020). Generally, farmers employ conventional farming practices, particularly in crop management aspects such as shelling, drying, and storage (Cecil et al., 2023). Corn shelling is typically done using locally produced sheller machines that are often unstandardized and untested. The drying process involves spreading the corn on tarps and leaving it to dry in the sun for two to three days. Consequently, the moisture content of the corn is highly dependent on weather conditions during drying. This traditional drying and storage method can lead to significant contamination of the corn kernels and postharvest losses (Bendinelli et al., 2020). Feed mills must carefully adjust the quality of lowgrade corn to meet factory feed formulation standards. A key factor affecting feed quality is moisture content, which recommends maintaining moisture levels between 14% and 16% (Cabañas-Ojeda et al., 2023). Corn with moisture levels exceeding 16% is prone to quality degradation, storage damage, and increased risk of fungal contamination. Damaged kernels, including moldy or cracked seeds, are particularly vulnerable to contamination by destructive microorganisms such as fungi (Islam et al., 2018). These contaminants can lead to mycotoxins, such as deoxynivalenol and zearalenone, negatively affecting feed safety. No significant"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Assessing gendered impacts of post-harvest technologies in Northern Ghana: gender equity and food security",
  "item_id": "IRR-e113",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "Ghana has one of the highest incidences of PHL in the world, significantly higher than other middle income countries (Bendinelli et al., 2020)."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Gendering post-harvest loss research: responsibilities of women and men to manage maize after harvest in southwestern Ethiopia",
  "item_id": "IRR-cc96",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "ther post-harvest loss reduction or in gender equality. However, potentially more problematic is the scenario in which progress on post-harvest loss reduction is achieved but that “food loss reduction does not address or even exacerbates gender inequalities” (2018, p. 19). Despite this increased awareness among development actors, most scientific research on post-harvest losses does not consider gender. In a literature review of fruit and vegetable post-harvest loss research by Gardas et al. (2018), none of the studies included brought up the issue of gender. A few journal articles on PHL that do bring up the term ‘gender’, do not actually go beyond sex disaggregation of household headship (Bendinelli et al., 2020; Chegere, 2018) For example, Chegere (2018), only separates the data by female and male household heads in a study about the economic trade-offs of adopting measures recommended to reduce post-harvest losses with no inclusion of other post-harvest management roles conducted by women and men. These studies do not make an effort to untangle any of the other gendered dynamics, for example at the household level, that relate to post-harvest management. 3 \u0007Research context and methods Jimma Zone, one of twenty in Oromia Regional State, was selected from the southwestern part of Ethiopia. Over 90% of the population of Jimma Zone is Oromo. Gender differences among the Jimma Oromo are"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "An overview of agriculture 4.0 development: Systematic review of descriptions, technologies, barriers, advantages, and disadvantages",
  "item_id": "IRR-e65d",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "A part of the waste in agriculture is related to the incidence of bad weather, increased tolerance of pests, and misuse of technologies (Baributsa and Njoroge, 2020, Bendinelli et al., 2020) in the agricultural production chain."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Financial distress, survival network design strategies, and airline pricing: An event study of a merger between a bankrupt FSC and an LCC in Brazil",
  "item_id": "IRR-692a",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "The procedure is similar to the one presented in, e.g., Bendinelli et al. (2016). The structural instruments consist of demand shifters, commonly used to identify variables in price models, which are expected to influence market concentration, number of passengers, and/or the extent of financial distress."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Nearly half of the world is suitable for diversified farming for sustainable intensification",
  "item_id": "IRR-6fce",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "47. Li, S. & Kallas, Z. Meta-analysis of consumers’ willingness to pay for sustainable food products. Appetite 163, 105239 (2021). 48. Kumar, A. et al. Adoption and diffusion of improved technologies and production practices in agriculture: insights from a donor-led intervention in Nepal. Land Use Policy 95, 104621 (2020). 49. Weiss, D. J. et al. A global map of travel time to cities to assess inequalities in accessibility in 2015. Nature 553, 333–336 (2018). 50. Mukoro, V., Sharmina, M. & Gallego-Schmid, A. A review of business models for access to affordable and clean energy in Africa: Do they deliver social, economic, and environmental value? Energy Res. Soc. Sci. 88, 102530 (2022). 51. Bendinelli, W. E., Su, C. T., Péra, T. G. & Caixeta Filho, J. V. What are the main factors that determine post-harvest losses of grains? Sustain. Prod. Consum. 21, 228–238 (2020). 52. Irungu, K. R. G., Mbugua, D. & Muia, J. Information and communication technologies (ICTs) attract youth into proﬁtable agriculture in Kenya. New Pub. KARLO 81, 24–33 (2015). 53. Jolex, A. & Tufa, A. The effect of ICT use on the proﬁtability of young agripreneurs in Malawi. Sustainability 14, 2536 (2022). 54. Warr, P. Roads and poverty in rural laos: an econometric analysis. Paciﬁc Econ. Rev. 15, 152–169 (2010). 55. Amador-Jimenez, L. & Willis, C. J. Demonstrating a correlation between infrastructure and national developm"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Assessing drivers of post-harvest losses: tangible and intangible resources’ perspective",
  "item_id": "IRR-4f3b",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "Also, it tends to impact the income generation of producers and consumer food security, which often leads to higher prices for available substitutes (Bendinelli et al., 2019)."
  ]
 },
 {
  "citation_style": null,
  "citing_title": "Optimizing modified ecological compositions enables eco-friendly control of Tribolium castaneum in grain storage",
  "item_id": "IRR-3978",
  "n_passages": 0,
  "paper": "grains",
  "passage_source": "curated",
  "passages": []
 },
 {
  "citation_style": "author_year",
  "citing_title": "Losses in agricultural produce: A review of causes and solutions, with a specific focus on grain crops",
  "item_id": "IRR-7fe7",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "The definition of losses can vary depending on factors such as the type of product, storage conditions, handling practices, and market dynamics (Bendinelli et al., 2020)."
  ]
 },
 {
  "citation_style": "numeric",
  "citing_title": "An econometric analysis for the determinants of flight speed in the air transport of passengers",
  "item_id": "IRR-357b",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "auto",
  "passages": [
   "For example, Mcconnachie et al.17, observed a reduction in mean speeds concomitantly with increases in fuel prices. • Flight delay management: refers to identifying, assessing, and mitigating delays in flight operations. A delayed flight can cause a cascading effect on the entire schedule of a carrier and disrupt the plans of many passengers and airports, besides other airlines. Flight delay management is therefore a critical function of flight operations. One of the strategies of flight delay management is flight schedule recovery, which can include adjusting the flight schedules and speeds, besides rerouting flights to minimize the impact of delays. Prince and ­Simon4, Kang and ­Hansen3, Bendinelli et al.28, Eufrásio et al.23, and Calzada and ­Fageda29, among many others, investigate the association between market competition and airlines’ concern with punctuality. • Airport operations: refers to the management and coordination of all activities performed at the endpoint airports of a flight. It involves many institutions besides the airline, including, among others, the ground handling of aircraft, passenger and baggage processing, air traffic control, and maintenance of the airport facilities and equipment. The primary goal of airport operations is to ensure that flights are conducted safely and efficiently, while also providing a high level of service to passengers and other airpor"
  ]
 },
 {
  "citation_style": "numeric",
  "citing_title": "Optimizing Supply Chain Management to Reduce Food Waste and Loss in Agriculture",
  "item_id": "IRR-efbf",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "These losses are caused by poor handling, poor storage facilities, or lack of proper logistics [2]."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Low costs na aviacao: importancia e desdobramentos",
  "item_id": "IRR-e06d",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "auto",
  "passages": [
   "Além do impacto no preço, como foi levantada na frase de Porter (2008), a presença de um concorrente pode forçar as companhias existentes a mudarem suas operações ou mesmo estratégias de negócio, e essa hipótese também foi testada nos últimos anos pela literatura da aviação. Sun (2015) diz que a presença de LCCs numa rota aumenta a diferenciação dos tempos de partida das aeronaves numa tentativa de evitar a concorrência direta ou o horário de pico, além de oferecer um produto diferenciado aos passageiros. Seguindo nessa linha, Mohammadian et al. (2019) dizem que as companhias aéreas concorrentes chegam a mudar o tipo de aeronave utilizada e até a frequência de voos servidos em uma rota. Já Bendinelli et al. (2016) encontraram resultados sugerindo que a presença de uma LCC pode ser responsável pela internalização dos custos dos atrasos pelas suas companhias aéreas. Ainda sobre impactos nas operações e estratégias das companhias aéreas incumbentes, Pearson et al. (2015) fizeram uma pesquisa investigativa no mercado asiático para avaliar a capacidade estratégica das companhias aéreas tradicionais para competir com o crescente número de LCCs naquele mercado; eles concluem que o nordeste asiático é a região em que as companhias aéreas estão menos preparada para a concorrência com as low costs, e que portanto as network carriers dessa região devem fortalecer a sua capacidade estratégica tanto"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Financial conditions and incumbent quality responses to entry: Evidence from airlines' on-time performance",
  "item_id": "IRR-1d19",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "while Prince and Simon [2015] uncover that LCC entry increases flight delays, Bubalo and Gaggero [2015] conclude just the opposite. Still Bendinelli et al., [2016] claim that there is little evidence to support either a moderating or accentuation effect of LCC entry on delays."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Convergence in airline operations: The case of ground times",
  "item_id": "IRR-0439",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "The operational share of an airline at an airport impacts on on-time performance of flight activities (Brueckner, 2002; Bendinelli et al., 2016). Consequently, we include this variable to control for its impact on ground times."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "What drives effective competition in the airline industry? An empirical model of city-pair market concentration",
  "item_id": "IRR-b9db",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "the literature has investigated and found a statistically significant association between airline delays and concentration at the airport and route levels - Mayer and Sinai, 2003, Mazzeo, 2003, Ater, 2012, and Bendinelli et al. (2016)."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Airport slots and the internalization of congestion by airlines: An empirical model of integrated flight disruption management in Brazil",
  "item_id": "IRR-1b78",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "We extend the literature on the congestion internalization behaviors of major airlines to examine the possible impact of airport slots (Daniel, 1995, Brueckner, 2002, Mayer and Sinai, 2003a, Santos and Robin, 2010, Ater, 2012, Bendinelli et al., 2016)."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Modeling the key factors leading to post-harvest loss and waste of fruits and vegetables in the agri-fresh produce supply chain",
  "item_id": "IRR-cda7",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "Bendinelli et al. (2020) discussed the influence of macroeconomic conditions on the PHL of grains (rice, maize, soybeans, and wheat). The results revealed that the lack of post-harvest infrastructure, especially in food storage and food marketing, was the significant cause of PHL."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Airport dominance, route network design and flight delays",
  "item_id": "IRR-3c3a",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "Bendinelli et al. (2016) try to conciliate these two strands of the literature by presenting a single econometric model to test both the “congestion internalization effect” and the “competition-quality effect”. Specifically, they suggest that airlines’ internalization of congestion can be explained by their dominant position at the airport."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Low-Cost Carriers in Aviation: Significance and Developments",
  "item_id": "IRR-6d84",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "auto",
  "passages": [
   "assic literature on the effects of LCCs on fares. In addition to price impacts, as highlighted by Porter (2008), the presence of a competitor can compel existing companies to modify their operations or even their business strategies—a hypothesis that has also been tested in recent aviation research. Sun (2015) found that the presence of LCCs on a route increases the differentiation of aircraft departure times as airlines seek to avoid direct competition or peak hours while offering a more differentiated product to passengers. Along similar lines, Mohammadian et al. (2019) reported that competing airlines also adjust the type of aircraft used and the frequency of flights operated on a route. Bendinelli et al. (2016) presented results suggesting that the presence of an LCC may lead incumbent airlines to internalize delay costs. Regarding the impacts on the operations and strategies of incumbent airlines, Pearson et al. (2015) conducted an exploratory study in the Asian market to assess the strategic capacity of traditional airlines to compete with the growing number of LCCs in the region. They concluded that Northeast Asia is the area where airlines are least prepared to face competition from low-cost carriers, and therefore network carriers in this region should strengthen their strategic capacity @ 2024 Center for Airline Economics, Brazil. 2 both to improve responsiveness to LCCs an"
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Understanding the nexus of postharvest losses and food insecurity: Empirical evidence from Nigeria",
  "item_id": "IRR-786d",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "Educated farmers with more assets tend to use better storage and handling practices, which helps lower physical and economic losses (Debebe, 2022; Bendinelli et al., 2020; Kikulwe et al., 2018)."
  ]
 },
 {
  "citation_style": "author_year",
  "citing_title": "Airline competition: A comprehensive review of recent research",
  "item_id": "IRR-be8d",
  "n_passages": 1,
  "paper": "airline",
  "passage_source": "curated",
  "passages": [
   "Bendinelli et al. (2016) | Ana | 209 routes in Brazil | 2002–2013 | Effects of LCC entry"
  ]
 },
 {
  "citation_style": "numeric",
  "citing_title": "Containerized Grain Logistics Processes for Implementing Sustainable Identity Preservation",
  "item_id": "IRR-4ed0",
  "n_passages": 1,
  "paper": "grains",
  "passage_source": "curated",
  "passages": [
   "Bendinelli et al. [17] empirically investigated the representative factors contributing to post-harvest losses of grains (rice, maize, soybean, and wheat) and found that insufﬁcient post-harvest infrastructure, especially in food storage and food marketing, could lead to higher post-harvest losses."
  ]
 }
]
```
