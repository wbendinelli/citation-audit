"""audit_61_irr_pack.py — monta o pacote CEGO para o segundo codificador
(inter-rater reliability) a partir do classify migrado (v2) e do master.

Fase 60 (análises). Lê `data/classify.json` (v2), `data/master.json`,
`data/claims/claims.json`, `METHOD.md` e, se existirem, `config.json` e
`data/claims/source_text/{airline,grains}.txt`. Grava em `data/irr/`:

  pack_blind.json      lista de 4 lotes, cada um uma lista de itens SEM doi,
                       veículo, ano, nota, rótulos, flags ou highlight
  pack_key.json        {item_id: {doi, paper, record_id, duplicate_of,
                       codebook_exemplar, passage_source, n_scrubbed, batch}}
  instructions.md      instruções do codificador (português)
  irr_c1_from_v2.json  os rótulos do 1º codificador projetados por item_id
                       (subproduto; entrada `--c1` de audit_62_irr_stats.py)

Itens = todas as entradas do classify (células raras ficariam vazias numa
amostra). Passagens: `passages_auto` do master (janelas automáticas de ±700
caracteres) quando o registro tem `text_path` e a lista não é vazia; senão as
passagens curadas do classify. O DOI e o nome do veículo do próprio citante
são apagados de dentro das passagens (cabeçalho corrido vaza identidade).
Embaralhamento com semente fixa; 10 itens duplicados sob um segundo item_id
(sonda intra-codificador), registrados só na chave.

Uso:
  python3 tools/audit_61_irr_pack.py [--root PATH] [--seed N] [--n-dup 10] [--n-batches 4]
  python3 tools/audit_61_irr_pack.py [--root PATH] --audit     # auditoria de vazamento

`--audit` procura no pacote: padrão de DOI (10.\\d{4,}) fora das passagens e o
DOI do próprio citante dentro delas; o veículo do próprio citante em qualquer
campo e qualquer veículo de >= 3 palavras fora das passagens; ano de 4 dígitos
junto de "et al." no título; e as palavras ghost|fantasma|misattribution|
foundational|drive_by fora das passagens. Sai com código 1 se houver vazamento.
"""

import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
JSON_KW = {"sort_keys": True, "indent": 1, "ensure_ascii": False}
SEED_DEFAULT = 20260904
LABEL_WORDS = re.compile(
    r"ghost|fantasma|misattribution|foundational|drive_by", re.IGNORECASE
)
DOI_PATTERN = re.compile(r"10\.\d{4,}")
FORBIDDEN_ITEM_KEYS = {
    "doi",
    "venue",
    "year",
    "note",
    "role",
    "flag",
    "presence",
    "depth",
    "accuracy",
    "distortion",
    "stance",
    "reuse",
    "relation",
    "record_flags",
    "highlight",
    "claims",
    "codebook_exemplar",
    "prov",
    "text_path",
    "id",
    "record_id",
    "duplicate_of",
}
ITEM_KEYS = [
    "item_id",
    "paper",
    "citing_title",
    "passages",
    "n_passages",
    "passage_source",
    "citation_style",
]
LABEL_KEYS = [
    "presence",
    "depth",
    "stance",
    "accuracy",
    "distortion",
    "reuse",
    "claim_ids",
    "confidence",
    "rationale",
]


# ---------------- E/S ----------------


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, **JSON_KW)
        f.write("\n")


def envelope(raw, key):
    if isinstance(raw, dict) and "meta" in raw and key in raw:
        return raw
    return {"meta": {"schema": 1}, key: raw}


def master_records(master):
    recs = {}
    for paper, block in master["papers"].items():
        for rec in block["citing"]:
            doi = (rec.get("doi") or "").strip().lower()
            if doi:
                recs[doi] = (paper, rec)
    return recs


# ---------------- itens ----------------


def item_id_for(seed, doi, suffix, taken):
    """'IRR-' + 4 hex de sha256(seed+doi[+suffix]); em colisão, desliza pelo
    digest (determinístico)."""
    digest = hashlib.sha256(f"{seed}{doi}{suffix}".encode()).hexdigest()
    for off in range(len(digest) - 4):
        cand = "IRR-" + digest[off : off + 4]
        if cand not in taken:
            taken.add(cand)
            return cand
    raise RuntimeError("sem item_id livre")


def scrub_passages(passages, doi, venue):
    """Apaga das passagens o DOI e o veículo do próprio citante (cabeçalho
    corrido). Devolve (passagens, nº de passagens alteradas)."""
    out, n = [], 0
    for p in passages:
        q = p
        if doi:
            q = re.sub(
                r"(https?://(dx\.)?doi\.org/)?" + re.escape(doi),
                "[DOI do citante removido]",
                q,
                flags=re.IGNORECASE,
            )
        if venue and len(venue) >= 4:
            q = re.sub(
                r"(?<![A-Za-z])" + re.escape(venue) + r"(?![A-Za-z])",
                "[veículo removido]",
                q,
                flags=re.IGNORECASE,
            )
        if q != p:
            n += 1
        out.append(q)
    return out, n


_BRACKET_YEAR = re.compile(
    r"\[\s*(?:19|20)\d\d[a-z]?\s*\]"
)  # "[2016]" é autor-ano entre colchetes
_NUMERIC_REF = re.compile(r"\[\d")  # "[12]", "[5,21,22]", "[1–3]"
_SUPERSCRIPT = re.compile(
    r"et al\.\d|\w\.\d{1,3}(?:[,–-]\d{1,3})*(?=\s|$)"
)  # "et al.17"


def citation_style(passages, surname):
    """'numeric' se há padrão `[dígito` perto do sobrenome (±150 caracteres),
    descontando anos entre colchetes ("[2016]" é autor-ano); sem o sobrenome
    na passagem (o citante usa número), 'numeric' se há `[dígito` ou numeral
    sobrescrito colado a 'et al.'; senão 'author_year'. None sem passagem."""
    text = "\n".join(passages)
    if not text.strip():
        return None
    low = text.lower()
    positions = [m.start() for m in re.finditer(re.escape(surname.lower()), low)]
    if positions:
        for pos in positions:
            window = _BRACKET_YEAR.sub(" ", text[max(0, pos - 150) : pos + 150])
            if _NUMERIC_REF.search(window) or re.search(r"et al\.,?\d", window):
                return "numeric"  # "[12]" ou sobrescrito colado: "et al.18"
        return "author_year"
    stripped = _BRACKET_YEAR.sub(" ", text)
    if _NUMERIC_REF.search(stripped) or _SUPERSCRIPT.search(stripped):
        return "numeric"
    return "author_year"


def build_items(classify, recs, surname, seed):
    """Um item por entrada do classify, com a passagem escolhida e limpa."""
    items, meta, taken = [], {}, set()
    for doi in sorted(classify["entries"]):
        e = classify["entries"][doi]
        if doi not in recs:
            raise SystemExit(f"{doi}: entrada do classify sem registro no master")
        paper, rec = recs[doi]
        auto = rec.get("passages_auto") or []
        if rec.get("text_path") and auto:
            passages, source = list(auto), "auto"
        else:
            passages, source = list(e.get("passages") or []), "curated"
        passages, n_scrub = scrub_passages(passages, doi, rec.get("venue"))
        iid = item_id_for(seed, doi, "", taken)
        items.append(
            {
                "item_id": iid,
                "paper": paper,
                "citing_title": rec.get("title") or "",
                "passages": passages,
                "n_passages": len(passages),
                "passage_source": source,
                "citation_style": citation_style(passages, surname),
            }
        )
        meta[iid] = {
            "doi": doi,
            "paper": paper,
            "record_id": rec.get("id"),
            "duplicate_of": None,
            "codebook_exemplar": bool(e.get("codebook_exemplar")),
            "passage_source": source,
            "n_scrubbed": n_scrub,
        }
    return items, meta, taken


def labels_of(entry):
    return {
        "presence": entry.get("presence"),
        "depth": entry.get("depth"),
        "stance": entry.get("stance"),
        "accuracy": entry.get("accuracy"),
        "distortion": entry.get("distortion"),
        "reuse": list(entry.get("reuse") or []),
        "claim_ids": list(entry.get("claims") or []),
        "confidence": None,
        "rationale": None,
    }


def make_pack(items, meta, taken, seed, n_dup, n_batches):
    rng = random.Random(seed)
    order = list(items)
    rng.shuffle(order)
    n = len(order)
    sizes = [n // n_batches + (1 if i < n % n_batches else 0) for i in range(n_batches)]
    batches, pos = [], 0
    batch_of = {}
    for b, s in enumerate(sizes):
        chunk = order[pos : pos + s]
        pos += s
        batches.append(chunk)
        for it in chunk:
            batch_of[it["item_id"]] = b
    dup_pairs = []
    for it in rng.sample(order, n_dup):
        orig = it["item_id"]
        dup_id = item_id_for(seed, meta[orig]["doi"], "#dup", taken)
        dup = dict(it, item_id=dup_id)
        b = (batch_of[orig] + n_batches // 2) % n_batches  # lote distinto do original
        batches[b].append(dup)
        batch_of[dup_id] = b
        meta[dup_id] = dict(meta[orig], duplicate_of=orig)
        dup_pairs.append((orig, dup_id))
    for b in batches:
        rng.shuffle(b)
    for iid, b in batch_of.items():
        meta[iid]["batch"] = b + 1
    return batches, dup_pairs


# ---------------- instruções ----------------


def extract_section(method_text, heading, number=None):
    """Corpo da seção `## <heading>` de METHOD.md. Aceita o título puro
    ("## Codebook: …") e o numerado ("## §6 — Codebook: …"); se o título foi
    renomeado, cai no número da seção — em METHOD.md o número é contrato, o
    título não."""
    heads = list(
        re.finditer(
            r"^## (?:§(\d+)\s*[—–-]\s*)?(.+?)[ \t]*$", method_text, re.MULTILINE
        )
    )
    pick = next(
        (h for h in heads if h.group(2).strip().lower() == heading.lower()), None
    )
    if pick is None and number is not None:
        pick = next((h for h in heads if h.group(1) == str(number)), None)
    if pick is None:
        raise SystemExit(f"METHOD.md sem a seção '## {heading}' (nem §{number})")
    start = pick.end()
    m2 = re.search(r"^## ", method_text[start:], re.MULTILINE)
    end = start + m2.start() if m2 else len(method_text)
    return method_text[start:end].strip()


def extract_abstract(text):
    """Abstract do PDF de duas colunas do Elsevier: as linhas entre o cabeçalho
    'a b s t r a c t' e a linha de copyright, lidas a partir da coluna do
    cabeçalho (a coluna esquerda traz o histórico do artigo)."""
    lines = text.splitlines()
    col = start = None
    for i, ln in enumerate(lines[:200]):
        m = re.search(r"a\s?b\s?s\s?t\s?r\s?a\s?c\s?t", ln, re.IGNORECASE)
        if m:
            col, start = m.start(), i + 1
            break
    if col is None:
        return None
    out = []
    for ln in lines[start : start + 80]:
        if re.search(r"(©|Ó|\(c\))\s*(19|20)\d\d|All rights reserved", ln):
            break
        if len(ln) > col and (col == 0 or ln[col - 1] == " "):
            seg = ln[col:].strip()
        else:
            parts = re.split(r"\s{3,}", ln.strip())
            seg = (
                parts[-1]
                if len(parts) > 1
                else ("" if len(ln.rstrip()) <= col else ln.strip())
            )
        if seg:
            out.append(seg)
    abstract = " ".join(out)
    abstract = re.sub(r"(\w)- (\w)", r"\1\2", abstract)
    abstract = re.sub(r"\s+", " ", abstract).strip()
    return abstract or None


TAXONOMY_V2_MD = """## Codebook v2 — taxonomia em eixos ortogonais

A versão 1 do codebook usava um único `role` de sete valores mais uma `flag`. A versão 2
separa o que ali estava misturado em três eixos independentes — **presença**,
**profundidade** e **exatidão** — e mantém **postura** (stance) e **reuso** como eixos
próprios. Cada eixo é julgado sozinho: uma citação pode ser profunda e errada, rasa e
exata, contrária e exata. Nunca deixe um eixo "puxar" o outro.

### Eixo 1 — PRESENCE: onde o artigo aparece no citante

| Valor | Significado |
|---|---|
| `in_text` | O artigo é mencionado no corpo do texto — inclusive dentro de um bloco de citações numéricas como `[5,21,22,23]` ou de um parêntese com várias fontes |
| `reference_list_only` | Consta na lista de referências, sem nenhuma menção no corpo. Exige corpo completo verificado (portão 3 de METHOD.md) |
| `not_cited` | Não aparece nem no corpo nem na lista de referências — aresta falsa do grafo de citações. Não ocorre neste pacote |

### Eixo 2 — DEPTH: quanto o artigo importou para quem citou (ordinal)

Só se aplica quando `presence = in_text`; caso contrário fica `null`.

| Nível | Valor | Significado |
|---|---|---|
| 1 | `drive_by` | Citação em bloco, afirmação genérica, sem uso próprio |
| 2 | `brief_mention` | Uma afirmação específica é atribuída ao artigo |
| 3 | `real_mention` | O artigo é descrito com seu conteúdo real |
| 4 | `supporting` | O artigo sustenta parte do argumento ou do desenho do citante |
| 5 | `foundational` | O citante constrói sobre o artigo, ou o identifica como referência única |

A profundidade é julgada pelo que o citante FAZ com o artigo, não pela exatidão do que
diz dele. Uma citação que atribui ao artigo uma afirmação específica errada continua
sendo `brief_mention` (nível 2) neste eixo e recebe o erro no eixo de exatidão. (No v1
esse caso era o `role` `wrongly_interpreted`, que misturava os dois eixos.)

### Eixo 3 — STANCE: postura do citante

`supporting` · `contradictory` · `none`

Regra deliberadamente liberal, como no original: qualquer contraponto conta como
`contradictory`, mesmo sem linguagem hostil e mesmo quando o citante também usa o
artigo como baseline. "Unlike X", "X não considera", "X é limitado a" — todos contam.
`supporting` é o citante que se apoia no artigo ou relata seu achado como válido;
`none` é a menção sem postura (bloco genérico, referência só na bibliografia).

### Eixo 4 — ACCURACY: o citante diz o que o artigo diz?

Só se aplica quando `presence = in_text`; caso contrário fica `null`. Compare o que a
passagem atribui ao artigo com o resumo e o registro de afirmações abaixo.

| Valor | Significado |
|---|---|
| `accurate` | O que é atribuído ao artigo corresponde ao que ele diz |
| `imprecise` | Leitura discutível, frouxa ou ampliada, mas não demonstravelmente falsa — um dado de outro país, uma generalização além do escopo, um achado lido numa direção que o artigo não afirma com clareza (no v1: flag `weak`) |
| `misrepresented` | O artigo é citado para algo que ele não diz — objeto, método ou achado errado (no v1: `wrongly_interpreted` / `misattribution`) |

**Sub-código DISTORTION** (Greenberg, 2009, *BMJ* 339:b2680), obrigatório quando
`accuracy != accurate` e `null` quando `accurate`:

| Valor | Significado |
|---|---|
| `dead_end` | O artigo é usado para sustentar uma afirmação sobre a qual ele não tem conteúdo relevante (política de concorrência nos Bálcãs; um dado sobre Gana) |
| `diversion` | O conteúdo do artigo é citado, mas com significado diferente do original ("investiga a estrutura de custo da companhia") |
| `transmutation` | Uma hipótese, conjectura ou limitação do artigo vira fato estabelecido na citação |
| `relayed_attribution` | O citante atribui ao artigo, como achado próprio, algo que o artigo apenas repassa de terceiros (afirmações marcadas REPASSADO no registro: "20–35% dos grãos perdidos" é Gustavsson et al., 2011) |

### Eixo 5 — REUSE: reuso efetivo (multi-rótulo)

`method_adoption` · `result_validated` · `dataset_reuse` · `benchmarking` · `work_extended`

Só marcado quando o citante **usa** o trabalho, não quando apenas o menciona. É o sinal
mais forte de impacto real. A régua é: **o citante mudaria de desenho se o artigo não
existisse?** Se a resposta é não, a lista fica vazia.

| Tag | Quando marcar |
|---|---|
| `method_adoption` | Adota do artigo um método, especificação, variável, instrumento, teste ou definição operacional como base do próprio desenho |
| `result_validated` | Usa o achado do artigo para validar ou confrontar o próprio resultado ("encontramos o mesmo que…") |
| `dataset_reuse` | Usa a mesma fonte de dados por causa do artigo |
| `benchmarking` | Compara quantitativamente os próprios números com os do artigo |
| `work_extended` | Declara estender o modelo, a pergunta ou o desenho do artigo |

### Eixos que NÃO entram no teste cego

`relation` (independent / coauthor / self), `record_flags` (duplicate_publication) e
`highlight` (none / good / best) exigem metadados de autoria ou são editoriais. Não os
codifique.

### CLAIM_IDS: que afirmações do artigo a passagem invoca

Escolha no registro de afirmações (abaixo) os ids do que a passagem atribui ao artigo —
o que o citante diz que o artigo diz, independentemente de estar certo. Lista vazia
quando `presence != in_text` ou quando a menção é genérica demais para apontar uma
afirmação. Uma afirmação REPASSADO escolhida junto com `accuracy = accurate` significa
que o citante atribuiu corretamente a terceiros; escolhida com `relayed_attribution`
significa que atribuiu ao artigo o que era de terceiros.
"""

V1_TO_V2_MD = """### Tradução dos termos v1 usados nos casos acima

| Termo no caso de fronteira (v1) | Codificação v2 |
|---|---|
| `contradictory` / `supporting` (stance) | `stance = contradictory` / `stance = supporting` — inalterado |
| `wrongly_interpreted` | `presence = in_text`, `depth` pelo que o citante faz (em geral `brief_mention`), `accuracy = misrepresented` + `distortion` |
| `weak` | `accuracy = imprecise` + `distortion` |
| `method_adoption` | `reuse` contém `method_adoption` (e `depth >= supporting`, porque sustenta o desenho) |
| `brief_mention`, `drive_by` | `depth = brief_mention` (2), `depth = drive_by` (1) |
| `bibliography_only` | `presence = reference_list_only`, `depth = null`, `accuracy = null` |
| `evidencia_insuficiente` | não ocorre no pacote — todo item tem corpo verificado ou passagem literal |
| autocitação / coautor | não codificado no teste cego (eixo `relation`) |
"""


def build_instructions(
    method_text, abstracts, papers, claims, n_items, n_batches, sizes
):
    boundary = extract_section(method_text, "Codebook: os casos de fronteira", number=6)
    parts = []
    parts.append(
        "# Instruções para o segundo codificador — teste cego de confiabilidade\n"
    )
    parts.append("""## 1. Seu papel

Você é o **segundo codificador independente** de uma auditoria da qualidade das citações
recebidas por dois artigos. O primeiro codificador já classificou os mesmos itens; você
não verá essa classificação, e ela não verá a sua até o cálculo da concordância. Regras:

- Codifique **só a partir do que está no item**: as passagens e o título do trabalho
  citante. Não procure o artigo citante na internet, não abra o PDF, não use o título
  para inferir veículo, ano ou autores. A identificação foi retirada de propósito.
- Não discuta itens com o primeiro codificador antes de entregar.
- Use este documento como único codebook. Se um item não couber em nenhuma regra,
  decida mesmo assim, registre `confidence = 1` e explique na `rationale`.
- Alguns itens aparecem duas vezes sob ids diferentes. Isso é intencional (sonda de
  consistência). Não procure os pares; codifique cada item como se fosse novo.
- Os dois artigos avaliados são sempre os mesmos (abaixo). A passagem cita um deles —
  o campo `paper` diz qual — por sobrenome e ano (`Bendinelli et al., 2016` ou
  `2020`, às vezes `2019`), por número (`[12]`) ou por sobrescrito.
""")
    parts.append(f"""## 2. O que há no pacote

`pack_blind.json` é uma lista de {n_batches} lotes ({", ".join(str(s) for s in sizes)} itens; {n_items} no total). Cada item:

| Campo | Conteúdo |
|---|---|
| `item_id` | identificador opaco (`IRR-xxxx`) — copie-o exatamente na saída |
| `paper` | `airline` ou `grains`: qual dos dois artigos é o citado |
| `citing_title` | título do trabalho citante |
| `passages` | trechos do texto citante onde o artigo aparece. Origem `auto`: janelas automáticas de ±700 caracteres em torno do sobrenome, cortadas no meio de frase e às vezes com sujeira de tabela ou cabeçalho — leia o miolo; origem `curated`: o trecho exato selecionado na leitura |
| `n_passages` | número de trechos |
| `passage_source` | `auto` ou `curated` |
| `citation_style` | `numeric` (o artigo é um número entre colchetes ou sobrescrito) ou `author_year` |

**Item sem passagem (`n_passages = 0`)**: o corpo completo do citante foi obtido e
verificado, e a busca pelo sobrenome não encontrou menção no corpo — o artigo consta só
na lista de referências. Codifique `presence = reference_list_only`; os demais eixos
ficam `null`/vazios e `stance = none`. Alguns itens trazem como passagem um trecho da
própria lista de referências (entradas bibliográficas em sequência): a decisão é a
mesma. Registre isso na `rationale`. Como nesses itens o eixo de presença é determinado
pela construção do pacote e não por julgamento independente, a concordância em
`presence` é reportada só como concordância bruta.

**Passagem em bloco numérico** (`[5,21,22,23]`, `[17] [18]`): o artigo é um dos números.
Isso é `in_text`; a profundidade costuma ser `drive_by` ou `brief_mention`, conforme a
afirmação seja genérica ou específica.
""")
    parts.append(TAXONOMY_V2_MD)
    parts.append("## Codebook: os casos de fronteira (METHOD.md, literal)\n")
    parts.append(boundary + "\n")
    parts.append(V1_TO_V2_MD)
    parts.append("""## 3. Ordem de decisão

Decida os eixos nesta ordem, um de cada vez, sem voltar atrás para "acertar" o conjunto:

1. **presence** — há menção no corpo? (`in_text` / `reference_list_only`). Se não há,
   pare aqui: `depth = null`, `accuracy = null`, `distortion = null`, `reuse = []`,
   `claim_ids = []`, `stance = none`.
2. **depth** — o que o citante faz com o artigo (1 a 5), ignorando se está certo.
3. **stance** — postura, pela regra liberal.
4. **accuracy** — compare o que é atribuído ao artigo com o resumo e o registro de
   afirmações; se `imprecise` ou `misrepresented`, escolha o **distortion**.
5. **reuse** — aplique a régua: o citante mudaria de desenho se o artigo não existisse?
6. **claim_ids** — ids do registro de afirmações que a passagem invoca.

Depois, `confidence` (1 = chute informado, 2 = razoável, 3 = seguro) e `rationale`
(até 30 palavras, em português, citando as palavras da passagem que decidiram).
""")
    parts.append("## 4. Os dois artigos avaliados\n")
    for key in ("airline", "grains"):
        p = papers.get(key) or {}
        parts.append(f"### `{key}` — {p.get('title') or key}\n")
        parts.append(
            f"*{p.get('authors', 'Bendinelli et al.')}, {p.get('venue', '')} ({p.get('year', '')})*\n"
        )
        ab = abstracts.get(key)
        parts.append(
            "**Resumo (abstract original):** " + (ab or "(resumo indisponível)") + "\n"
        )
    parts.append("""## 5. Registro de afirmações (claims.json)

Cada afirmação tem um id. `AIR-*` pertence ao artigo `airline`, `GR-*` ao artigo
`grains`. As marcadas REPASSADO são o que o próprio artigo atribui a terceiros — se o
citante as atribui ao artigo como achado próprio, é `relayed_attribution`.
""")
    for key in ("airline", "grains"):
        parts.append(f"### Artigo `{key}`\n")
        for c in claims:
            if c.get("paper") == key:
                parts.append(f"- **{c['id']}** — {c['text']}")
        parts.append("")
    parts.append("""## 6. Contrato de saída (estrito)

Entregue **um único arquivo JSON**, `irr_c2_<seu_nome>.json`, um objeto cujas chaves são
os `item_id` de todos os lotes e cujos valores seguem exatamente este formato:

```json
{
 "IRR-a1b2": {
  "presence": "in_text",
  "depth": "brief_mention",
  "stance": "supporting",
  "accuracy": "imprecise",
  "distortion": "dead_end",
  "reuse": [],
  "claim_ids": ["GR-R01"],
  "confidence": 2,
  "rationale": "Atribui ao artigo um dado sobre Gana que ele não contém."
 }
}
```

Regras de validação (o script de estatística rejeita o que não cumprir):

| Campo | Valores |
|---|---|
| `presence` | `in_text` · `reference_list_only` · `not_cited` |
| `depth` | `drive_by` · `brief_mention` · `real_mention` · `supporting` · `foundational`; **`null` se `presence != in_text`** |
| `stance` | `supporting` · `contradictory` · `none` |
| `accuracy` | `accurate` · `imprecise` · `misrepresented`; **`null` se `presence != in_text`** |
| `distortion` | `dead_end` · `diversion` · `transmutation` · `relayed_attribution`; **`null` se `accuracy` é `accurate` ou `null`** |
| `reuse` | lista (pode ser vazia) de `method_adoption` · `result_validated` · `dataset_reuse` · `benchmarking` · `work_extended`; vazia se `presence != in_text` |
| `claim_ids` | lista (pode ser vazia) de ids do registro; vazia se `presence != in_text` |
| `confidence` | inteiro 1, 2 ou 3 |
| `rationale` | texto de até 30 palavras |

Todos os `item_id` do pacote devem aparecer. Não acrescente campos. Não altere os ids.
""")
    return "\n".join(parts)


# ---------------- auditoria de vazamento ----------------


def audit(root):
    irr = root / "data" / "irr"
    pack = load_json(irr / "pack_blind.json")
    key = load_json(irr / "pack_key.json")
    master = envelope(load_json(root / "data" / "master.json"), "papers")
    recs = master_records(master)
    venues = sorted(
        {(r.get("venue") or "").strip() for _, r in recs.values() if r.get("venue")},
        key=len,
        reverse=True,
    )
    long_venues = [v for v in venues if len(v.split()) >= 3]
    leaks, info = (
        [],
        {"doi_de_terceiros_em_passagens": 0, "itens": 0, "lotes": len(pack)},
    )
    seen = set()
    for b, batch in enumerate(pack, 1):
        for it in batch:
            info["itens"] += 1
            iid = it.get("item_id")
            if iid in seen:
                leaks.append((iid, "item_id repetido no pacote"))
            seen.add(iid)
            if iid not in key:
                leaks.append((iid, "item_id sem entrada na chave"))
                continue
            k = key[iid]
            bad_keys = set(it) & FORBIDDEN_ITEM_KEYS
            if bad_keys:
                leaks.append((iid, f"campos proibidos no item: {sorted(bad_keys)}"))
            extra = set(it) - set(ITEM_KEYS)
            if extra:
                leaks.append((iid, f"campos inesperados no item: {sorted(extra)}"))
            passages = it.get("passages") or []
            outside = json.dumps(
                {kk: v for kk, v in it.items() if kk != "passages"}, ensure_ascii=False
            )
            inside = "\n".join(passages)
            # DOI
            if DOI_PATTERN.search(outside):
                leaks.append((iid, "padrão de DOI fora das passagens"))
            own_doi = (k.get("doi") or "").lower()
            if own_doi and own_doi in inside.lower():
                leaks.append((iid, "DOI do próprio citante dentro de uma passagem"))
            info["doi_de_terceiros_em_passagens"] += len(DOI_PATTERN.findall(inside))
            # veículo
            own_venue = (
                (recs.get(own_doi) or (None, {}))[1].get("venue") or ""
            ).strip()
            if own_venue and len(own_venue) >= 4:
                pat = re.compile(
                    r"(?<![A-Za-z])" + re.escape(own_venue) + r"(?![A-Za-z])",
                    re.IGNORECASE,
                )
                if pat.search(outside):
                    leaks.append(
                        (
                            iid,
                            f"veículo do próprio citante fora das passagens: {own_venue!r}",
                        )
                    )
                if pat.search(inside):
                    leaks.append(
                        (
                            iid,
                            f"veículo do próprio citante dentro de uma passagem: {own_venue!r}",
                        )
                    )
            for v in long_venues:
                if re.search(
                    r"(?<![A-Za-z])" + re.escape(v) + r"(?![A-Za-z])",
                    outside,
                    re.IGNORECASE,
                ):
                    leaks.append(
                        (
                            iid,
                            f"nome de veículo (>= 3 palavras) fora das passagens: {v!r}",
                        )
                    )
            # ano junto de "et al." no título
            title = it.get("citing_title") or ""
            if re.search(r"et al\.?,?\s*\(?\s*(19|20)\d\d", title, re.IGNORECASE):
                leaks.append((iid, "ano junto de 'et al.' no título"))
            # palavras de rótulo fora das passagens
            m = LABEL_WORDS.search(outside)
            if m:
                leaks.append(
                    (iid, f"palavra de rótulo fora das passagens: {m.group(0)!r}")
                )
            # coerência com a chave
            if k.get("batch") != b:
                leaks.append(
                    (iid, f"lote na chave ({k.get('batch')}) != lote no pacote ({b})")
                )
    for iid, k in key.items():
        if iid not in seen:
            leaks.append((iid, "item da chave ausente do pacote"))
        d = k.get("duplicate_of")
        if d and (d not in key or key[d].get("doi") != k.get("doi")):
            leaks.append((iid, "duplicata inconsistente com o original"))
    n_dup = sum(1 for k in key.values() if k.get("duplicate_of"))
    print(
        f"== Auditoria de cegueira: {info['itens']} itens em {info['lotes']} lotes, {n_dup} duplicatas"
    )
    print(
        f"  DOIs de terceiros dentro de passagens (permitidos, informativo): {info['doi_de_terceiros_em_passagens']}"
    )
    print(
        f"  passagens com DOI/veículo do próprio citante apagados na montagem: "
        f"{sum(k.get('n_scrubbed', 0) for k in key.values() if not k.get('duplicate_of'))}"
    )
    if leaks:
        print(f"  VAZAMENTOS: {len(leaks)}")
        for iid, msg in leaks:
            print(f"    {iid}: {msg}")
        return 1
    print("  VAZAMENTOS: 0")
    return 0


# ---------------- principal ----------------


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--seed", type=int, default=SEED_DEFAULT)
    ap.add_argument("--n-dup", type=int, default=10)
    ap.add_argument("--n-batches", type=int, default=4)
    ap.add_argument(
        "--audit", action="store_true", help="só audita o pacote já gravado"
    )
    args = ap.parse_args(argv)
    root = args.root.resolve()
    if args.audit:
        return audit(root)

    data = root / "data"
    classify = envelope(load_json(data / "classify.json"), "entries")
    if not all("presence" in e for e in classify["entries"].values()):
        raise SystemExit(
            "classify.json não está no codebook v2 — rode audit_60_taxonomy_v2.py antes"
        )
    master = envelope(load_json(data / "master.json"), "papers")
    claims = load_json(data / "claims" / "claims.json")
    if isinstance(claims, dict):
        claims = claims.get("claims") or []
    method_text = (root / "METHOD.md").read_text(encoding="utf-8")
    config = load_json(root / "config.json") if (root / "config.json").exists() else {}
    surname = config.get("author_surname") or "Bendinelli"
    recs = master_records(master)

    papers = {}
    for key in ("airline", "grains"):
        target = (master["papers"].get(key) or {}).get("target") or {}
        cfg = (config.get("papers") or {}).get(key) or {}
        papers[key] = {
            "title": target.get("title") or cfg.get("title") or key,
            "venue": target.get("venue") or cfg.get("venue") or "",
            "year": target.get("year") or cfg.get("year") or "",
            "authors": target.get("authors") or "Bendinelli et al.",
        }
    abstracts, abstract_source = {}, {}
    for key in ("airline", "grains"):
        src = data / "claims" / "source_text" / f"{key}.txt"
        ab = (
            extract_abstract(src.read_text(encoding="utf-8", errors="ignore"))
            if src.exists()
            else None
        )
        if ab:
            abstract_source[key] = "source_text"
        else:
            quotes = [
                c["quote"]
                for c in claims
                if c.get("paper") == key
                and c.get("status") == "original"
                and c.get("quote")
            ]
            ab = (
                "(resumo reconstruído a partir das citações literais do registro de afirmações) "
                + " ".join(quotes)
            )
            abstract_source[key] = "claims_quotes"
        abstracts[key] = ab

    items, meta, taken = build_items(classify, recs, surname, args.seed)
    batches, dup_pairs = make_pack(
        items, meta, taken, args.seed, args.n_dup, args.n_batches
    )
    sizes = [len(b) for b in batches]
    n_items = sum(sizes)

    c1 = {}
    for iid, k in meta.items():
        c1[iid] = labels_of(classify["entries"][k["doi"]])

    instructions = build_instructions(
        method_text, abstracts, papers, claims, n_items, args.n_batches, sizes
    )

    irr = data / "irr"
    irr.mkdir(parents=True, exist_ok=True)
    dump_json(batches, irr / "pack_blind.json")
    dump_json(meta, irr / "pack_key.json")
    dump_json(c1, irr / "irr_c1_from_v2.json")
    (irr / "instructions.md").write_text(instructions, encoding="utf-8")

    n_auto = sum(
        1
        for k in meta.values()
        if not k["duplicate_of"] and k["passage_source"] == "auto"
    )
    n_cur = sum(
        1
        for k in meta.values()
        if not k["duplicate_of"] and k["passage_source"] == "curated"
    )
    n_empty = sum(1 for it in items if it["n_passages"] == 0)
    n_ex = sum(
        1 for k in meta.values() if not k["duplicate_of"] and k["codebook_exemplar"]
    )
    styles = {}
    for it in items:
        styles[it["citation_style"]] = styles.get(it["citation_style"], 0) + 1
    print(
        f"== Pacote cego: {len(items)} itens originais + {len(dup_pairs)} duplicatas = {n_items}, "
        f"lotes {sizes}, semente {args.seed}"
    )
    print(
        f"  passagens: auto={n_auto} curated={n_cur}; itens sem passagem={n_empty}; "
        f"passagens limpas (DOI/veículo próprio)={sum(k['n_scrubbed'] for k in meta.values() if not k['duplicate_of'])}"
    )
    print(f"  estilo de citação: {styles}")
    print(f"  exemplares do codebook (excluídos das estatísticas primárias): {n_ex}")
    print(f"  resumos: {abstract_source}")
    print("  duplicatas (só na chave): " + ", ".join(f"{a}->{b}" for a, b in dup_pairs))
    print("== Gravados:")
    for p in (
        "pack_blind.json",
        "pack_key.json",
        "instructions.md",
        "irr_c1_from_v2.json",
    ):
        print(f"  {irr / p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
