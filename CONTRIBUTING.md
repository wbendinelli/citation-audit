# Contribuindo

Este é um repositório de auditoria: cada citação recebida pelos dois artigos
é lida, e a classificação carrega a evidência que a sustenta. A página abaixo
é o guia prático — é também o que o CI cobra em cada pull request, para
ninguém precisar policiar isso à mão.

Correções e réplicas de qualquer pessoa são bem-vindas. A coisa mais valiosa
que você pode mandar é uma medição mostrando que algo aqui está errado.

## Sua primeira contribuição

1. **Fork** o repositório e clone o seu fork.
2. **Configure o ambiente** (Python ≥ 3.10; os números commitados foram
   produzidos em 3.12):

   ```bash
   uv venv --python 3.12 .venv
   VIRTUAL_ENV="$PWD/.venv" uv pip install -r requirements.txt
   brew install poppler   # pdftotext, usado pelos scripts que extraem PDF
   ```

   `pip install -r requirements.txt` num virtualenv 3.10+ funciona igual de
   bem se você preferir não usar `uv`. Para reproduzir o ambiente commitado
   byte a byte: `uv pip install --require-hashes -r requirements.lock`.

3. **Rode a derivação offline** (bloco B do [`tools/README.md`](tools/README.md#como-rodar))
   para ver o pipeline funcionando sem tocar rede.
4. **Branch, mude, abra um pull request.** CI roda `pre-commit`, os scripts
   com `--check` e confere links — se algo estiver errado, o robô diz
   exatamente o quê, antes de qualquer pessoa olhar.

## A régua de evidência

A ideia que faz este material valer a pena publicar — tudo nele pode ser
conferido, não só acreditado:

1. **Todo número em prosa (README, METHOD.md, ROADMAP.md, o texto do
   relatório) é impresso por um script versionado.** Um número sem célula/
   script que o imprima é bug — ou some o script, ou apague o número.
2. **Toda classificação em `data/classify.json` carrega a passagem literal**
   do texto citante e o bloco `prov` completo (`codebook`, `coded_at`,
   `coded_by`, `evidence_kind`, `evidence_sha256_16`, `source`) — ver
   METHOD.md § Provenance. Citação sem passagem recuperada fica fora de toda
   contagem, nunca é presumida boa nem ruim.
3. **Quando uma medição contradiz a prosa, a prosa muda e o valor antigo
   fica registrado na nota**, marcado como corrigido. Correção é parte do
   material, não algo para esconder.

## A regra de direito autoral

`pdf/` e `text/` guardam texto de terceiros — obtido para leitura e
classificação, não para redistribuição. **Nunca commite arquivo dentro de
`pdf/` ou `text/`** (o `.gitignore` já barra `*.pdf`/`*.txt` nesses
diretórios; não force `git add` neles). Uma passagem citada em
`data/classify.json` ou na prosa do repositório é uma citação de escopo
limitado — na prática, até ~430 caracteres — nunca o texto completo do
citante.

## Como adicionar um PDF obtido manualmente

Baixe pelo seu próprio acesso institucional, um arquivo por vez — a coleta
automatizada através de proxy institucional viola os termos dos publishers e
costuma derrubar o acesso da instituição inteira (ver
[`pdf/README.md`](pdf/README.md)). Salve como `pdf/<id>.pdf` e rode:

```bash
python3 tools/audit_30_validate_texts.py && python3 tools/audit_31_passages.py
python3 tools/check_data.py --local
```

## Estilo de commit

`tipo(escopo): resumo`, escopos `tools` `data` `method` `readme` `report`
`ci` — por exemplo `fix(data): corrige DOI duplicado em airline_057`,
`docs(method): §9 — corrige tabela de cobertura`. Uma correção de número é
sempre `fix`, nunca `docs`, mesmo quando o diff é só texto.
