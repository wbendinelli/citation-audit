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

## Itens desta parte (10)

### IRR-1b78 · artigo `airline` · DECIDIR: depth
Título do citante: Airport slots and the internalization of congestion by airlines: An empirical model of integrated flight disruption management in Brazil
Passagens (curated):
  > We extend the literature on the congestion internalization behaviors of major airlines to examine the possible impact of airport slots (Daniel, 1995, Brueckner, 2002, Mayer and Sinai, 2003a, Santos and Robin, 2010, Ater, 2012, Bendinelli et al., 2016).
Codificações:
  - c1 (original; leu o texto completo): presence=in_text depth=supporting stance=supporting accuracy=accurate distortion=None reuse=['work_extended'] claim_ids=[]
  - c2 (Opus, cego): presence=in_text depth=drive_by stance=supporting accuracy=accurate distortion=None reuse=[] claim_ids=['AIR-F01']
      razão: "We extend the literature on the congestion internalization behaviors": bloco de seis, estende a linha e nao o artigo; sem contraste explicito.
  - c3 (Sonnet, cego): presence=in_text depth=brief_mention stance=supporting accuracy=accurate distortion=None reuse=[] claim_ids=['AIR-F01']
      razão: Bloco de 6 citações que declara 'estender a literatura' sobre internalização de congestionamento; tema central do artigo, mas sem adoção específica.
Afirmações invocadas: AIR-F01 [original]: Achado 1: a concentração no nível do AEROPORTO/CIDADE REDUZ os atrasos. O coeficiente de HHI max endpoint cities é negativo e significante em todas as especificações de ODDS e MINS — evidência de internalização do congestionamento (H1).

### IRR-29fd · artigo `grains` · DECIDIR: depth, accuracy
Título do citante: Enhancing Food Security, Safety, and Sustainability via the Application of Radiation Technology
Passagens (curated):
  (sem passagem: só na bibliografia)
Codificações:
  - c1 (original; leu o texto completo): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
  - c2 (Opus, cego): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
      razão: Sem passagens; corpo verificado sem mencao ao sobrenome, artigo so na bibliografia.
  - c3 (Sonnet, cego): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
      razão: n_passages=0; sem menção no corpo verificado; só na lista de referências.
Afirmações invocadas: —

### IRR-357b · artigo `airline` · DECIDIR: depth
Título do citante: An econometric analysis for the determinants of flight speed in the air transport of passengers
Passagens (auto):
  > For example, Mcconnachie et al.17, observed a reduction in mean speeds concomitantly with increases in fuel prices. • Flight delay management: refers to identifying, assessing, and mitigating delays in flight operations. A delayed flight can cause a cascading effect on the entire schedule of a carrier and disrupt the plans of many passengers and airports, besides other airlines. Flight delay management is therefore a critical function of flight operations. One of the strategies of flight delay management is flight schedule recovery, which can include adjusting the flight schedules and speeds, besides rerouting flights to minimize the impact of delays. Prince and ­Simon4, Kang and ­Hansen3, Bendinelli et al.28, Eufrásio et al.23, and Calzada and ­Fageda29, among many others, investigate the association between market competition and airlines’ concern with punctuality. • Airport operations
Codificações:
  - c1 (original; leu o texto completo): presence=in_text depth=real_mention stance=supporting accuracy=accurate distortion=None reuse=[] claim_ids=[]
  - c2 (Opus, cego): presence=in_text depth=drive_by stance=supporting accuracy=accurate distortion=None reuse=[] claim_ids=['AIR-M01']
      razão: Bloco com cinco autores "among many others, investigate the association between market competition and airlines' concern with punctuality": objeto correto, atribuicao generica.
  - c3 (Sonnet, cego): presence=in_text depth=brief_mention stance=supporting accuracy=accurate distortion=None reuse=[] claim_ids=['AIR-M01', 'AIR-F02']
      razão: Bloco numérico de 5 citações descrevendo tema comum — associação entre competição de mercado e pontualidade — corresponde ao objeto central do artigo.
Afirmações invocadas: AIR-F02 [original]: Achado 2: a concentração no nível da ROTA/MERCADO AUMENTA os atrasos. O coeficiente de HHI city-pair é positivo e significante ao menos a 5% em todos os casos — evidência da relação competição-qualidade (H2).; AIR-M01 [original]: Arcabouço unificador: testa em um ÚNICO modelo econométrico a hipótese de internalização do congestionamento aeroportuário e a de relação competição-qualidade no mercado, dispensando a hipótese de simetria de rotas da literatura de internalização.

### IRR-6cdf · artigo `grains` · DECIDIR: depth, accuracy
Título do citante: Analysis of the Factors Influencing the Stability of Stored Grains: Implications for Agricultural Sustainability and Food Security
Passagens (curated):
  (sem passagem: só na bibliografia)
Codificações:
  - c1 (original; leu o texto completo): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
  - c2 (Opus, cego): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
      razão: Item sem passagem (n_passages = 0): corpo completo verificado, artigo consta apenas na lista de referencias.
  - c3 (Sonnet, cego): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
      razão: n_passages=0: corpo verificado sem menção ao sobrenome — reference_list_only, conforme regra do pacote.
Afirmações invocadas: —

### IRR-81e6 · artigo `grains` · DECIDIR: accuracy
Título do citante: TESTING THE EFFECT OF HERBAL POWDERS ON GRAIN PARAMETERS IN STORED WHEAT IN THE PRESENCE OF SITOPHILUS ORYZAE UNDER FREE CHOICE
Passagens (auto):
  > the insects that infest grains that have been stored, and the genera Sitophilus and Tribolium are the most destructive species of storage insects (Khan and Selman 1988). The rice weevil, Sitophilus oryzae (L.), is one of the most destructive pests of cereal grains and their products. (Yan et al., 2014; Rita Devi et al., 2017). It is a major pest that feeds on whole grain kernels. Significant loss in grain weight, secondary pest infestation, and contamination due to growth of fungus are all results of adult feeding and larval activity inside kernels (Athanassiou et al., 2017). Grain production in many developing nations mainly depends on Small-scale farmers and postharvest processing mills (Bendinelli et al., 2020). When grains are stored, synthetic insecticides are used to control rice weevil pest. Chemical insecticides and fumigants were frequently used to treat insect storage pests, bu
Codificações:
  - c1 (original; leu o texto completo): presence=in_text depth=drive_by stance=supporting accuracy=accurate distortion=None reuse=[] claim_ids=[]
  - c2 (Opus, cego): presence=in_text depth=brief_mention stance=supporting accuracy=misrepresented distortion=dead_end reuse=[] claim_ids=[]
      razão: 'Grain production in many developing nations mainly depends on Small-scale farmers and postharvest processing mills': painel macro global nada afirma sobre porte de produtor.
  - c3 (Sonnet, cego): presence=in_text depth=drive_by stance=supporting accuracy=imprecise distortion=diversion reuse=[] claim_ids=[]
      razão: Afirmação genérica sobre pequenos produtores e moinhos; não corresponde a achado específico do painel macro do artigo.
Afirmações invocadas: —

### IRR-8cba · artigo `airline` · DECIDIR: depth, accuracy
Título do citante: An early assessment of the impact of COVID-19 on air transport: Just another crisis or the end of aviation as we know it?
Passagens (curated):
  (sem passagem: só na bibliografia)
Codificações:
  - c1 (original; leu o texto completo): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
  - c2 (Opus, cego): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
      razão: Item sem passagem (n_passages = 0): corpo completo verificado, mencao apenas na lista de referencias.
  - c3 (Sonnet, cego): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
      razão: n_passages=0: corpo verificado sem menção ao sobrenome — reference_list_only, conforme regra do pacote.
Afirmações invocadas: —

### IRR-a1e3 · artigo `grains` · DECIDIR: accuracy
Título do citante: Design of a Cooling System Integrated with Ultraviolet Light for Preservation of Fruits and Vegetables at Variable Tropical Weather Conditions: A Case Study of Arusha, Tanzania
Passagens (auto):
  > onditions (Gall and Benkeblia 2022, Freimoser et al. (Arah et al. 2016, Dhakulkar et al. 2018, 2019, Pétriacq et al. 2018). The challenge in Sibomana et al. 2016). Perishability of fruits minimizing fruits and vegetables post-harvest and vegetables is directly linked to rapid losses is largely hinged on how to come up quality losses immediately after harvest when with reliable and sustainable storage systems subjected to poor handling and storage for perishable produce at the minimum initial 741 http://tjs.udsm.ac.tz/index.php/tjs www.ajol.info/index.php/tjs/ Gunda et al. - Design of a Cooling System Integrated with Ultraviolet Light for Preservation and running costs (Ambuko et al. 2017, Bendinelli et al. 2020, Bustos and Moors 2018). Evaporative cooling systems are one of the options for horticultural post-harvest storage because of their environmental friendliness and energy-saving fe
Codificações:
  - c1 (original; leu o texto completo): presence=in_text depth=drive_by stance=none accuracy=accurate distortion=None reuse=[] claim_ids=[]
  - c2 (Opus, cego): presence=in_text depth=drive_by stance=none accuracy=imprecise distortion=dead_end reuse=[] claim_ids=['GR-P01']
      razão: Bloco de tres fontes sobre armazenagem de frutas e hortalicas; o artigo trata de graos e veda extrapolacao a periveis (GR-L03).
  - c3 (Sonnet, cego): presence=in_text depth=drive_by stance=none accuracy=misrepresented distortion=dead_end reuse=[] claim_ids=[]
      razão: Cita artigo sobre grãos em bloco genérico sobre armazenagem de frutas/hortaliças; o próprio artigo (GR-L03) diz não extrapolar a perecíveis.
Afirmações invocadas: GR-P01 [original]: Política: esforços para aumentar a produção de alimentos não podem se restringir à produção na fazenda, pois geram excedente e PHL muito maiores; devem ser complementados por investimentos em infraestrutura pós-colheita, em especial armazenagem e comercialização.

### IRR-c162 · artigo `airline` · DECIDIR: depth, accuracy
Título do citante: Dynamic pricing and market segmentation responses to low-cost carrier entry
Passagens (curated):
  (sem passagem: só na bibliografia)
Codificações:
  - c1 (original; leu o texto completo): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
  - c2 (Opus, cego): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
      razão: Sem passagens; corpo verificado sem mencao ao sobrenome, artigo so na bibliografia.
  - c3 (Sonnet, cego): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
      razão: n_passages=0; sem menção no corpo verificado; só na lista de referências.
Afirmações invocadas: —

### IRR-cc69 · artigo `airline` · DECIDIR: distortion
Título do citante: Impact of COVID-19 on Airlines’ Financial Performance and Innovation Strategy
Passagens (auto):
  > 019 is 64.6% of global passenger traffic. In addition, the AsiaPacific region has a loss of 2,148 million passengers, representing a decrease of 61.3% from all regions. The International Civil Aviation Organization (ICAO) (2021) reported that during the COVID-19 outbreak, the number of worldwide passengers decreased by 60% in 2020, 49% in 2021, and 27% to 32% in 2022 compared with the year 2019. Moreover, the Airports Council International World (ACI) (2021) said that airlines’ revenue dropped by around $380 billion compared to 2019. Due to the pandemic, travel restrictions grounded global aircraft by 64% in April 2020. Several studies have focused on factors impacting the airline industry. Bendinelli et al. (2016), Kalemba and Campa-Planas (2019), Fardnia et al. (2021), Chang et al. (2018) examine the relationship between accident records or safety and financial performance. Kiracı (201
Codificações:
  - c1 (original; leu o texto completo): presence=in_text depth=brief_mention stance=supporting accuracy=misrepresented distortion=None reuse=[] claim_ids=[]
  - c2 (Opus, cego): presence=in_text depth=brief_mention stance=supporting accuracy=misrepresented distortion=diversion reuse=[] claim_ids=[]
      razão: 'examine the relationship between accident records or safety and financial performance': o artigo nao trata de seguranca nem de desempenho financeiro.
  - c3 (Sonnet, cego): presence=in_text depth=brief_mention stance=supporting accuracy=misrepresented distortion=dead_end reuse=[] claim_ids=[]
      razão: Agrupa o artigo entre estudos sobre 'accident records or safety and financial performance'; tema real é atraso/concentração — dead_end.
Afirmações invocadas: —

### IRR-ed51 · artigo `grains` · DECIDIR: depth, accuracy, presence
Título do citante: Modeling and Control of an Indirect Solar Dryer in Forced Convection Mode Using System Identification and Model Predictive Control
Passagens (auto):
  > mplementation process HUMAN AND ANIMAL RIGHTS 6. CONCLUSION In conclusion, the proposed system successfully demonstrated the superior efficiency of an indirect solar dryer with forced convection mode, substantiated by compelling numerical results. The comparative assessment of three No violation of Human and Animal Rights is involved. FUNDING No funding is involved in this work. Rafiq et al.: Modeling and Control of an Indirect Solar Dryer in Forced Convection Mode Using System Identification and Model Predictive Control 827 DATA AVAILABILITY STATEMENT Data sharing not applicable to this article as no datasets were generated or analyzed during the current study. REFERENCES 0[1] W. E. Bendinelli, C. T. Su, T. G. P�era, and J. V. Caixeta Filho, “What are the main factors that determine post-harvest losses of grains,” Sustain. Prod. Consump., vol. 21, pp. 228–238, 2020. DOI: 10.1016/j.spc.2
Codificações:
  - c1 (original; leu o texto completo): presence=in_text depth=real_mention stance=supporting accuracy=accurate distortion=None reuse=[] claim_ids=[]
  - c2 (Opus, cego): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
      razão: Passagem e a propria lista bibliografica ("REFERENCES 0[1]... 0[2]... 0[3]"), entradas em sequencia; sem mencao no corpo.
  - c3 (Sonnet, cego): presence=reference_list_only depth=None stance=none accuracy=None distortion=None reuse=[] claim_ids=[]
      razão: Passagem é lista de referências numerada ('[1]...[2]...[3]...'), sem menção no corpo do texto; reference_list_only apesar de n_passages=1.
Afirmações invocadas: —