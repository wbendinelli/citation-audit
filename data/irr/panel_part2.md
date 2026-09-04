# Colegiado de adjudicação — codificação de citações

Você decide os eixos em que três codificadores independentes divergiram em três valores distintos, ou em que a maioria dos dois cegos contraria o codificador que tinha o texto completo. Regras:

1. Decida SÓ os eixos listados em "DECIDIR" de cada item. Os demais já estão decididos por maioria.
2. O codebook abaixo é a única régua; cite a regra que fundamenta cada decisão.
3. `presence`: c1 leu o texto completo; c2 e c3 viram só a janela do pacote. Se a janela automática mostrou trecho irrelevante (conclusão, bibliografia) e c1 diz `in_text`, a evidência de c1 prevalece.
4. `accuracy`: o registro de afirmações é a verdade sobre o que o artigo diz. Afirmação `relayed` atribuída ao artigo como achado próprio = `misrepresented` + `relayed_attribution`. Bloco que cola o artigo a afirmação que ele não contém = `imprecise` (tema adjacente) ou `misrepresented` + `dead_end` (nenhum conteúdo relevante). Extensão de escopo (outras culturas, outra geografia, comportamento individual a partir de painel macro) = `imprecise` + `diversion`. `misrepresented` só quando o objeto ou a DIREÇÃO do achado está errado.
5. `depth`: bloco genérico = drive_by; uma afirmação específica atribuída = brief_mention; descrição do conteúdo real = real_mention; sustenta desenho ou argumento do citante = supporting; constrói sobre, ou referência única = foundational.
6. `distortion` só quando accuracy ≠ accurate; senão null.
7. Saída: UM bloco JSON `{item_id: {eixo: valor, ..., "rationale": "≤40 palavras"}}`, só os eixos a decidir, valores exatos do vocabulário.

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



## Registro de afirmações
- AIR-M01 [original]: Arcabouço unificador: testa em um ÚNICO modelo econométrico a hipótese de internalização do congestionamento aeroportuário e a de relação competição-qualidade no mercado, dispensando a hipótese de simetria de rotas da literatura de internalização.
- AIR-M02 [original]: O modelo não impõe a hipótese de simetria de rotas e admite internalização de congestionamento EM PARALELO à gestão de qualidade de serviço, o que permite pôr concentração de rota e de cidade na mesma equação.
- AIR-M03 [original]: A endogeneidade do HHI de rota e do HHI máximo das cidades-extremo é tratada por variáveis instrumentais estimadas por GMM eficiente factível em dois passos (2SGMM), com erros-padrão robustos a heterocedasticidade e autocorrelação (Newey-West, kernel de Bartlett).
- AIR-M04 [original]: Identificação por instrumentos do tipo Hausman: a concentração de outras rotas instrumenta a concentração de uma dada rota, descartando cidades próximas segundo três limiares (150, 300 e 500 km); validade e relevância checadas por Hansen J e Kleibergen-Paap.
- AIR-M05 [original]: Duas famílias de regressandos: ODDS (log-odds da proporção de voos atrasados = PREVALÊNCIA) e MINS (diferença média em minutos entre chegada programada e efetiva = DURAÇÃO), além de versões truncadas (MINS>15, MINS>30) e de partida (ODDSD, MINSD).
- AIR-D01 [original]: Painel de 209 rotas brasileiras de janeiro de 2002 a dezembro de 2013, agregado ao nível rota-mês, restrito a rotas entre capitais estaduais e Brasília; a rota é definida como par-de-cidades doméstico e direcional.
- AIR-D02 [original]: Fonte primária: o relatório Voo Regular Ativo (VRA) da ANAC, base online com dados no nível do voo — empresa, par-de-aeroportos, número do voo e horários programados e efetivos — desde 2000, com código de justificativa de cada atraso.
- AIR-D03 [original]: A base bruta tem 10 milhões de voos do VRA. As incumbentes full-service analisadas são Tam, Varig, Transbrasil e Vasp; as low cost carriers da amostra são Gol e Azul.
- AIR-D04 [original]: Aplicação a uma economia emergente: o Brasil é caso em que os atrasos são longamente debatidos e em que pedágios de congestionamento nunca foram implementados; a aviação comercial foi plenamente desregulamentada em 2001.
- AIR-D05 [original]: Descritivo (Tabela 1): a proporção de voos atrasados caiu 33,5% de 2006-2010 para 2011-2013 e 5,3% frente a 2002-2005; no mesmo confronto o hubbing caiu 11,0%, o HHI de cidade subiu 4,3% e o de par-de-cidades caiu 0,4%.
- AIR-DEF01 [original]: Atraso é medido pelo padrão de 15 minutos do BTS/DOT norte-americano — e NÃO pelo padrão brasileiro de 30 minutos da ANAC — computado sobre a diferença entre a chegada programada e a efetiva.
- AIR-DEF02 [original]: 'Hora congestionada' é a hora cheia em que o número de operações (pousos mais decolagens) supera a capacidade oficial declarada do aeroporto, conforme estudo de capacidade encomendado pelo governo brasileiro.
- AIR-F01 [original]: Achado 1: a concentração no nível do AEROPORTO/CIDADE REDUZ os atrasos. O coeficiente de HHI max endpoint cities é negativo e significante em todas as especificações de ODDS e MINS — evidência de internalização do congestionamento (H1).
- AIR-F02 [original]: Achado 2: a concentração no nível da ROTA/MERCADO AUMENTA os atrasos. O coeficiente de HHI city-pair é positivo e significante ao menos a 5% em todos os casos — evidência da relação competição-qualidade (H2).
- AIR-F03 [original]: Achado 3: a presença de LCC nas CIDADES-EXTREMO reduz a PREVALÊNCIA dos atrasos (coeficiente negativo e significante em ODDS) mas NÃO a sua DURAÇÃO (não significante em MINS) — internalização extra induzida pela entrada.
- AIR-F04 [original]: Achado 4: NÃO há efeito robusto da presença de LCC na PRÓPRIA ROTA — as respostas locais à entrada são não significantes ou significantes só a 10%, sem apoio à hipótese de corte de custos/preços de Prince e Simon (2015).
- AIR-F05 [original]: Achado 5 (título do artigo): spillover não-tarifário — a entrada de LCC em uma rota gera competição potencial nas demais rotas da cidade, com efeito positivo sobre a pontualidade das rotas NÃO entradas.
- AIR-F06 [original]: Omitir o HHI de cidade enviesa negativamente a estimativa do HHI de rota (correlação de 0,48 entre as duas): qualquer subespecificação das variáveis de concentração pode gerar estimação inconsistente e falso negativo.
- AIR-F07 [original]: Ignorar a endogeneidade inverte os sinais: sob OLS os sinais dos HHI mudam, o que sustenta a recomendação de estimação por variáveis instrumentais. Resultados estáveis sob LIML e com atrasos de partida.
- AIR-I01 [interpretation]: Interpretação dos autores: há um aparente paradoxo — as incumbentes auto-internalizam congestionamento quando sua dominância aeroportuária aumenta e TAMBÉM mantêm alguma internalização quando essa dominância é desafiada pela entrada de uma LCC.
- AIR-I02 [interpretation]: Mecanismo CONJECTURADO, não testado: depeaking, com voos realocados para horários fora de pico em que a LCC é mais atrativa a passageiros de lazer, permitiria manter a internalização mesmo com queda da concentração aeroportuária.
- AIR-P01 [original]: Implicação de política: enquanto a competição por qualidade é observada localmente no mercado, a emergência e o crescimento das LCCs podem ser um fator adicional de melhoria da pontualidade do setor aéreo.
- AIR-L01 [limitation]: Limitação: os atrasos são medidos estritamente contra o horário programado, sem controlar o padding estratégico de malha; o recorte par-de-cidades também impede observar realocações estratégicas entre pares de aeroportos adjacentes.
- AIR-R01 [relayed]: REPASSADO de Molnar (2013): a internalização depende dos incentivos estratégicos das empresas ao equilibrar benefícios de conexões e horários preferidos com custos de congestionamento, havendo evidência de que a DISSUASÃO ESTRATÉGICA DE ENTRADA PREVALECE NOS HUBS.
- AIR-R02 [relayed]: REPASSADO de Daniel (1995) e Brueckner (2002): a companhia dominante de um aeroporto teria incentivos mais fortes que as menores para enfrentar o congestionamento e internalizaria naturalmente os custos dos atrasos que ela própria impõe.
- AIR-R03 [relayed]: REPASSADO de relatório de 2014 do Office of Inspector General da FAA: a ausência de competição em muitas rotas pode ser fonte de aumento das taxas de atrasos e cancelamentos de voos.
- AIR-R04 [relayed]: REPASSADO de Rupp e Sayanak (2008) e Castillo-Manzano e Lopez-Valpuesta (2014): as LCCs apresentam melhor desempenho de pontualidade do que as full-service carriers. Não é resultado próprio deste artigo.
- AIR-R05 [relayed]: REPASSADO: Prince e Simon (2015) acham que a entrada de LCC AUMENTA os atrasos das incumbentes via corte de custos sob competição de preços; Bubalo e Gaggero (2015) acham o contrário. A literatura carece de consenso.
- AIR-R06 [relayed]: REPASSADO de Daniel e Harback (2008), Rupp (2009) e, em certa medida, Bilotkach e Lakew (2014): há evidência de AUSÊNCIA de auto-internalização, o que sugeriria papel para a tarifação de congestionamento.
- AIR-R07 [relayed]: REPASSADO de Brueckner, Lee e Singer (2014): pares de CIDADES, e não pares de aeroportos, são a definição de mercado apropriada em muitas análises de transporte aéreo — justificativa do recorte adotado.
- GR-DEF01 [original]: PHL são definidas como a redução NÃO INTENCIONAL da quantidade de alimento produzido para consumo humano em todas as etapas da cadeia de suprimentos, independentemente de causa ou destino, EXCLUÍDAS as etapas de varejo e consumo final.
- GR-DEF02 [relayed]: REPASSADO da literatura: distingue-se food loss, que ocorre nas etapas iniciais da cadeia, de food waste, que ocorre no varejo ou depois de chegar ao consumidor e está ligado a comportamento — ato intencional de uma pessoa.
- GR-DEF03 [relayed]: A variável dependente %PHL segue a fórmula de Gustavsson et al. (2013): perdas divididas pela oferta, sendo oferta = produção + importação + variação de estoques. A fórmula NÃO é dos autores.
- GR-D01 [original]: Painel de 82 países entre 2000 e 2011, selecionados por deterem ao menos 1% da oferta doméstica de grãos de sua região geográfica; dados de oferta doméstica das Food Balance Sheets da FAO (FAOSTAT).
- GR-D02 [original]: Os grãos analisados são arroz, milho, soja e trigo — principal fonte de alimento para humanos e animais; dados independentes vêm de FAOSTAT, Banco Mundial e UNESCO.
- GR-D03 [original]: ATENÇÃO: os 82 países são a base bruta. Após excluir dados faltantes e outliers (acima de 3 desvios-padrão), o painel desbalanceado efetivamente estimado tem 546 observações/69 países, e 534 observações/68 países nos modelos-base.
- GR-M01 [original]: Especificação log-log (Eq. 2) da variável dependente e das explicativas, adotada para capturar as não-linearidades do problema e ler os parâmetros estimados diretamente como elasticidades, evitando uma etapa extra de estimação.
- GR-M02 [original]: Estimação por mínimos quadrados generalizados factíveis (FGLS) em painel, com efeitos fixos de grupo e de tempo e estatísticas robustas a heterocedasticidade e correlação serial, com parâmetro de correlação único por painel.
- GR-M03 [original]: Diagnósticos: raiz unitária tipo Fisher (Choi, 2001) com médias transversais subtraídas, Wald modificado para heterocedasticidade entre grupos e teste de Wooldridge para autocorrelação de 1ª ordem, corrigida por Newey-West.
- GR-M04 [original]: Tratamento da endogeneidade: ln_supply é excluído das especificações com %PHL e o PIB per capita é convertido em quatro dummies de faixa de renda, o que permite manter ln_price e ln_trade no modelo.
- GR-M05 [original]: Novidade declarada: é o PRIMEIRO trabalho a estimar determinantes de PHL com painel de dados mundial e correções para reduzir viés de parâmetros; os únicos dois antecedentes globais (KC et al., 2016; Rosegrant et al., 2015) teriam viés maior.
- GR-F01 [original]: Achado principal: o PIB per capita é o determinante de MAIOR impacto sobre as PHL nos modelos-base (colunas 4 e 6 da Tabela 3), reduzindo-as intensamente.
- GR-F02 [original]: A relação entre desenvolvimento econômico e PHL é NÃO-LINEAR e compatível com uma curva de Kuznets: ln_income entra positivo (2,017 e 2,899) e ln_square_income negativo (-0,135 e -0,184), ambos a 1%.
- GR-F03 [original]: Lacunas por faixa de renda, com high_income como grupo-base (Tabela 3, col. 6): low_income +0,731; low_middle_income +0,706; upper_middle_income +0,534 em log de %PHL, todos significantes a 1%.
- GR-F04 [original]: A urbanização REDUZ as PHL com efeito moderado: países pouco urbanizados apresentam 29,9% mais PHL e os de urbanização média 23,6% mais PHL do que os altamente urbanizados.
- GR-F05 [original]: A abertura ao comércio internacional REDUZ as PHL (ln_trade -0,204 a -0,216): países com baixo nível de comércio global têm 23,9% mais PHL do que os de alto nível, por padronização de operações e embalagens.
- GR-F06 [original]: A crise de 2008-2011 AUMENTOU as PHL (dummy crisis positiva e significante a 1% nos modelos-base, +0,138 e +0,292), por afetar o poder de compra do consumidor e suspender investimentos, por exemplo em armazenagem fora da fazenda.
- GR-F07 [original]: Efeitos de BAIXA magnitude para tamanho do setor de alimentos, volatilidade do preço de alimentos (positiva sobre PHL, +0,059 a +0,087) e densidade ferroviária (negativa); a densidade rodoviária NÃO é significante nos modelos-base.
- GR-F08 [original]: O excedente alimentar (ln_supply) AUMENTA fortemente as PHL (coeficientes de 0,95 a 1,56): onde a oferta supera a demanda há baixo incentivo econômico para evitar perdas e pode faltar infraestrutura para lidar com o excedente.
- GR-F09 [original]: Achado-síntese: há um TRADE-OFF difícil entre ampliar a oferta de alimentos e o nível de PHL — sem infraestrutura pós-colheita adequada, sobretudo armazenagem e comercialização, o esforço para aumentar a oferta eleva as PHL.
- GR-F10 [original]: Robustez: trocar a dependente de %PHL para toneladas inverte os sinais de rodovia, ferrovia e urbanização — esperado, pois a variável não é ponderada; ponderando pela população, só setor de alimentos e ferrovia trocam de sinal.
- GR-P01 [original]: Política: esforços para aumentar a produção de alimentos não podem se restringir à produção na fazenda, pois geram excedente e PHL muito maiores; devem ser complementados por investimentos em infraestrutura pós-colheita, em especial armazenagem e comercialização.
- GR-P02 [original]: Política: a construção de infraestrutura como instalações de armazenagem em países em desenvolvimento, somada à transferência de conhecimento e tecnologias de países industrializados, tem levado à redução das PHL.
- GR-R01 [relayed]: REPASSADO de Gustavsson et al. (2011): estima-se que as PHL de grãos variem de 20% a 35% entre as diferentes regiões geográficas do mundo. NÃO é estimativa dos autores deste artigo.
- GR-R02 [relayed]: REPASSADO de Gustavsson et al. (2011): quase um terço da produção global de alimentos, em peso, é perdido. NÃO é estimativa dos autores deste artigo.
- GR-R03 [relayed]: REPASSADO de Kummu et al. (2012): cerca de um quarto da água, terra agricultável e fertilizante consumidos para produzir alimentos é desperdiçado.
- GR-R04 [relayed]: REPASSADO de Hodges et al. (2011): espera-se que a população mundial alcance 9 bilhões de pessoas até 2050, o que exigirá 70% mais alimentos.
- GR-R05 [relayed]: REPASSADO de Cardoen et al. (2015a) e Gustavsson et al. (2011): em países em desenvolvimento e em transição a perda nas etapas iniciais da cadeia supera o desperdício; em países desenvolvidos e industrializados ocorre o inverso.
- GR-R06 [relayed]: REPASSADO: a Tabela 1, que caracteriza as PHL por estágio de desenvolvimento tecnológico/econômico do país, é ADAPTADA de Parfitt et al. (2010) e Hodges et al. (2011), não construída pelos autores.
- GR-R07 [relayed]: REPASSADO: dados sobre PHL são escassos, antigos, majoritariamente pouco confiáveis e frequentemente não comparáveis — justificativa dos autores para recorrer a bases secundárias globais.
- GR-L01 [limitation]: Limitação: não existe variável de armazenagem de alimentos publicamente disponível em painel global; densidade de rodovias e de ferrovias foram usadas como PROXY da infraestrutura do país.
- GR-L02 [limitation]: Limitação de escopo: como PHL aqui NÃO inclui food waste (varejo e consumidor), variáveis explicativas de comportamento do consumidor não entraram no modelo, embora devessem entrar num modelo de desperdício.
- GR-L03 [limitation]: Limitação de generalização: culturas perecíveis como frutas e hortaliças têm requisitos de cadeia distintos dos grãos, de modo que as conclusões deste trabalho não podem ser extrapoladas diretamente para esse grupo.

## Itens desta parte (11)

### IRR-1b0c · artigo `airline` · DECIDIR: distortion
Título do citante: Price reactions to a rival’s market exit: evidence from the U.S. airline industry
Passagens (curated):
  > LCCs target markets for leisure travel, because leisure travelers are more price-sensitive than non-leisure travelers (Bendinelli et al., 2016).
Codificações:
  - c1 (original; leu o texto completo): presence=in_text depth=brief_mention stance=supporting accuracy=accurate distortion=None reuse=[] claim_ids=[]
  - c2 (Opus, cego): presence=in_text depth=brief_mention stance=supporting accuracy=imprecise distortion=transmutation reuse=[] claim_ids=['AIR-I02']
      razão: "LCCs target markets for leisure travel, because leisure travelers are more price-sensitive": conjectura do artigo sobre passageiros de lazer virada fato.
  - c3 (Sonnet, cego): presence=in_text depth=brief_mention stance=supporting accuracy=imprecise distortion=dead_end reuse=[] claim_ids=[]
      razão: 'LCCs target markets for leisure travel, because leisure travelers are more price-sensitive' — mesmo padrão de IRR-8dc2/IRR-b1f0.
Afirmações invocadas: AIR-I02 [interpretation]: Mecanismo CONJECTURADO, não testado: depeaking, com voos realocados para horários fora de pico em que a LCC é mais atrativa a passageiros de lazer, permitiria manter a internalização mesmo com queda da concentração aeroportuária.

### IRR-1eca · artigo `grains` · DECIDIR: accuracy
Título do citante: Path Analysis of Corn Kernel Physical Properties as Quality Indicators of Poultry Feed Ingredients
Passagens (auto):
  > through mediated relationships. Thus, improving corn kernel quality remains challenging at the farm level, particularly in areas such as harvest and postharvest mechanization, moisture management, and contamination control during storage. Corn batches are procured from smallholder farmers across multiple regions both within and beyond South Sulawesi Province, resulting in considerable variability in conditions and quality. In general, farmers rely on traditional farming practices, particularly in postharvest processes such as shelling, drying, and storage (Cecil et al., 2023). Suboptimal mechanization often results in increased damaged and broken kernels, which subsequently degrade quality (Bendinelli et al., 2020). Moreover, many farmers still rely on uncontrolled natural drying methods (Arslan & Alibaş, 2024), resulting in inconsistent moisture levels that increase the risk of mold gro
Codificações:
  - c1 (original; leu o texto completo): presence=in_text depth=brief_mention stance=supporting accuracy=accurate distortion=None reuse=[] claim_ids=[]
  - c2 (Opus, cego): presence=in_text depth=brief_mention stance=supporting accuracy=misrepresented distortion=dead_end reuse=[] claim_ids=[]
      razão: "Suboptimal mechanization often results in increased damaged and broken kernels": achado agronomico de qualidade que o artigo, macroeconometrico e de quantidade, nao contem.
  - c3 (Sonnet, cego): presence=in_text depth=brief_mention stance=supporting accuracy=imprecise distortion=dead_end reuse=[] claim_ids=[]
      razão: 'suboptimal mechanization often results in increased damaged and broken kernels' — mecanismo agronômico não coberto pelo artigo (macro, não micro).
Afirmações invocadas: —

### IRR-327a · artigo `airline` · DECIDIR: depth
Título do citante: The evaluation of the Balkan countries results relative to establishing effective market competition
Passagens (curated):
  > te, 1993; Lin et al., 2000; Gilbert, 2018), as well as in any other economic system such as Serbia (Begović & Mijatović, 2002; Begović & Pavić, 2010; Protić & Lazarević, 2015; Radivojević, 2018). Competition policy based on effective market competition eliminates the possibility of creating restrictive agreements, abuse of dominant position, and a merger between market participants that could have negative effects on competition. There are numerous empirical studies that examine the level of market competition in various industries worldwide. For example, Grzybowski (2008) and Whalley & Curwen (2012) explore market competition in the mobile telecommunications industry in European countries. Bendinelli, Bettini & Oliveira, (2016) and Oliveira & Oliveira (2018) analyse the level of market concentration and competition intensity in the airline industry. There is also a large body of similar
Codificações:
  - c1 (original; leu o texto completo): presence=in_text depth=drive_by stance=none accuracy=imprecise distortion=None reuse=[] claim_ids=[]
  - c2 (Opus, cego): presence=in_text depth=brief_mention stance=supporting accuracy=imprecise distortion=dead_end reuse=[] claim_ids=[]
      razão: 'analyse the level of market concentration and competition intensity' em artigo sobre politica de concorrencia nos Balcas; objeto deslocado, sem conteudo relevante.
  - c3 (Sonnet, cego): presence=in_text depth=real_mention stance=supporting accuracy=accurate distortion=None reuse=[] claim_ids=['AIR-M01']
      razão: Descreve corretamente o artigo como análise de concentração de mercado e intensidade de competição na indústria aérea.
Afirmações invocadas: AIR-M01 [original]: Arcabouço unificador: testa em um ÚNICO modelo econométrico a hipótese de internalização do congestionamento aeroportuário e a de relação competição-qualidade no mercado, dispensando a hipótese de simetria de rotas da literatura de internalização.

### IRR-4cc0 · artigo `grains` · DECIDIR: accuracy
Título do citante: Causes and Mitigation Strategies of Food Loss and Waste: A Systematic Literature Review and Framework Development
Passagens (curated):
  > Food loss and waste (FLW) sums one-third of the total food produced globally for human consumption, about 1.3 billion tons of food (Priefer et al., 2016; Bendinelli et al., 2020).
Codificações:
  - c1 (original; leu o texto completo): presence=in_text depth=drive_by stance=none accuracy=accurate distortion=None reuse=[] claim_ids=[]
  - c2 (Opus, cego): presence=in_text depth=brief_mention stance=supporting accuracy=imprecise distortion=relayed_attribution reuse=[] claim_ids=['GR-R02']
      razão: 'one-third of the total food produced globally... 1.3 billion tons' e estimativa de Gustavsson apenas repassada pelo artigo, aqui atribuida a ele.
  - c3 (Sonnet, cego): presence=in_text depth=brief_mention stance=supporting accuracy=misrepresented distortion=relayed_attribution reuse=[] claim_ids=['GR-R02']
      razão: Atribui 'one-third of total food' como achado do artigo; GR-R02 marca isso REPASSADO de Gustavsson et al. 2011.
Afirmações invocadas: GR-R02 [relayed]: REPASSADO de Gustavsson et al. (2011): quase um terço da produção global de alimentos, em peso, é perdido. NÃO é estimativa dos autores deste artigo.

### IRR-786d · artigo `grains` · DECIDIR: accuracy
Título do citante: Understanding the nexus of postharvest losses and food insecurity: Empirical evidence from Nigeria
Passagens (curated):
  > Educated farmers with more assets tend to use better storage and handling practices, which helps lower physical and economic losses (Debebe, 2022; Bendinelli et al., 2020; Kikulwe et al., 2018).
Codificações:
  - c1 (original; leu o texto completo): presence=in_text depth=brief_mention stance=supporting accuracy=accurate distortion=None reuse=[] claim_ids=[]
  - c2 (Opus, cego): presence=in_text depth=brief_mention stance=supporting accuracy=imprecise distortion=diversion reuse=[] claim_ids=['GR-F09']
      razão: "Educated farmers with more assets tend to use better storage": achado macro (renda, infraestrutura) transposto para comportamento do produtor individual.
  - c3 (Sonnet, cego): presence=in_text depth=brief_mention stance=supporting accuracy=misrepresented distortion=dead_end reuse=[] claim_ids=[]
      razão: Atribui achado sobre educação/ativos de agricultores e práticas de armazenagem, tema de nível domiciliar ausente do painel macro por país — dead_end.
Afirmações invocadas: GR-F09 [original]: Achado-síntese: há um TRADE-OFF difícil entre ampliar a oferta de alimentos e o nível de PHL — sem infraestrutura pós-colheita adequada, sobretudo armazenagem e comercialização, o esforço para aumentar a oferta eleva as PHL.

### IRR-87ab · artigo `grains` · DECIDIR: depth, accuracy
Título do citante: Food Waste Biorefineries: Developments, Current Advances and Future Outlook
Passagens (curated):
  (sem passagem: só na bibliografia)
Codificações:
  - c1 (original; leu o texto completo): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
  - c2 (Opus, cego): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
      razão: Sem passagem: corpo verificado sem mencao ao sobrenome; o artigo consta apenas na lista de referencias do citante.
  - c3 (Sonnet, cego): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
      razão: n_passages=0; corpo verificado sem menção, consta só na lista de referências.
Afirmações invocadas: —

### IRR-a050 · artigo `grains` · DECIDIR: depth, accuracy
Título do citante: Interaction of vehicles with the grain pre-treatment point
Passagens (curated):
  (sem passagem: só na bibliografia)
Codificações:
  - c1 (original; leu o texto completo): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
  - c2 (Opus, cego): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
      razão: Sem passagem: corpo verificado sem mencao ao sobrenome; o artigo consta apenas na lista de referencias do citante.
  - c3 (Sonnet, cego): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
      razão: n_passages=0; corpo verificado sem menção, consta só na lista de referências.
Afirmações invocadas: —

### IRR-b1f0 · artigo `airline` · DECIDIR: distortion
Título do citante: Credible vs. deceptive threat of market entry: Empirical evidence from the US airline industry
Passagens (curated):
  > MarketType. LCCs typically focus on markets with a high proportion of leisure passengers because this segment of the market is more price-sensitive than business travelers (Bendinelli, Bettini, & Oliveira, 2016). To determine whether a given market is a leisure market, we used Gerardi and Shapiro (2009) list of leisure destinations in the US.
Codificações:
  - c1 (original; leu o texto completo): presence=in_text depth=supporting stance=supporting accuracy=accurate distortion=None reuse=['method_adoption'] claim_ids=[]
  - c2 (Opus, cego): presence=in_text depth=brief_mention stance=supporting accuracy=imprecise distortion=transmutation reuse=[] claim_ids=['AIR-I02']
      razão: "LCCs typically focus on markets with a high proportion of leisure passengers": conjectura sobre atratividade da LCC para lazer apresentada como fato estabelecido.
  - c3 (Sonnet, cego): presence=in_text depth=brief_mention stance=supporting accuracy=imprecise distortion=dead_end reuse=[] claim_ids=[]
      razão: 'LCCs typically focus on markets with a high proportion of leisure passengers' — mesmo padrão de IRR-8dc2; tema fora do registro.
Afirmações invocadas: AIR-I02 [interpretation]: Mecanismo CONJECTURADO, não testado: depeaking, com voos realocados para horários fora de pico em que a LCC é mais atrativa a passageiros de lazer, permitiria manter a internalização mesmo com queda da concentração aeroportuária.

### IRR-cc5f · artigo `airline` · DECIDIR: accuracy
Título do citante: Modelo de identificação do impacto futuro de chuvas extremas nos atrasos/cancelamentos de voos
Passagens (curated):
  > exas e difı́ceis de serem mensuradas e gerenciadas, como eventos de situaçõ es meteoroló gicas extremas. Entre esses eventos, ı́ndices pluviomé tricos oscilantes podem ser considerados como de alto impacto nas operaçõ es de transporte aé reo. Estudos sobre eventos meteoroló gicos impactantes na aviaçã o, como incidê ncias de tempestades formadoras de rajadas de vento, podem ser identi icados em Metchko e Monteiro (2014), bem como estudos sobre ocorrê ncia de cancelamentos de voos devido à chuva extrema, como em Koetse e Rietveld (2009). Alé m desses, há també m estudos que buscam mensurar os impactos dos atrasos dos voos nos custos e na dinâ mica do transporte aé reo, como em Bendinelli, Bettini e Oliveira (2016), que consideram em suas aná lises, entre outras, variá veis relacionadas à proporçã o de atrasos de voos devido ao mau tempo. Já em Santos e Robin (2010), em
Codificações:
  - c1 (original; leu o texto completo): presence=in_text depth=real_mention stance=supporting accuracy=accurate distortion=None reuse=[] claim_ids=[]
  - c2 (Opus, cego): presence=in_text depth=brief_mention stance=contradictory accuracy=misrepresented distortion=diversion reuse=[] claim_ids=['AIR-D02']
      razão: Objeto errado: 'mensurar os impactos dos atrasos dos voos nos custos'; e contrapoe: 'tais estudos nao consideram as situacoes climaticas'.
  - c3 (Sonnet, cego): presence=in_text depth=brief_mention stance=supporting accuracy=imprecise distortion=diversion reuse=[] claim_ids=[]
      razão: Atribui variável sobre 'atrasos devido ao mau tempo' ao artigo; não consta no registro de afirmações — leitura não confirmável.
Afirmações invocadas: AIR-D02 [original]: Fonte primária: o relatório Voo Regular Ativo (VRA) da ANAC, base online com dados no nível do voo — empresa, par-de-aeroportos, número do voo e horários programados e efetivos — desde 2000, com código de justificativa de cada atraso.

### IRR-e1b7 · artigo `grains` · DECIDIR: depth, accuracy
Título do citante: The Role of Biotechnology in Climate Change Adaptation and Postharvest Loss Mitigation in Blueberries
Passagens (curated):
  (sem passagem: só na bibliografia)
Codificações:
  - c1 (original; leu o texto completo): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
  - c2 (Opus, cego): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
      razão: Sem passagens; corpo verificado nao menciona o artigo, que consta apenas na lista de referencias.
  - c3 (Sonnet, cego): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
      razão: n_passages=0; corpo verificado sem menção no texto; consta só na lista de referências.
Afirmações invocadas: —

### IRR-f08a · artigo `airline` · DECIDIR: depth
Título do citante: Can airfares tell? An alternative empirical strategy for airport congestion internalization
Passagens (curated):
  > To conciliate these two strands of literature, Bendinelli et al. (2016) differentiate the market concentrations at the market level and at the airport level. They propose that airport concentration is more relevant to airport congestion self-internalization while market concentration is more relevant to the competition in the quality aspect of delay.
Codificações:
  - c1 (original; leu o texto completo): presence=in_text depth=foundational stance=supporting accuracy=accurate distortion=None reuse=[] claim_ids=[]
  - c2 (Opus, cego): presence=in_text depth=real_mention stance=supporting accuracy=accurate distortion=None reuse=[] claim_ids=['AIR-M01', 'AIR-M02', 'AIR-F01', 'AIR-F02']
      razão: "differentiate the market concentrations at the market level and at the airport level": descreve o arcabouco unificador e os dois achados com conteudo real.
  - c3 (Sonnet, cego): presence=in_text depth=supporting stance=supporting accuracy=accurate distortion=None reuse=[] claim_ids=['AIR-M01', 'AIR-M02']
      razão: 'differentiate the market concentrations at market level and airport level' — descreve a distinção metodológica central, usada para conciliar duas correntes.
Afirmações invocadas: AIR-F01 [original]: Achado 1: a concentração no nível do AEROPORTO/CIDADE REDUZ os atrasos. O coeficiente de HHI max endpoint cities é negativo e significante em todas as especificações de ODDS e MINS — evidência de internalização do congestionamento (H1).; AIR-F02 [original]: Achado 2: a concentração no nível da ROTA/MERCADO AUMENTA os atrasos. O coeficiente de HHI city-pair é positivo e significante ao menos a 5% em todos os casos — evidência da relação competição-qualidade (H2).; AIR-M01 [original]: Arcabouço unificador: testa em um ÚNICO modelo econométrico a hipótese de internalização do congestionamento aeroportuário e a de relação competição-qualidade no mercado, dispensando a hipótese de simetria de rotas da literatura de internalização.; AIR-M02 [original]: O modelo não impõe a hipótese de simetria de rotas e admite internalização de congestionamento EM PARALELO à gestão de qualidade de serviço, o que permite pôr concentração de rota e de cidade na mesma equação.