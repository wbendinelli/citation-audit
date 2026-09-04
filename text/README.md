# text/

Texto completo dos trabalhos que citam os dois artigos auditados, extraído
localmente (PDF via `pdftotext`, ou HTML/XML baixado) para permitir localizar
a passagem citante e classificar a citação com a evidência em mãos (ver
[METHOD.md](../METHOD.md) — regra de evidência).

**Não é redistribuível.** É o texto de terceiros, obtido para leitura e
classificação, não para republicação — por isso o diretório está fora do git
(ver `.gitignore`: `text/*.txt`) e só este README é rastreado.

## Como regenerar

- **Citantes de acesso aberto**: fases 20–22 —
  `python3 tools/audit_20_download.py`, `audit_21_download_deep.py`,
  `audit_22_retry_all.py` (tocam rede: OpenAlex, Unpaywall). Extraem o texto
  do PDF/HTML/XML baixado e gravam `text/<id>.txt`.
- **Citantes só-acesso-institucional (SSO)**: sem rota automática — baixe o
  PDF manualmente (ver [`pdf/README.md`](../pdf/README.md)) e rode
  `python3 tools/audit_30_validate_texts.py`, que extrai `pdf/<id>.pdf` para
  `text/<id>.txt` via `pdftotext` e valida que o texto é do artigo certo.
- Depois de qualquer nova extração, rode
  `python3 tools/audit_31_passages.py` para localizar a passagem citante.

## `text/_orfaos/`

Arquivos que não são o `text_path` de nenhum registro em `data/master.json`
no momento — texto que já foi extraído mas ficou sem vínculo (ex.: o registro
que ele apoiava foi absorvido por deduplicação, ou o arquivo é de uma rodada
de re-arquivamento anterior). Ficam aqui em vez de apagados para permitir
re-vinculação manual, e não contam como órfão de verdade — só os arquivos
soltos direto em `text/` contam.

## Invariante

`python3 tools/check_data.py --local` verifica que o conjunto de arquivos em
`text/*.txt` é exatamente igual ao conjunto de `text_path` referenciados em
`data/master.json` (nem sobra, nem falta) — arquivo em `text/_orfaos/` fica
fora dessa conferência.
