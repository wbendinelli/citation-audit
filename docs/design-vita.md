# Design VITA aplicado à auditoria

A referência é `sapians-design-vita/src/content/design-system.json` e seu guia
`docs/brand-system.md`, consultados no workspace do proprietário. A fotografia
versionada está em [tools/vita_tokens.json](../tools/vita_tokens.json).
A execução não depende do repositório privado nem de serviços de fontes.

O fundo é branco, superfícies são cinza neutro e a hierarquia usa preto SAPIANS.
Terracota é exclusivo de botões de ação. Texto, tabelas e diagramas conceituais
usam neutros. As figuras de medida têm uma extensão cromática local, descrita em
`data_visualization` nos tokens, para que categorias próximas não se confundam.
Essa extensão não é apresentada como parte da paleta canônica da interface VITA.

## Cor a serviço da leitura dos dados

| Uso | Codificação |
| --- | --- |
| Categorias distintas | Azul, verde-petróleo, ocre, magenta e cinza, conforme a legenda de cada figura |
| Profundidade, quartil e intensidade | Rampa sequencial de azul; intensidade carrega ordem ou magnitude |
| Linha do tempo | Categoria em faixa própria, nome junto ao dado, contagens e escala comum; azul, verde-petróleo, ocre e cinza reforçam a distinção |
| Só bibliografia na cobertura | Cinza com diagonais |
| Pendência e erro na cobertura | Fundo branco pontilhado para pendência; magenta com diagonais para aresta falsa |
| Postura e acurácia | Segmentos sólidos, pontilhados e diagonais, acompanhados de percentuais |
| Variantes do índice de disrupção | Cor e forma próprias: círculo, quadrado, losango e triângulo |

Cor não é a única chave: as barras empilhadas têm padrões e contagens ou
percentuais; os pontos têm formas distintas; categorias isoladas têm rótulos
diretos. A linha do tempo dispensa legenda: a posição e o nome identificam cada
categoria, com artigos em colunas e a mesma escala em todas as faixas.
O mapa de calor mantém escala linear e imprime também as células vazias como
zero, sem sugerir ausência de dado. Texto sobre preenchimento usa a alternativa
clara ou escura que oferece maior contraste calculado em sRGB linear.

Artigos aparecem em painéis separados, e toda barra parte do zero, exceto as
diferenças flutuantes explicitamente identificadas no waterfall. A inspeção
visual inclui a versão colorida, a conversão para cinza e as páginas do PDF no
tamanho de leitura, além da conferência automática da reprodução das figuras.

O projeto público conserva Inter e JetBrains Mono sob OFL, já vendorizadas.
Optimistic VF é a referência tipográfica da VITA, mas não é redistribuída aqui.
Esta é uma adaptação documentada para reprodução aberta, não uma alegação de
fidelidade tipográfica integral à interface privada.

A capa do README usa a mesma composição neutra, respiro e métricas geradas do snapshot. A página organiza propósito, resultados, método, entregas e reprodução, com diagramas junto da explicação correspondente.

Os mesmos tokens alimentam o tema de figuras em `tools/sapians.py`, os SVGs do
README, o painel HTML e `reports/01-impacto/vita.typ`. O PDF usa hierarquia sans,
legendas alinhadas à esquerda, superfícies planas e cabeçalho/rodapé discreto.
As figuras foram regeneradas a partir de `dados.json`; diagrama não recebe
estatística digitada à mão. O painel usa fontes locais e tem layout responsivo.

## Figuras para leitura, detalhes para consulta

O pipeline ensina o percurso da evidência; os nomes de scripts ficam no guia
operacional. O funil começa no inventário reunido, sem apresentar a lista do
Scholar como se fosse um conjunto que contém todas as APIs. A taxonomia explica
as perguntas em português e mantém os campos auxiliares fora dos eixos de função.
Os portões distinguem pendência, classificação e ausência confirmada manualmente.

A arquitetura complementa essa visão geral: mostra as fontes, os artefatos de
evidência, a leitura e o teste cego, as análises e a consolidação das medidas.
O README preserva o vínculo entre camadas e scripts e distingue julgamento
registrado de derivação automática; o detalhe operacional segue em tools/README.md.

Cada diagrama tem uma composição própria para celular, com fluxo vertical,
texto legível e a mesma informação essencial da versão ampla. A simplificação
é de apresentação; definições e critérios continuam em METHOD.md.
