<!-- Gerado por tools/audit_83_review.py; não editar contagens à mão. -->
# Revisão da atualização — 2026-10-24

A coleta pública foi repetida e a análise refeita. A população conserva o critério
registrado em [METHOD.md](../../METHOD.md). Valores anteriores abaixo ficam
**corrigidos na apresentação corrente**, preservados como snapshot histórico.

| Medida | Snapshot anterior | Atual |
|---|---:|---:|
| Registros do inventário | 176 | 177 |
| Com DOI | 147 | 147 |
| População do estudo | 87 | 87 |
| Classificações com passagem | 104 | 105 |
| Classificadas na população | 74 | 75 |
| Menções no corpo | 92 | 93 |
| Má atribuição | 16 | 17 |
| Trecho literal entre registros com quartil | 74 | 75 |
| Pendentes entre registros com quartil | 17 | 16 |
| CD5 (airline) | -0.010567 | -0.011550 |
| DI5 (airline) | 0.600000 | 0.588235 |
| CD5 (grains) | 0.000839 | 0.000834 |
| DI5 (grains) | 0.306122 | 0.306122 |
| Co-citação posterior (share AB) | 0.084956 | 0.084806 |

Fonte: `audit_70 §atualizacao`, `§inventario`, `§populacao`, `§cobertura` e `§eixos`;
[dados gerados](dados.json). As contagens da edição anterior estão preservadas em
[data/baselines](../../data/baselines/2026-09-04.json).

## Coleta e deduplicação

| Artigo | Base | Resposta | Registros retornados |
|---|---|---|---:|
| airline | europepmc | ok | 0 |
| airline | openalex | ok | 57 |
| airline | opencitations | ok | 39 |
| airline | s2 | ok | 48 |
| grains | europepmc | ok | 0 |
| grains | openalex | ok | 60 |
| grains | opencitations | ok | 50 |
| grains | s2 | ok | 54 |

As APIs não acrescentaram obras após a deduplicação. Elas completaram metadados
e documentaram DOIs alternativos. O cruzamento com a lista local do Scholar
recuperou um título ausente, ainda sem DOI nem passagem. A lista do Scholar
continua sendo uma entrada manual; não houve nova consulta autenticada ao Scholar.
A duplicata deliberadamente arquivada não foi reintroduzida.

## Leitura adicional e seu limite

`grains_007`, revisão em *Advances in Agriculture*, recebeu classificação a partir
da tabela de perdas qualitativas na [página integral da editora](https://onlinelibrary.wiley.com/doi/10.1155/aia/3910210).
A linha atribuída ao artigo auditado descreve preço por dano em hortaliças;
o artigo-fonte modela determinantes macroeconômicos de perdas quantitativas de grãos.
A atribuição foi codificada como `misrepresented` / `dead_end`, com passagem,
origem e hash em [classify.json](../../data/classify.json). A profundidade é
`supporting` porque o citante o emprega como evidência da síntese; não foi presumido
reuso metodológico nem de dados. Esta leitura ainda requer revisão independente.
O HTML completo da editora não foi persistido; a passagem curta e sua origem
foram preservadas. Isso não foi transformado em alegação de texto completo em disco.

A IRR continua referente ao pacote cego original. Seus coeficientes não devem
ser apresentados como validação das classificações adicionais.

## Resultados correntes

Má atribuição: 17/93, 18%.
Citação perfunctória: 68/93, 73%.
Trecho recuperado entre registros com quartil: 75/98, 77%.
Não se deve inferir qualidade de citação a partir do quartil: cobertura e acesso
continuam desiguais. Comparadores da literatura ainda assinalados como pendentes
não foram promovidos a evidência verificada.

## Grafos de disrupção e co-citação

- `airline`: snapshot 2026-10-24.
- `grains`: snapshot 2026-10-24.

Os arquivos de grafo preservam backend, pedidos de rede, falhas e referências
sem mapeamento. O método, as janelas e as sementes foram mantidos. CD e DI usam
variantes diferentes: discordância de sinal não sustenta veredito causal.

## Correções de engenharia

- Coleta incremental: preserva IDs, passagens, status terminal e registros antigos,
  inclusive quando uma base falha ou retorna menos resultados.
- Candidatos de múltiplas fontes são unidos antes do cruzamento com o inventário;
  títulos e DOI não são comparados antes de completar os metadados disponíveis.
- A triagem preserva IDs e arestas falsas; periódicos já conhecidos sobrevivem
  à indisponibilidade de endpoints.
- Resolução de DOI rejeita respostas sem título ou sem correspondência suficiente, evitando converter uma tese em projeto de pesquisa.
- IDs exclusivos do Scholar avançam a partir dos já usados; a derivação é idempotente.
- A data do relatório pertence ao snapshot, impedindo que o CI falhe só porque
  o verificador rodou em outro dia.
- O casamento Scimago prioriza ISSN-L e ordena os demais ISSNs: a ordem de um conjunto não pode mudar o quartil entre execuções.
- Os campos de sensibilidade e cruzamento do CD são exportados com seus nomes reais.

## Apresentação VITA

Figuras, diagramas do README, painel HTML e composição do PDF compartilham os
[tokens locais](../../tools/vita_tokens.json), fotografados do design global VITA.
Branco, cinza e preto organizam a leitura; rótulos, intensidade e marcadores
preservam as distinções. Terracota fica reservado a ações reais. Inter e JetBrains
Mono, sob OFL, mantêm a reprodução aberta; Optimistic VF não foi redistribuída.

## Pendências que permanecem

- Validar as afirmações dos artigos com o autor e concluir a codificação humana.
- Obter corpos integrais das leituras institucionais não persistidas.
- Verificar comparadores nas fontes primárias.
- Resolver referências sem correspondência entre bases e atualizar a lista manual
  do Scholar quando houver nova exportação.
