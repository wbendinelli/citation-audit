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

## Codebook: os casos de fronteira

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

## Provenance

Cada classificação em `data/classify.json` carrega um bloco `prov` com data, quem
codificou, o hash SHA-256 da evidência, o tipo de evidência (passagem literal ou corpo
completo sem menção), a URL ou arquivo de origem, e a versão do codebook.
