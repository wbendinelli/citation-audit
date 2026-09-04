# Reparos

Scripts de uso único, escritos em reação a erro encontrado nos dados. **Não fazem
parte do pipeline reprodutível** — rodá-los de novo sobre dados já corrigidos é
inofensivo mas inútil, e a numeração deles não continua a do `pipeline/`.

| Script | Erro que motivou |
|---|---|
| `10_repair_texts.py` | textos da 1ª rodada nomeados por IDs antigos; re-arquiva por DOI |
| `11_validate_texts.py` | 5 arquivos eram de outro artigo; exige que o texto contenha o próprio título |
| `12_gate_bibonly.py` | 8 falsos "fantasma"; veredito de bibliografia exige corpo comprovado |

O `11` continua valendo como portão e deve rodar após qualquer coleta nova.
