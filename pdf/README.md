# pdf/

PDFs dos trabalhos citantes, baixados para extrair o texto completo
(ver [`text/README.md`](../text/README.md)) quando não há rota de acesso
aberto automática.

**Não é redistribuível** — é o PDF de terceiros, guardado só para permitir a
extração local. Por isso o diretório está fora do git (`.gitignore`:
`pdf/*.pdf`) e só este README é rastreado.

## Nomenclatura

`<id>.pdf`, onde `<id>` é o identificador do registro em `data/master.json`
(ex.: `airline_057.pdf`, `grains_s001.pdf`).

## Como adicionar um PDF

Download avulso e manual, pelo seu próprio acesso institucional, um arquivo
por vez. A coleta automatizada através de proxy institucional viola os termos
dos publishers e costuma derrubar o acesso da instituição inteira.

Depois de salvar o arquivo em `pdf/<id>.pdf`, rode:

```
python3 tools/audit_30_validate_texts.py && python3 tools/audit_31_passages.py
```

O primeiro extrai o texto e valida que o PDF é do artigo certo (portão de
integridade — ver [METHOD.md](../METHOD.md)); o segundo localiza a passagem
citante no texto extraído.
