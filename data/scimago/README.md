# data/scimago/

Planilha do Scimago Journal Rank usada por `tools/audit_41_scimago.py` para
atribuir o quartil oficial de cada periódico citante (ver METHOD.md — "Tier
de periódico: quartil Scimago oficial").

**Não é redistribuível** e não é gerada por script — é baixada manualmente.
Por isso está fora do git (`.gitignore`: `data/scimago/*.csv`) e só este
README é rastreado; os campos derivados que o pipeline precisa (quartil,
SJR, h-index, Overton, etc., por periódico) ficam commitados dentro de
`data/journals.json`, não neste CSV bruto.

## Como baixar

URL: <https://www.scimagojr.com/journalrank.php?out=xls> — edição **2025**,
todas as categorias, todos os países (parâmetros padrão da página).

O site devolve HTTP 403 para requisições automatizadas (`curl`, `urllib`
etc.) — baixe pelo navegador e salve como `data/scimago/scimagojr_2025.csv`.

Arquivo esperado: sha256
`6f20399957173a13e3c1729a5fb3b5821844ba75e8d640c8b3040ab19a6f7180`,
11.253.130 bytes (ambos em `config.json › scimago`).

## Como usar

```
python3 tools/audit_41_scimago.py
```

Casa por ISSN com `data/journals.json` e grava o quartil, SJR, h-index, rank,
país e Overton de cada periódico casado. `--check` valida o `journals.json`
já commitado sem precisar do CSV em disco.
