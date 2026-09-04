# Método de auditoria de citações

Avaliar **a qualidade de cada citação recebida**, não a contagem. A pergunta não é
"quantos me citaram", é "quem me usou de verdade, quem me citou de passagem, e quem
me citou errado".

## Taxonomia

Quatro eixos independentes. A taxonomia foi extraída do código-fonte do
`citation-explorer` do Paperclip (pacote `gxl_paperclip` 0.7.47, módulo
`cli/citation_explorer.py`), e é compatível com a literatura de *citation function
analysis* (CiTO; Teufel et al.; os *intents* do Semantic Scholar).

### 1. ROLE — quanto o artigo importou para quem citou

| Valor | Significado |
|---|---|
| `bibliography_only` | Consta na lista de referências, sem menção no corpo |
| `drive_by` | Citação em bloco, afirmação genérica, sem uso próprio |
| `brief_mention` | Uma afirmação específica é atribuída ao artigo |
| `real_mention` | O artigo é descrito com seu conteúdo real |
| `supporting` | O artigo sustenta parte do argumento ou do desenho do citante |
| `foundational` | O citante constrói sobre o artigo, ou o identifica como referência única |
| `wrongly_interpreted` | O artigo é citado para algo que ele não diz |

### 2. STANCE — postura do citante

`supporting` · `contradictory` · `none`

Regra deliberadamente liberal, como no original: qualquer contraponto conta como
`contradictory`, mesmo sem linguagem hostil e mesmo quando o citante também usa o
artigo como baseline. "Unlike X", "X não considera", "X é limitado a" — todos contam.

### 3. REUSE_TAGS — reuso efetivo

`method_adoption` · `result_validated` · `dataset_reuse` · `benchmarking` · `work_extended`

Só marcado quando o citante **usa** o trabalho, não quando apenas o menciona.
É o sinal mais forte de impacto real.

### 4. CITATION_STATUS

`in_text` · `bibliography_only` · `not_found`

## Regra de evidência

**Nenhuma classificação sem a passagem literal.** Toda entrada classificada guarda o
trecho exato do texto citante. Citação sem passagem recuperada fica fora de todas as
contagens — não é classificada como "ruim", é classificada como "não lida".

Isso torna as métricas honestas: elas são sempre "entre as citações que deu para ler".

## Fontes

| Camada | Fonte |
|---|---|
| Grafo de citações | OpenAlex (`filter=cites:`) |
| Texto completo | Unpaywall, Europe PMC, arXiv, repositórios institucionais |
| Trechos de citação | Semantic Scholar (`/citations?fields=contexts,intents,isInfluential`) |
| Metadados | OpenAlex, Crossref |

Todas gratuitas e sem autenticação.

## Portões de integridade

Três verificações automáticas impedem que a auditoria produza conclusões falsas.
Todas foram acrescentadas depois de detectarem erro real nos dados.

**1. O texto tem de ser do artigo certo.** O arquivo baixado precisa conter o próprio
título do registro. Cinco arquivos falharam nesse teste — eram de outro artigo, por
colisão de nome durante o re-arquivamento. Teriam contaminado a classificação.

**2. Página de rosto não é texto completo.** Documento curto sem o sobrenome citado é
abstract, não artigo. Marcado como parcial e fora de toda contagem.

**3. "Só na bibliografia" exige o corpo do artigo.** Páginas de rosto de publisher
(Springer, Wiley) exibem a lista de referências inteira sem o corpo. Encontrar o
sobrenome só na bibliografia desses documentos **não** prova citação-fantasma — prova
apenas que o corpo não foi obtido. O veredito de fantasma só vale com corpo comprovado.
Esse portão derrubou 8 falsos positivos e confirmou 6 fantasmas legítimos.

## Autocitação e citação de coautor

Marcadas explicitamente e excluídas do indicador de reuso metodológico externo.
Uma citação assinada por coautor do artigo citado não mede alcance independente.
