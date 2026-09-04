# Registro de afirmações dos dois artigos

`claims.json` — 63 afirmações (30 aviação, 33 grãos) extraídas dos PDFs publicados por
Claude Opus em 2026-09-04, cada uma com citação literal verificada contra três extrações
independentes do PDF. `validated_by_author` é `false` em todas: a validação pelo autor
está pendente, e até lá o registro vale como leitura de segundo codificador.

`status=relayed` (16 afirmações) marca o que o próprio artigo atribui a terceiros — o que
um citante pode erroneamente atribuir aos autores. Exemplos: "20–35% dos grãos perdidos"
é Gustavsson et al. (2011); a fórmula de %PHL é Gustavsson et al. (2013); "dissuasão de
entrada prevalece em hubs" é Molnar (2013).

## Armadilha de extração

`pdftotext` no PDF de aviação **descarta todo sinal de menos** (glifo `0x03`), lendo
`−1.4772***` como `1.4772***` e `−33.5` como `33.5`. Os sinais são o ponto do artigo.
`source_text/airline.txt` já vem com `0x03`→`−`, `0x02`→`•`, `U+2044`→`*` corrigidos.
Qualquer script que rode `pdftotext` cru sobre esse PDF lê os coeficientes ao contrário.
