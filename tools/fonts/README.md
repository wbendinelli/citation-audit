# tools/fonts/ — as fontes empacotadas

Seis arquivos `.ttf` estáticos e as duas licenças que precisam viajar
junto. Nada aqui é código do repositório: são binários de terceiros,
redistribuídos sob a **SIL Open Font License 1.1**.

## Procedência

Copiados verbatim de
[`sapians-latex`](https://github.com/wbendinelli/sapians-latex) —
`assets/fonts/`, commit `4c10f27` (os dois `OFL-*.txt` vieram de `e76f190`
da mesma árvore, onde moram ao lado dos binários; os `.ttf` são
byte-idênticos nos dois commits, conferido por `shasum -a 256`).

| Arquivo | Família | Versão | Upstream | Licença |
|---|---|---|---|---|
| `Inter-Regular.ttf` | Inter | 4.000 (`git-a52131595`) | [rsms/inter](https://github.com/rsms/inter) | [`OFL-Inter.txt`](OFL-Inter.txt) |
| `Inter-Medium.ttf` | Inter | 4.000 | rsms/inter | `OFL-Inter.txt` |
| `Inter-SemiBold.ttf` | Inter | 4.000 | rsms/inter | `OFL-Inter.txt` |
| `Inter-Bold.ttf` | Inter | 4.000 | rsms/inter | `OFL-Inter.txt` |
| `JetBrainsMono-Regular.ttf` | JetBrains Mono | 2.304 | [JetBrains/JetBrainsMono](https://github.com/JetBrains/JetBrainsMono) | [`OFL-JetBrainsMono.txt`](OFL-JetBrainsMono.txt) |
| `JetBrainsMono-Bold.ttf` | JetBrains Mono | 2.304 | JetBrains/JetBrainsMono | `OFL-JetBrainsMono.txt` |

São os **estáticos**, não a fonte variável (`InterVariable.ttf`): o
`font_manager` do matplotlib resolve pesos por arquivo, e um `.ttf`
variável registra um peso só — o que faria `fontweight="bold"` cair
silenciosamente no Regular. Quatro pesos de Inter (400/500/600/700) cobrem
o que o estilo pede: corpo, rótulo de eixo (`axes.labelweight: medium`),
kicker e título. Dois de JetBrains Mono cobrem código, DOI e tabelas
monoespaçadas.

## Charter não é empacotada — e não precisa ser

O token `font-serif` do design system (`("Charter", "Times New Roman")`,
definido em `packages/typst/src/tokens.typ` do `sapians-latex`/`sapians`)
não tem arquivo `.ttf` aqui, por duas razões:

- **Licença.** Charter é uma fonte comercial da Bitstream, não OFL.
  Empacotá-la exigiria uma licença que este repositório não tem — os seis
  arquivos acima são todos OFL 1.1 precisamente para evitar esse problema.
- **Uso.** O layout deste relatório (`reports/01-impacto/`, via
  `@preview/sapians` e `tools/sapians.py`) usa só as famílias sans
  (`font-sans`, Inter) e mono (`font-mono`, JetBrains Mono). Nenhum título,
  parágrafo, legenda ou tabela invoca `font-serif`. `SP.aplicar()` só
  registra as seis fontes de `FONTES`; Charter nunca entra no matplotlib
  nem no `typst compile` deste relatório, e sua ausência aqui não é uma
  lacuna a preencher.

## Por que empacotadas, e não instaladas

Porque o número precisa ser conferível e o relatório precisa sair igual em
qualquer máquina. O PDF final combina texto do Typst com figuras PNG do
matplotlib na mesma página — os dois caminhos, `typst compile --font-path
tools/fonts` e `SP.aplicar()`, precisam resolver exatamente às mesmas seis
fontes, ou o título de uma figura sai num Inter e o corpo do parágrafo ao
lado sai em outro. Uma fonte resolvida pelo sistema quebra isso de três
jeitos:

- **Nem toda máquina tem Inter/JetBrains Mono instaladas.** Quando falta,
  Typst e matplotlib caem cada um no seu próprio fallback (não o mesmo),
  então o mesmo `.typ` produz PDFs com quebra de linha e paginação
  diferentes conforme quem compila.
- **Sem as fontes, matplotlib cai no DejaVu Sans em silêncio** — sem erro,
  sem aviso — e o PNG muda em cada glifo.
- **Mesmo quando presente, uma versão diferente da família muda métricas**
  e move texto por frações de pixel, o que também reflui a paginação.

Empacotadas e registradas por caminho absoluto — `font_manager.fontManager.
addfont` em `tools/sapians.py`, `--font-path tools/fonts` na chamada do
Typst — a fonte é a mesma em qualquer ambiente, e `SP.aplicar()` **falha
alto** (`FileNotFoundError`) se algum arquivo sumir, em vez de degradar em
silêncio para o DejaVu. Ver CLAUDE.md para a regra de evidência que torna
essa reprodutibilidade byte-a-byte parte do contrato do repositório, não
só conveniência.

Custo: ~2,1 MB no repositório, uma vez. Os arquivos não mudam — se um dia
mudarem, é bump deliberado com nova compilação do relatório inteiro, como
qualquer pin.

## A licença

A OFL 1.1 permite uso, modificação e redistribuição livres, desde que as
fontes não sejam vendidas isoladamente e **o texto da licença acompanhe os
arquivos** — é exatamente por isso que os dois `OFL-*.txt` moram aqui, ao
lado dos binários. A licença MIT do repositório **não** cobre este
diretório. Figuras (PNG) e o PDF do relatório produzidos com estas fontes
não carregam obrigação adicional.
