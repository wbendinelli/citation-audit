// Figuras desenhadas no próprio Typst, com os tokens do sapians.
//
// Mesma linguagem de reports/01-metodos-locais/figuras.typ
// (interpretable-ml-lectures): _caixa, _seta, barreira tracejada
// terracota, grids; 7.6 / 6.9 / 6.2 pt de texto, 0.7 / 0.4 pt de traço,
// 2pt de raio.
//
// Regra: nenhum dígito dentro dos desenhos. A figura ensina o mecanismo;
// os números vivem na prosa (reports/01-impacto/numeros.typ), onde a
// nota de rodapé os alcança.

#import "@preview/sapians:0.3.2": *

#let _caixa(titulo, corpo, destaque: false) = block(
  width: 100%,
  fill: if destaque { sapians-card-bg } else { sapians-paper },
  stroke: (
    paint: if destaque { sapians-terracotta } else { sapians-line },
    thickness: if destaque { 0.7pt } else { 0.4pt },
  ),
  radius: 2pt,
  inset: (x: 2.6mm, y: 2.2mm),
)[
  #text(size: 7.6pt, weight: "bold", fill: if destaque { sapians-terracotta } else { sapians-text-dark })[#titulo]
  #if corpo != none [
    #v(0.9mm)
    #text(size: 6.9pt, fill: sapians-muted-dark)[#corpo]
  ]
]

#let _seta(rotulo) = align(center)[
  #v(3.5mm)
  #text(size: 6.2pt, fill: sapians-muted-dark)[#rotulo]
  #v(-1.2mm)
  #text(size: 12pt, fill: sapians-terracotta)[→]
]

// ---------------------------------------------------------------------------
// fig-taxonomia — três eixos independentes, um por linha. Um eixo não
// implica o outro: uma citação recebe um valor em cada um dos três, mais
// a flag de acurácia (à parte, não é um quarto nível de profundidade).
// ---------------------------------------------------------------------------

#let _degrau(rotulo) = block(
  width: 100%,
  fill: sapians-paper,
  stroke: (paint: sapians-line, thickness: 0.4pt),
  radius: 2pt,
  inset: (x: 1.6mm, y: 1.4mm),
)[
  #align(center)[#text(size: 6.2pt, fill: sapians-text-dark)[#rotulo]]
]

#let _escada(..rotulos) = grid(
  columns: (1fr,) * rotulos.pos().len(),
  column-gutter: 0.8mm,
  ..rotulos.pos().map(_degrau)
)

#let _ancora(corpo) = block(
  width: 100%,
  fill: sapians-card-bg,
  stroke: (paint: sapians-line, thickness: 0.4pt),
  radius: 2pt,
  inset: (x: 2.2mm, y: 2mm),
)[
  #text(size: 6.2pt, fill: sapians-muted-dark)[#corpo]
]

#let _eixo(pergunta, escada, ancora-txt) = grid(
  columns: (28mm, 1fr, 34mm),
  column-gutter: 3mm,
  align: horizon,
  _caixa(pergunta, none, destaque: true),
  escada,
  _ancora(ancora-txt),
)

#let fig-taxonomia() = block(width: 100%, breakable: false)[
  #_eixo(
    [Quanto o artigo importou?],
    _escada(
      [só na bibliografia], [de passagem], [menção breve],
      [menção real], [sustenta], [fundacional],
    ),
    [Moravcsik: orgânica/perfunctória; Valenzuela: importante/incidental],
  )
  #v(1.4mm)
  #grid(
    columns: (28mm, 1fr, 34mm),
    column-gutter: 3mm,
    [],
    align(center)[
      #line(length: 55%, stroke: (paint: sapians-terracotta, thickness: 0.9pt, dash: "dashed"))
      #v(1.2mm)
      #box(width: 32%)[#_degrau([interpretado errado])]
      #v(0.6mm)
      #text(size: 6.2pt, fill: sapians-terracotta, style: "italic")[eixo à parte: acurácia, não profundidade]
    ],
    [],
  )
  #v(3.4mm)

  #_eixo(
    [De que lado o citante se pôs?],
    _escada([apoia], [neutra], [contrapõe]),
    [Moravcsik: confirmativa/negacional; Catalini],
  )
  #v(3.4mm)

  #_eixo(
    [O que ele reusou?],
    [
      #_escada(
        [adota método], [valida resultado], [reusa dado],
        [benchmark], [estende],
      )
      #v(0.8mm)
      #align(center)[#text(size: 6.2pt, fill: sapians-muted-dark, style: "italic")[várias por citação]]
    ],
    [CiTO: usesMethodIn, extends; Greenberg: distorções],
  )

  #v(2.2mm)
  #align(center)[
    #text(size: 6.2pt, fill: sapians-muted-dark)[
      cada citação recebe um valor em cada eixo; um eixo não implica o outro
    ]
  ]
]

// ---------------------------------------------------------------------------
// fig-portoes — cinco estações, três barreiras. Uma barreira não descarta
// o registro: reclassifica o status e o devolve para a próxima etapa do
// pipeline poder reler.
// ---------------------------------------------------------------------------

#let _estacao(titulo, corpo) = _caixa(titulo, corpo)

// motivo/destino chegam com quebras de linha manuais (\ ) já decididas no
// ponto de chamada: numa coluna de 25mm a 6.2pt o auto-wrap do Typst nem
// sempre acha o mesmo ponto de quebra que caberia no desenho, então quem
// decide onde quebrar é quem escreve a legenda, não o layout automático.
#let _rejeicao(motivo, destino) = block(width: 100%)[
  #set align(center)
  #set par(justify: false, leading: 0.45em)
  #text(size: 6.2pt, fill: sapians-terracotta)[#motivo]
  #linebreak()
  #text(size: 5.6pt, fill: sapians-muted-dark, font: font-mono)[→ #destino]
]

#let _barreira(motivo, destino) = block(width: 100%)[
  #align(center)[
    #line(length: 11mm, angle: 90deg, stroke: (paint: sapians-terracotta, thickness: 1.1pt, dash: "dashed"))
  ]
  #v(1.4mm)
  #_rejeicao(motivo, destino)
]

#let fig-portoes() = block(width: 100%, breakable: false)[
  #grid(
    columns: (1fr, 8mm, 1fr, 25mm, 1fr, 25mm, 1fr, 25mm, 1fr),
    align: top,
    _estacao(
      [registro no grafo],
      [O par citante-citado entra no inventário, unido de múltiplas fontes.],
    ),
    _seta[],
    _estacao(
      [texto obtido],
      [O texto integral é baixado ou extraído por uma rota de acesso aberto.],
    ),
    _barreira([título ausente \ do texto], [texto\_incorreto]),
    _estacao(
      [passagem localizada],
      [A menção ao artigo é encontrada dentro do corpo do texto.],
    ),
    _barreira([página de rosto \ sem corpo], [texto\_parcial]),
    _estacao(
      [classificação com passagem literal],
      [A citação recebe papel, postura e reuso com o trecho exato em mãos.],
    ),
    _barreira([só na bibliografia \ sem corpo comprovado], [evidencia\_ \ insuficiente]),
    [
      #_estacao(
        [proveniência: hash, data, codebook],
        [Cada classificação carrega a evidência que a sustenta.],
      )
      #v(1.4mm)
      #align(center)[
        #text(size: 6.2pt, fill: sapians-muted-dark, style: "italic")[
          aresta falsa: corpo verificado, nenhuma menção — veredito terminal
        ]
      ]
    ],
  )
]

// ---------------------------------------------------------------------------
// fig-cd — o índice de disrupção lido como grafo: quem vem depois do
// artigo cita os antecessores dele, o próprio artigo, ou os dois.
// ---------------------------------------------------------------------------

#let _no-central(rotulo) = block(
  width: 100%,
  fill: sapians-card-bg,
  stroke: (paint: sapians-terracotta, thickness: 0.7pt),
  radius: 2pt,
  inset: (x: 2.6mm, y: 2.2mm),
)[
  #align(center)[#text(size: 7.6pt, weight: "bold", fill: sapians-terracotta)[#rotulo]]
]

#let _card-pequeno(rotulo, letra) = block(
  width: 100%,
  fill: sapians-paper,
  stroke: (paint: sapians-line, thickness: 0.4pt),
  radius: 2pt,
  inset: (x: 2.2mm, y: 1.8mm),
)[
  #text(size: 6.9pt, fill: sapians-text-dark)[#rotulo]
  #h(1fr)
  #text(size: 7.6pt, weight: "bold", fill: sapians-terracotta)[(#letra)]
]

#let _liga(ativa) = align(center + horizon)[
  #if ativa [
    #text(size: 11pt, fill: sapians-terracotta)[←]
  ] else [
    #text(size: 11pt, fill: sapians-line)[·]
  ]
]

#let fig-cd() = block(width: 100%, breakable: false)[
  #grid(
    columns: (1fr, 8mm, 1fr, 8mm, 1.15fr),
    row-gutter: 2.6mm,
    column-gutter: 1.4mm,
    grid.cell(rowspan: 3, align: horizon)[
      #_caixa([antecessores], [as referências do artigo])
    ],
    _liga(false),
    grid.cell(rowspan: 3, align: horizon)[#_no-central([o artigo])],
    _liga(true),
    _card-pequeno([cita o artigo, não os antecessores], "i"),

    _liga(true),
    _liga(true),
    _card-pequeno([cita o artigo e os antecessores], "j"),

    _liga(true),
    _liga(false),
    _card-pequeno([cita os antecessores, não o artigo], "k"),
  )
  #v(2.4mm)
  #align(center)[
    #text(size: 6.2pt, fill: sapians-muted-dark)[
      CD = (i − j) / (i + j + k) · CD sem k ignora os antecessores solitários ·
      DI cinco exige cinco referências em comum
    ]
  ]
]
