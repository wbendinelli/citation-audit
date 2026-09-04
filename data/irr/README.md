# Pacote cego de confiabilidade entre codificadores (IRR)

Protocolo completo em [METHOD.md §17](../../METHOD.md). Os quatro arquivos aqui são
gerados por `tools/audit_61_irr_pack.py` a partir de `data/classify.json` já migrado
para o codebook v2 (§16) — semente fixa (`20260904`), reproduzível byte a byte.

| Arquivo | Conteúdo |
|---|---|
| `pack_blind.json` | O pacote em si: 4 lotes, 114 itens (104 entradas vivas + 10 duplicadas como sonda intra-codificador). Cada item tem só `item_id`, `paper`, `citing_title`, `passages`, `n_passages`, `passage_source`, `citation_style` — sem DOI, veículo, ano, nota ou qualquer rótulo v1/v2. É o que os codificadores 2 e 3 recebem. |
| `pack_key.json` | A chave: `item_id -> {doi, paper, record_id, duplicate_of, codebook_exemplar, passage_source, n_scrubbed, batch}`. Nunca vai para um codificador — é o que liga a resposta cega de volta ao registro real, usado só por `audit_62_irr_stats.py`. |
| `instructions.md` | O codebook v2 completo (eixos, casos de fronteira literais de METHOD.md §6, ordem de decisão, contrato de saída) mais o resumo e o registro de afirmações dos dois artigos — o único material que um codificador cego lê. |
| `irr_c1_from_v2.json` | Os rótulos do **codificador 1**: a classificação original de `data/classify.json`, projetada para o formato de rótulo do pacote (`labels_of()`) — não um novo julgamento, é a entrada de `--c1` em `audit_62_irr_stats.py`. |

## O que falta

Os rótulos do codificador 2 (Opus) e do codificador 3 (Sonnet) — cada um coleta, em
contexto novo, a partir só de `instructions.md` e do lote, sem ver este diretório do
repositório. Quando os dois arquivos chegarem, `audit_62_irr_stats.py --c1
irr_c1_from_v2.json --c2 <arquivo> --c3 <arquivo> --key pack_key.json --out
data/irr/irr_stats.json` calcula a concordância (α de Krippendorff, κ de Cohen,
PABAK, AC1 de Gwet, Jaccard, PPI) e o resultado preenche a seção "Resultados" de
METHOD.md §17.

## Cuidado

Não regrave `pack_blind.json`/`pack_key.json` com semente diferente enquanto a
coleta estiver em andamento — muda todo `item_id` e desalinha o que os codificadores
já entregaram. Para conferir que o pacote continua sem vazamento de identidade:
`python3 tools/audit_61_irr_pack.py --audit --root .` (sai com código 1 se achar
algum).
