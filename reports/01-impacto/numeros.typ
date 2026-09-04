// numeros.typ — a ponte entre os dados gerados e a prosa do relatório.
//
// `D` é o único ponto de entrada de número no documento: toda cifra citada
// em reports/01-impacto/main.typ lê daqui, nunca digitada à mão — é o que
// tools/check_numbers.py confere (reports/01-impacto/numeros.txt é a
// versão-texto da mesma fonte, gerada pelo mesmo pipeline, para o checador
// não precisar avaliar Typst). Junto de D moram os três blocos de
// composição que main.typ importa: o par de show-rules de título/legenda
// copiado verbatim de reports/01-metodos-locais/main.typ
// (interpretable-ml-lectures), o cartão de resumo (sapians-report não tem
// slot de abstract) e o wrapper de tabela numerada.
//
// Uso em main.typ:
//   #import "@preview/sapians:0.3.2": *
//   #import "numeros.typ": *
//   #show: sapians-report.with(title: ..., author: ..., date: ..., lang: "pt")
//   #show: estilo-numeros
//   #resumo[...]
//   #tabela([legenda], "tab-funil", columns: (auto, 1fr), [a], [b], fonte: [...])
//
// #show DENTRO de um módulo só vale para o conteúdo QUE O PRÓPRIO MÓDULO
// produz — `#import "numeros.typ": *` não propaga um #show de nível
// superior para quem importa (testado: um #show heading solto neste
// arquivo não pega os headings de main.typ). Por isso as duas show-rules
// de main.typ (legenda, H1, H2) vão dentro de estilo-numeros(body), uma
// função que main.typ aplica com #show: — o mesmo padrão de
// sapians-report.with(...), não um efeito colateral de import.

#import "@preview/sapians:0.3.2": *

// Caminho repo-root-absoluto: resolve com `typst compile --root .` a
// partir da raiz do repositório (o mesmo padrão de
// image("/reports/01-metodos-locais/figuras/...") em
// reports/01-metodos-locais/main.typ). dados.json ainda não existe no
// repositório — é gerado por uma etapa do pipeline (tools/audit_NN_*.py)
// ainda não escrita; até lá, este import falha ao compilar main.typ, o
// que é o comportamento certo: sem dados.json não há número para citar.
//
// Teste de stage (sem raiz de repositório git): main_test.typ, em vez de
// importar main.typ de verdade, importa este arquivo e sobrescreve D
// depois — ver a nota em main_test.typ. dados.json de fixture mora em
// reports/01-impacto/dados.json, um caminho RELATIVO a partir daqui só
// para o smoke test compilar fora do repositório real.
#let D = json("/reports/01-impacto/dados.json")

// ---------------------------------------------------------------------------
// sp-tab — copiado verbatim de reports/01-metodos-locais/main.typ
// (interpretable-ml-lectures), linhas ~75-90. Booktabs: filete grosso no
// topo e no pé, fino sob o cabeçalho, nada mais — sem linha vertical e sem
// malha, como em IEEE, Elsevier e ACM.
// ---------------------------------------------------------------------------

#let sp-tab(fonte: none, ..args) = block(width: 100%, above: 2.6mm, below: 3mm, breakable: false)[
  #set text(size: 7.4pt)
  #set par(leading: 0.55em)
  #block(stroke: (top: 0.9pt + sapians-text-dark, bottom: 0.9pt + sapians-text-dark))[
    #table(
      stroke: (x, y) => (top: if y == 1 { 0.4pt + sapians-muted-dark } else { 0pt }),
      fill: none,
      inset: (x: 2.2mm, y: 1.5mm),
      align: left,
      ..args
    )
  ]
  #if fonte != none [#v(1mm) #text(size: 6.6pt, fill: sapians-muted-dark)[Fonte: #fonte]]
]

// ---------------------------------------------------------------------------
// estilo-numeros — as duas show-rules de reports/01-metodos-locais/main.typ,
// linhas ~53-73: legenda no padrão de periódico (menor que o corpo,
// alinhada à esquerda, rótulo em negrito) e a hierarquia de títulos (H1
// nunca menor que o corpo, H2 marcado em terracota). Empacotadas numa
// função — não soltas no módulo — porque #show de módulo importado não
// alcança quem importa (ver nota no topo do arquivo).
// ---------------------------------------------------------------------------

#let estilo-numeros(body) = {
  show figure.caption: it => block(width: 100%, above: 1.8mm)[
    #set text(size: 7.6pt, fill: sapians-muted-dark)
    #set par(justify: true, leading: 0.56em)
    #align(left)[
      #text(weight: "bold", fill: sapians-text-dark)[#it.supplement #context it.counter.display(it.numbering).]
      #h(0.5mm)#it.body
    ]
  ]
  show heading.where(level: 1): it => [
    #v(3.2mm)
    #text(size: 10.5pt, weight: "bold", fill: sapians-text-dark)[#it.body]
    #v(1.4mm)
  ]
  show heading.where(level: 2): it => [
    #v(2.4mm)
    #text(size: 9.2pt, weight: "bold", fill: sapians-terracotta)[#it.body]
    #v(0.9mm)
  ]
  body
}

// ---------------------------------------------------------------------------
// resumo — o cartão de abstract que sapians-report não tem (o layout
// report.typ vai direto de kicker+título para o corpo; ver
// packages/preview/sapians/0.3.2/src/layouts/report.typ, sem parâmetro
// abstract). Um bloco só, logo depois do #show: sapians-report.with(...).
// ---------------------------------------------------------------------------

#let resumo(body) = block(
  width: 100%,
  fill: sapians-card-bg,
  radius: radius-sm,
  stroke: stroke-light,
  inset: 3.5mm,
)[
  #text(size: 8pt, weight: "bold", fill: sapians-text-dark)[Resumo]
  #v(1mm)
  #text(size: 7.8pt, fill: sapians-muted-dark)[#body]
]

// ---------------------------------------------------------------------------
// tabela — sp-tab dentro de #figure(kind: table), para a tabela entrar na
// contagem "Tabela N" e aceitar @rotulo. `label` é uma string (ex.
// "tab-funil"); o label do Typst se anexa ao figure adjacente no mesmo
// bloco de conteúdo — não dá para "somar" content + label diretamente
// (testado: content + label(...) é erro de tipo em Typst 0.15).
// ---------------------------------------------------------------------------

#let tabela(caption, lbl, columns, ..cells, fonte: none) = [
  #figure(
    kind: table,
    supplement: [Tabela],
    caption: caption,
    sp-tab(columns: columns, ..cells, fonte: fonte),
  )#label(lbl)
]
