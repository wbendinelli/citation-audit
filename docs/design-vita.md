# Design VITA aplicado à auditoria

A referência é `sapians-design-vita/src/content/design-system.json` e seu guia
`docs/brand-system.md`, consultados no workspace do proprietário. A fotografia
versionada está em [tools/vita_tokens.json](../tools/vita_tokens.json).
A execução não depende do repositório privado nem de serviços de fontes.

O fundo é branco, superfícies são cinza neutro e a hierarquia usa preto SAPIANS.
Terracota é exclusivo de botões de ação; gráficos, números, tabelas e diagramas
usam neutros. Intensidade ordinal, rótulos diretos e formas de marcador distinguem
as séries. Artigos aparecem em painéis separados, e toda barra parte do zero,
exceto as diferenças flutuantes explicitamente identificadas no waterfall.

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

Cada diagrama tem uma composição própria para celular, com fluxo vertical,
texto legível e a mesma informação essencial da versão ampla. A simplificação
é de apresentação; definições e critérios continuam em METHOD.md.
