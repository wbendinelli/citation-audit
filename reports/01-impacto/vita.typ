// Composição editorial local: tokens neutros do design global VITA.
// Inter OFL é a alternativa portátil à Optimistic VF, sem redistribuir a fonte comercial.
#let V = json("/tools/vita_tokens.json").palette
#let sapians-text-dark = rgb(V.ink)
#let sapians-muted-dark = rgb(V.muted)
#let sapians-paper = rgb(V.canvas)
#let sapians-card-bg = rgb(V.composition)
#let sapians-line = rgb(V.line)
#let sapians-terracotta = sapians-text-dark // compatibilidade; destaque editorial neutro
#let font-mono = "JetBrains Mono"
#let radius-sm = 4pt
#let stroke-light = 0.5pt + sapians-line

#let vita-report(title: "", subtitle: "", author: "", date: "", version: "", lang: "pt", kicker: "", org: "", author-title: "", date-title: "", version-title: "", body) = {
  set document(title: title, author: author, description: subtitle)
  set text(font: "Inter", lang: lang, region: "BR", fill: sapians-text-dark, size: 10pt)
  set par(justify: true, leading: 0.65em)
  set page(paper: "a4", margin: (x: 17mm, top: 20mm, bottom: 19mm),
    header: context {
      if counter(page).get().first() > 1 {
        text(size: 7pt, fill: sapians-muted-dark)[SAPIANS #h(1fr) Qualidade das citações]
        v(1mm)
        line(length: 100%, stroke: stroke-light)
      }
    },
    footer: context [
      #line(length: 100%, stroke: stroke-light)
      #v(1mm)
      #text(size: 7pt, fill: sapians-muted-dark)[Pesquisa e Desenvolvimento #h(1fr) #counter(page).display("1")]
    ],
  )
  set heading(numbering: none)
  set figure(gap: 2mm)
  show link: set text(fill: sapians-text-dark)
  block(width: 100%, below: 6mm)[
    #text(size: 8pt, weight: "medium", fill: sapians-muted-dark, tracking: 0.08em)[#kicker]
    #v(4mm)
    #text(size: 32pt, weight: "medium", tracking: -0.035em)[#title]
    #v(3mm)
    #text(size: 13pt, fill: sapians-muted-dark)[#subtitle]
    #v(5mm)
    #line(length: 100%, stroke: 0.8pt + sapians-text-dark)
    #v(2mm)
    #text(size: 8pt, fill: sapians-muted-dark)[#author #h(1fr) #date · #version-title #version]
  ]
  body
}
