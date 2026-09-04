"""audit_60_taxonomy_v2.py — migra a classificação v1 (um `role` de sete valores
mais uma `flag`) para os três eixos ortogonais do codebook v2, sem perda.

Fase 60 (análises). Lê `data/classify.json`, `data/classify_orfas.json`,
`data/master.json` e `METHOD.md`; grava os dois classify migrados e
`data/taxonomy_v2.json`. Só stdlib.

Esquema v2 por entrada (campos novos; `stance`, `reuse`, `note`, `passages` e
`prov` são mantidos; `role` e `flag` saem do topo e ficam em
`prov.migrated_from_v1`):

  presence       in_text | reference_list_only | not_cited
  depth          drive_by(1) < brief_mention(2) < real_mention(3) <
                 supporting(4) < foundational(5); null se presence != in_text
  accuracy       accurate | imprecise | misrepresented; null se presence != in_text
  distortion     sub-código de Greenberg (2009), só quando accuracy != accurate:
                 dead_end | diversion | transmutation | relayed_attribution;
                 null na migração (atribuído depois pelo mapeamento de claims)
  relation       independent | coauthor | self
  record_flags   lista ⊆ {duplicate_publication}
  highlight      none | good | best   (editorial; fora das estatísticas)
  claims         []  (preenchido depois)
  codebook_exemplar  true nos casos de fronteira nomeados em METHOD.md

Regras R1–R9 em MIGRATION_RULES. A projeção inversa `auditlib.role_flag_v1()`
reconstrói (role, flag) com a prioridade de flag observada nos dados, e o
script ABORTA antes de gravar se o round-trip não reproduzir os originais em
100% das entradas (104 vivas + 1 órfã).

Uso:
  python3 tools/audit_60_taxonomy_v2.py [--root PATH] [--dry-run]
                                        [--date AAAA-MM-DD] [--force]

`--root` é a raiz do repositório (padrão: inferida de __file__), para que o
mesmo script rode no diretório de estágio e no repositório real.
"""

import argparse
import collections
import datetime
import json
import re
import sys
from pathlib import Path

import auditlib

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
JSON_KW = {"sort_keys": True, "indent": 1, "ensure_ascii": False}

CODEBOOK_V1 = "METHOD.md@v1"
CODEBOOK_V2 = "METHOD.md@v2"

# ---------------- vocabulário v2 ----------------
PRESENCE = ["in_text", "reference_list_only", "not_cited"]
DEPTH = ["drive_by", "brief_mention", "real_mention", "supporting", "foundational"]
DEPTH_RANK = {v: i + 1 for i, v in enumerate(DEPTH)}
ACCURACY = ["accurate", "imprecise", "misrepresented"]
DISTORTION = ["dead_end", "diversion", "transmutation", "relayed_attribution"]
RELATION = ["independent", "coauthor", "self"]
RECORD_FLAGS = ["duplicate_publication"]
HIGHLIGHT = ["none", "good", "best"]
STANCE = ["none", "supporting", "contradictory"]
REUSE = [
    "method_adoption",
    "result_validated",
    "dataset_reuse",
    "benchmarking",
    "work_extended",
]
V2_FIELDS = (
    "presence",
    "depth",
    "accuracy",
    "distortion",
    "relation",
    "record_flags",
    "highlight",
    "claims",
    "codebook_exemplar",
)
PROV_V2_KEYS = ("migrated_from_v1", "migration_rules", "adjudicated", "depth_basis")

# ---------------- vocabulário v1 ----------------
V1_ROLES = [
    "bibliography_only",
    "drive_by",
    "brief_mention",
    "real_mention",
    "supporting",
    "foundational",
    "wrongly_interpreted",
]
V1_FLAGS = [
    "ghost",
    "critical",
    "weak",
    "good",
    "misattribution",
    "duplicate",
    "best",
    "coautor",
    "autocitacao",
]
# Prioridade observada nos dados para a flag única do v1 — é a ordem que
# auditlib.role_flag_v1() usa quando mais de um eixo v2 poderia gerar uma flag.
V1_FLAG_PRIORITY = [
    "ghost",
    "misattribution",
    "weak",
    "duplicate",
    "coautor",
    "autocitacao",
    "best",
    "good",
    "critical",
    "",
]

MIGRATION_RULES = [
    {
        "id": "R1",
        "when": "role == bibliography_only (flag ghost é absorvida)",
        "then": "presence = reference_list_only; depth = null; accuracy = null",
    },
    {
        "id": "R2",
        "when": "role não é bibliography_only nem wrongly_interpreted",
        "then": "presence = in_text; depth = role",
    },
    {
        "id": "R3",
        "when": "role == wrongly_interpreted",
        "then": "presence = in_text; accuracy = misrepresented; depth = brief_mention "
        "com prov.depth_basis = migration_rule_R3",
    },
    {"id": "R4", "when": "flag == weak", "then": "accuracy = imprecise"},
    {
        "id": "R5",
        "when": "flag == misattribution",
        "then": "accuracy = misrepresented (conjunto R5 tem de ser igual ao conjunto R3)",
    },
    {
        "id": "R6",
        "when": "flag in {coautor, autocitacao}",
        "then": "relation = coauthor | self",
    },
    {
        "id": "R7",
        "when": "flag == duplicate",
        "then": "record_flags = [duplicate_publication]",
    },
    {"id": "R8", "when": "flag in {good, best}", "then": "highlight = flag"},
    {
        "id": "R9",
        "when": "flag == critical",
        "then": "descartada — 100% redundante com stance == contradictory (verificado na migração)",
    },
    {
        "id": "R0",
        "when": "padrão",
        "then": "accuracy = accurate para in_text não tocado por R3/R4/R5; relation = independent; "
        "record_flags = []; highlight = none; distortion = null; claims = []",
    },
]

# Casos de fronteira de METHOD.md ("Codebook: os casos de fronteira"). O ano
# citado em METHOD.md ora é o do DOI (j.tra.2018.10.005 -> "TR-A 2018"), ora o
# do registro em master.json; o casamento aceita qualquer um dos dois e exige
# a citação literal e a assinatura v1, com exatamente um candidato.
EXEMPLARS = [
    {
        "case": "contraposicao_sem_hostilidade",
        "method_ref": 'TR-A 2018 — "In contrast to these studies, this work investigates…"',
        "paper": "airline",
        "venue_prefix": "Transportation Research Part A",
        "year": 2018,
        "quote": "In contrast to these studies",
        "v1": {"stance": "contradictory"},
    },
    {
        "case": "verbo_de_distanciamento_nao_basta",
        "method_ref": 'JATM 2022 — "Still Bendinelli et al. claim that there is little evidence…"',
        "paper": "airline",
        "venue_prefix": "Journal of Air Transport Management",
        "year": 2022,
        "quote": "Still Bendinelli",
        "v1": {"stance": "supporting"},
    },
    {
        "case": "wrongly_interpreted_versus_weak/misrepresented",
        "method_ref": "JATM 2019 — estrutura de custo (objeto errado)",
        "paper": "airline",
        "venue_prefix": "Journal of Air Transport Management",
        "year": 2019,
        "quote": "cost structure",
        "v1": {"role": "wrongly_interpreted"},
    },
    {
        "case": "wrongly_interpreted_versus_weak/imprecise",
        "method_ref": "Transport Policy 2019 — leitura do resultado sobre LCC como positivo",
        "paper": "airline",
        "venue_prefix": "Transport Policy",
        "year": 2019,
        "quote": "Bubalo and Gaggero",
        "v1": {"flag": "weak"},
    },
    {
        "case": "method_adoption_versus_brief_mention/method_adoption",
        "method_ref": "TR-E 2020 — adota o tratamento de endogeneidade e instrumenta HHI",
        "paper": "airline",
        "venue_prefix": "Transportation Research Part E",
        "year": 2020,
        "quote": "endogenous",
        "v1": {"reuse": "method_adoption"},
    },
    {
        "case": "method_adoption_versus_brief_mention/brief_mention",
        "method_ref": "Economics of Transportation 2022 — bloco de oito referências",
        "paper": "airline",
        "venue_prefix": "Economics of Transportation",
        "year": 2022,
        "quote": "control variables",
        "v1": {"role": "brief_mention"},
    },
    {
        "case": "drive_by_versus_brief_mention/drive_by",
        "method_ref": 'grãos — "cereais são componentes vitais da alimentação"',
        "paper": "grains",
        "quote": "vital components",
        "v1": {"role": "drive_by"},
    },
]

# Crosswalk para os esquemas publicados. Chaves fixas em todas as linhas;
# None = sem equivalente naquele esquema.
_SCHEMES = [
    "moravcsik_murugesan_1975",
    "teufel_2006",
    "jurgens_2018",
    "scicite_cohan_2019",
    "valenzuela_2015",
    "cito",
]


def _xw(
    axis,
    value,
    mm=None,
    teufel=None,
    jurgens=None,
    scicite=None,
    valenzuela=None,
    cito=None,
    note=None,
):
    return {
        "axis": axis,
        "value": value,
        "moravcsik_murugesan_1975": mm,
        "teufel_2006": teufel,
        "jurgens_2018": jurgens,
        "scicite_cohan_2019": scicite,
        "valenzuela_2015": valenzuela,
        "cito": cito,
        "note": note,
    }


CROSSWALK = [
    _xw(
        "depth",
        "drive_by",
        ["perfunctory"],
        ["Neut"],
        ["Background"],
        ["background"],
        "incidental",
        ["citesForInformation"],
    ),
    _xw(
        "depth",
        "brief_mention",
        ["perfunctory"],
        ["Neut", "PMot"],
        ["Background"],
        ["background"],
        "incidental",
        ["citesAsAuthority"],
    ),
    _xw(
        "depth",
        "real_mention",
        ["organic"],
        ["PMot", "PSim"],
        ["Background", "Motivation"],
        ["background"],
        "incidental",
        ["describes"],
    ),
    _xw(
        "depth",
        "supporting",
        ["organic"],
        ["PBas", "PUse", "PSup"],
        ["Uses", "Motivation"],
        ["method", "background"],
        "important",
        ["usesMethodIn", "citesAsEvidence"],
        "SciCite: method quando há reuso metodológico, background quando só sustenta argumento",
    ),
    _xw(
        "depth",
        "foundational",
        ["organic", "evolutionary"],
        ["PBas", "PModi"],
        ["Extends", "Uses"],
        ["method", "result"],
        "important",
        ["extends"],
    ),
    _xw(
        "stance",
        "supporting",
        ["confirmative"],
        ["PSup"],
        None,
        ["result"],
        None,
        ["supports"],
    ),
    _xw(
        "stance",
        "contradictory",
        ["negational"],
        ["CoCo-", "Weak"],
        ["CompareOrContrast"],
        ["result"],
        None,
        ["disagreesWith"],
    ),
    _xw(
        "stance",
        "none",
        None,
        ["Neut"],
        None,
        None,
        None,
        None,
        "sem postura declarada; equivale ao Neut de Teufel quando não há PMot/PSup",
    ),
    _xw(
        "reuse",
        "method_adoption",
        ["organic"],
        ["PUse"],
        ["Uses"],
        ["method"],
        "important",
        ["usesMethodIn"],
    ),
    _xw(
        "reuse",
        "result_validated",
        ["organic", "confirmative"],
        ["PSup", "CoCoR0"],
        ["CompareOrContrast"],
        ["result"],
        "important",
        ["confirms"],
    ),
    _xw(
        "reuse",
        "dataset_reuse",
        ["organic"],
        ["PUse"],
        ["Uses"],
        ["method"],
        "important",
        ["usesDataFrom"],
    ),
    _xw(
        "reuse",
        "benchmarking",
        ["organic"],
        ["CoCoR0"],
        ["CompareOrContrast"],
        ["result"],
        "important",
        ["citesAsRelated"],
    ),
    _xw(
        "reuse",
        "work_extended",
        ["organic", "evolutionary"],
        ["PBas", "PModi"],
        ["Extends"],
        ["method"],
        "important",
        ["extends"],
    ),
    _xw(
        "presence",
        "in_text",
        None,
        None,
        None,
        None,
        None,
        None,
        "fora dos esquemas de função; base de comparação: Boyack et al. 2018 (menções no corpo)",
    ),
    _xw(
        "presence",
        "reference_list_only",
        None,
        None,
        None,
        None,
        None,
        None,
        "Boyack et al. 2018: referência não mencionada no corpo (1,4% no corpus Elsevier)",
    ),
    _xw(
        "presence",
        "not_cited",
        None,
        None,
        None,
        None,
        None,
        None,
        "aresta falsa do grafo de citações; sem equivalente",
    ),
    _xw(
        "accuracy",
        "accurate",
        None,
        None,
        None,
        None,
        None,
        None,
        "eixo de veridicidade — fora dos esquemas de função (Jergas & Baethge 2015)",
    ),
    _xw(
        "accuracy",
        "imprecise",
        None,
        None,
        None,
        None,
        None,
        None,
        "erro menor de citação (Jergas & Baethge 2015, categoria minor)",
    ),
    _xw(
        "accuracy",
        "misrepresented",
        None,
        None,
        None,
        None,
        None,
        None,
        "erro maior de citação; sub-códigos de Greenberg 2009 em `distortion`",
    ),
    _xw(
        "distortion",
        "dead_end",
        None,
        None,
        None,
        None,
        None,
        None,
        "Greenberg 2009: dead-end citation — a fonte não tem conteúdo relevante para a afirmação",
    ),
    _xw(
        "distortion",
        "diversion",
        None,
        None,
        None,
        None,
        None,
        None,
        "Greenberg 2009: citation diversion — conteúdo citado com significado diferente",
    ),
    _xw(
        "distortion",
        "transmutation",
        None,
        None,
        None,
        None,
        None,
        None,
        "Greenberg 2009: citation transmutation — hipótese vira fato pela citação",
    ),
    _xw(
        "distortion",
        "relayed_attribution",
        None,
        None,
        None,
        None,
        None,
        None,
        "extensão local: atribui ao artigo, como achado próprio, o que ele repassa de terceiros",
    ),
    _xw(
        "relation",
        "coauthor",
        None,
        None,
        None,
        None,
        None,
        None,
        "citação de coautor — literatura de autocitação, fora dos esquemas de função",
    ),
    _xw("relation", "self", None, None, None, None, None, None, "autocitação"),
]

SCHEME_VOCABULARIES = {
    "moravcsik_murugesan_1975": {
        "depth": ["organic", "perfunctory"],
        "lineage": ["evolutionary", "juxtapositional"],
        "stance": ["confirmative", "negational"],
    },
    "teufel_2006": [
        "Weak",
        "CoCoGM",
        "CoCoR0",
        "CoCo-",
        "CoCoXY",
        "PBas",
        "PUse",
        "PModi",
        "PMot",
        "PSim",
        "PSup",
        "Neut",
    ],
    "jurgens_2018": [
        "Background",
        "Uses",
        "Extends",
        "Motivation",
        "CompareOrContrast",
        "Future",
    ],
    "scicite_cohan_2019": ["background", "method", "result"],
    "valenzuela_2015": ["incidental", "important"],
    "cito": [
        "citesForInformation",
        "citesAsAuthority",
        "usesMethodIn",
        "usesDataFrom",
        "extends",
        "confirms",
        "supports",
        "disagreesWith",
        "citesAsRelated",
        "describes",
        "citesAsEvidence",
    ],
}


# ---------------- E/S ----------------


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, **JSON_KW)
        f.write("\n")


def envelope(raw, key):
    """Aceita o v1 plano ou o v2 com `meta`; devolve sempre {"meta", key}."""
    if isinstance(raw, dict) and "meta" in raw and key in raw:
        return raw
    return {"meta": {"schema": 1}, key: raw}


def master_records(master):
    """dict doi minúsculo -> (paper_key, registro)."""
    recs = {}
    for paper, block in master["papers"].items():
        for rec in block["citing"]:
            doi = (rec.get("doi") or "").strip().lower()
            if doi:
                recs[doi] = (paper, rec)
    return recs


# ---------------- migração ----------------


def v1_view(entry):
    """(role, flag, base sem role/flag). Aceita entrada v1 ou v2 já migrada — no
    segundo caso reconstrói a visão v1 a partir de prov.migrated_from_v1."""
    if "presence" in entry:
        mig = (entry.get("prov") or {}).get("migrated_from_v1")
        if not mig:
            raise SystemExit(
                "entrada v2 sem prov.migrated_from_v1 — impossível re-migrar"
            )
        base = {k: v for k, v in entry.items() if k not in V2_FIELDS}
        prov = dict(base.get("prov") or {})
        for k in PROV_V2_KEYS:
            prov.pop(k, None)
        prov["codebook"] = CODEBOOK_V1
        base["prov"] = prov
        return mig["role"], mig["flag"] or None, base
    base = {k: v for k, v in entry.items() if k not in ("role", "flag")}
    return entry.get("role"), (entry.get("flag") or None), base


def migrate_entry(role, flag, base):
    """Aplica R1–R9 a uma entrada; devolve (entrada v2, regras aplicadas)."""
    if role not in V1_ROLES:
        raise ValueError(f"role v1 desconhecido: {role!r}")
    if flag is not None and flag not in V1_FLAGS:
        raise ValueError(f"flag v1 desconhecida: {flag!r}")
    rules = []
    presence = depth = accuracy = None
    relation, record_flags, highlight = "independent", [], "none"
    prov = dict(base.get("prov") or {})
    prov.pop("depth_basis", None)

    if role == "bibliography_only":
        presence = "reference_list_only"
        rules.append("R1")
    elif role == "wrongly_interpreted":
        presence, accuracy, depth = "in_text", "misrepresented", "brief_mention"
        prov["depth_basis"] = "migration_rule_R3"
        rules.append("R3")
    else:
        presence, depth, accuracy = "in_text", role, "accurate"
        rules.append("R2")

    if flag == "ghost":
        rules.append("R1")
    if flag == "weak":
        accuracy = "imprecise"
        rules.append("R4")
    if flag == "misattribution":
        accuracy = "misrepresented"
        rules.append("R5")
    if flag == "coautor":
        relation = "coauthor"
        rules.append("R6")
    if flag == "autocitacao":
        relation = "self"
        rules.append("R6")
    if flag == "duplicate":
        record_flags = ["duplicate_publication"]
        rules.append("R7")
    if flag in ("good", "best"):
        highlight = flag
        rules.append("R8")
    if flag == "critical":
        rules.append("R9")

    if presence != "in_text" and (depth is not None or accuracy is not None):
        raise ValueError(f"role={role} flag={flag}: depth/accuracy fora de in_text")

    prov.update(
        {
            "codebook": CODEBOOK_V2,
            "migrated_from_v1": {"role": role, "flag": flag},
            "migration_rules": sorted(set(rules)),
            "adjudicated": False,
        }
    )
    out = dict(base)
    out.update(
        {
            "presence": presence,
            "depth": depth,
            "accuracy": accuracy,
            "distortion": None,
            "relation": relation,
            "record_flags": record_flags,
            "highlight": highlight,
            "claims": [],
            "codebook_exemplar": False,
            "prov": prov,
        }
    )
    return out, rules


def migrate_entries(entries, label):
    """Migra um dict doi -> entrada; devolve (dict v2, relatório)."""
    out, report = (
        {},
        {
            "n": len(entries),
            "R3": set(),
            "R5": set(),
            "R9_flag_critical": set(),
            "stance_contradictory": set(),
            "ghost_flag": set(),
            "bib_only": set(),
            "rules": collections.Counter(),
        },
    )
    for doi, entry in entries.items():
        role, flag, base = v1_view(entry)
        v2, rules = migrate_entry(role, flag, base)
        out[doi] = v2
        for r in rules:
            report["rules"][r] += 1
        if role == "wrongly_interpreted":
            report["R3"].add(doi)
        if flag == "misattribution":
            report["R5"].add(doi)
        if flag == "critical":
            report["R9_flag_critical"].add(doi)
        if v2.get("stance") == "contradictory":
            report["stance_contradictory"].add(doi)
        if flag == "ghost":
            report["ghost_flag"].add(doi)
        if role == "bibliography_only":
            report["bib_only"].add(doi)
    report["label"] = label
    return out, report


def round_trip(entries_v1, entries_v2):
    """Confere auditlib.role_flag_v1(v2) == (role, flag) original para cada
    entrada."""
    failures = []
    for doi, entry in entries_v1.items():
        role, flag, _ = v1_view(entry)
        got = auditlib.role_flag_v1(entries_v2[doi])
        if got != (role, flag):
            failures.append((doi, (role, flag), got))
    return failures


# ---------------- exemplares do codebook ----------------


def doi_year(doi):
    m = re.search(r"\.((?:19|20)\d\d)\.", doi or "")
    return int(m.group(1)) if m else None


def resolve_exemplars(entries_v2, recs):
    found = []
    for spec in EXEMPLARS:
        cands = []
        for doi, e in entries_v2.items():
            paper, rec = recs[doi]
            if spec.get("paper") and paper != spec["paper"]:
                continue
            if spec.get("venue_prefix") and not (rec.get("venue") or "").startswith(
                spec["venue_prefix"]
            ):
                continue
            if spec.get("year") and spec["year"] not in (
                doi_year(doi),
                rec.get("year"),
            ):
                continue
            passages = e.get("passages") or []
            if spec.get("quote") and not any(
                spec["quote"].lower() in p.lower() for p in passages
            ):
                continue
            mig = e["prov"]["migrated_from_v1"]
            v1 = spec.get("v1") or {}
            if "role" in v1 and mig["role"] != v1["role"]:
                continue
            if "flag" in v1 and mig["flag"] != v1["flag"]:
                continue
            if "stance" in v1 and e.get("stance") != v1["stance"]:
                continue
            if "reuse" in v1 and v1["reuse"] not in (e.get("reuse") or []):
                continue
            cands.append(doi)
        if len(cands) != 1:
            raise SystemExit(
                f"exemplar {spec['case']!r}: esperado 1 candidato, achei {len(cands)}: {cands}"
            )
        doi = cands[0]
        paper, rec = recs[doi]
        found.append(
            {
                "case": spec["case"],
                "method_ref": spec["method_ref"],
                "doi": doi,
                "record_id": rec.get("id"),
                "paper": paper,
                "venue": rec.get("venue"),
                "year_master": rec.get("year"),
                "year_doi": doi_year(doi),
                "v1": entries_v2[doi]["prov"]["migrated_from_v1"],
                "v2": {
                    k: entries_v2[doi][k]
                    for k in ("presence", "depth", "accuracy", "stance", "reuse")
                },
            }
        )
    return found


# ---------------- relatório ----------------


def distribution(entries, field, multi=False):
    c = collections.Counter()
    for e in entries.values():
        v = e.get(field)
        if multi:
            for t in v or []:
                c[t] += 1
            if not v:
                c["(nenhum)"] += 1
        else:
            c["null" if v is None else str(v)] += 1
    return dict(sorted(c.items(), key=lambda kv: (-kv[1], kv[0])))


def print_dist(title, dist, order=None):
    print(f"  {title}:")
    keys = [k for k in (order or []) if k in dist] + [
        k for k in dist if k not in (order or [])
    ]
    for k in keys:
        print(f"    {k:<24} {dist[k]:>4}")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--root", type=Path, default=DEFAULT_ROOT, help="raiz do repositório"
    )
    ap.add_argument("--dry-run", action="store_true", help="não grava nada")
    hoje = datetime.datetime.now(tz=datetime.timezone.utc).date().isoformat()
    ap.add_argument("--date", default=hoje, help="data da migração (meta.migrated_at)")
    ap.add_argument(
        "--force",
        action="store_true",
        help="re-migra um classify já em v2 (a partir de prov.migrated_from_v1)",
    )
    args = ap.parse_args(argv)
    root = args.root.resolve()
    data = root / "data"

    classify = envelope(load_json(data / "classify.json"), "entries")
    orfas = envelope(load_json(data / "classify_orfas.json"), "entries")
    master = envelope(load_json(data / "master.json"), "papers")
    recs = master_records(master)

    already = any("presence" in e for e in classify["entries"].values())
    if already and not args.force:
        raise SystemExit(
            "classify.json já está no codebook v2 (campo `presence` presente). "
            "Use --force para re-migrar a partir de prov.migrated_from_v1."
        )
    if already:
        adj = [
            d
            for d, e in classify["entries"].items()
            if (e.get("prov") or {}).get("adjudicated")
        ]
        if adj:
            raise SystemExit(
                f"--force recusado: {len(adj)} entradas já adjudicadas seriam sobrescritas: {adj[:5]}"
            )

    print("== Migração v1 -> v2")
    live_v2, rep_live = migrate_entries(classify["entries"], "classify.json")
    orf_v2, rep_orf = migrate_entries(orfas["entries"], "classify_orfas.json")

    # Verificações de redundância (R5 == R3; R9 <-> stance; ghost <-> bibliography_only)
    ok = True
    for rep in (rep_live, rep_orf):
        lbl = rep["label"]
        if rep["R3"] != rep["R5"]:
            ok = False
            print(
                f"  ERRO {lbl}: conjunto R5 (misattribution) != conjunto R3 (wrongly_interpreted): "
                f"só-R3={sorted(rep['R3'] - rep['R5'])} só-R5={sorted(rep['R5'] - rep['R3'])}"
            )
        else:
            print(f"  {lbl}: R5 == R3 ({len(rep['R3'])} entradas) ok")
        if rep["R9_flag_critical"] != rep["stance_contradictory"]:
            ok = False
            print(
                f"  ERRO {lbl}: flag=critical NÃO é redundante com stance=contradictory: "
                f"só-critical={sorted(rep['R9_flag_critical'] - rep['stance_contradictory'])} "
                f"só-contradictory={sorted(rep['stance_contradictory'] - rep['R9_flag_critical'])}"
            )
        else:
            print(
                f"  {lbl}: R9 — flag=critical <=> stance=contradictory ({len(rep['R9_flag_critical'])} entradas) 100% redundante, descartada"
            )
        if rep["ghost_flag"] != rep["bib_only"]:
            ok = False
            print(
                f"  ERRO {lbl}: flag=ghost NÃO é redundante com role=bibliography_only"
            )
        else:
            print(
                f"  {lbl}: R1 — flag=ghost <=> role=bibliography_only ({len(rep['bib_only'])} entradas) ok"
            )
        print(f"  {lbl}: regras aplicadas {dict(sorted(rep['rules'].items()))}")

    # Round-trip
    fails = round_trip(classify["entries"], live_v2) + round_trip(
        orfas["entries"], orf_v2
    )
    n_total = len(live_v2) + len(orf_v2)
    if fails:
        ok = False
        print(f"  ROUND-TRIP FALHOU em {len(fails)}/{n_total} entradas:")
        for doi, orig, got in fails[:20]:
            print(f"    {doi}: original={orig} projetado={got}")
    else:
        print(
            f"  ROUND-TRIP OK: auditlib.role_flag_v1(v2) reproduz (role, flag) em "
            f"{n_total}/{n_total} entradas ({len(live_v2)} vivas + {len(orf_v2)} órfãs)"
        )
    if not ok:
        raise SystemExit("migração abortada: a projeção inversa não é sem perda")

    # Exemplares do codebook
    exemplars = resolve_exemplars(live_v2, recs)
    print("== Exemplares do codebook (METHOD.md, casos de fronteira)")
    for x in exemplars:
        live_v2[x["doi"]]["codebook_exemplar"] = True
        print(
            f"  {x['case']:<58} {x['doi']:<36} {x['record_id']}  [{x['v1']['role']}/{x['v1']['flag']}]"
        )

    # Distribuições
    print(f"== Distribuições (classify.json, n={len(live_v2)})")
    print_dist("presence", distribution(live_v2, "presence"), PRESENCE)
    print_dist("depth", distribution(live_v2, "depth"), DEPTH)
    print_dist("accuracy", distribution(live_v2, "accuracy"), ACCURACY)
    print_dist("distortion", distribution(live_v2, "distortion"), DISTORTION)
    print_dist("relation", distribution(live_v2, "relation"), RELATION)
    print_dist(
        "record_flags", distribution(live_v2, "record_flags", multi=True), RECORD_FLAGS
    )
    print_dist("highlight", distribution(live_v2, "highlight"), HIGHLIGHT)
    print_dist("stance", distribution(live_v2, "stance"), STANCE)
    print_dist("reuse", distribution(live_v2, "reuse", multi=True), REUSE)
    print_dist("codebook_exemplar", distribution(live_v2, "codebook_exemplar"))
    print(f"== Órfãs (classify_orfas.json, n={len(orf_v2)})")
    for doi, e in orf_v2.items():
        print(
            f"  {doi}: presence={e['presence']} depth={e['depth']} accuracy={e['accuracy']} "
            f"record_flags={e['record_flags']}"
        )

    # Saídas
    for env in (classify, orfas):
        meta = dict(env.get("meta") or {})
        meta.update(
            {
                "codebook": CODEBOOK_V2,
                "taxonomy": "v2",
                "migrated_from": CODEBOOK_V1,
                "migrated_at": args.date,
                "migration_tool": "audit_60_taxonomy_v2.py",
                "schema": max(2, int(meta.get("schema", 1))),
            }
        )
        env["meta"] = meta
    classify["entries"] = live_v2
    orfas["entries"] = orf_v2

    taxonomy = {
        "meta": {
            "codebook": CODEBOOK_V2,
            "version": "2.0",
            "generated_by": "audit_60_taxonomy_v2.py",
            "generated_at": args.date,
            "note": "Três eixos ortogonais (presence, depth, accuracy) + stance + reuse; "
            "highlight é editorial e fica fora das estatísticas.",
        },
        "axes": {
            "presence": {
                "type": "nominal",
                "values": PRESENCE,
                "null_when": None,
                "description": "onde o artigo aparece no citante",
            },
            "depth": {
                "type": "ordinal",
                "values": DEPTH,
                "ranks": DEPTH_RANK,
                "null_when": "presence != in_text",
                "description": "quanto o artigo importou para quem citou",
            },
            "accuracy": {
                "type": "nominal",
                "values": ACCURACY,
                "null_when": "presence != in_text",
                "description": "o citante diz o que o artigo diz?",
            },
            "distortion": {
                "type": "nominal",
                "values": DISTORTION,
                "null_when": "accuracy == accurate",
                "source": "Greenberg (2009) BMJ 339:b2680 + relayed_attribution (local)",
                "description": "mecanismo do erro; atribuído no mapeamento de claims",
            },
            "stance": {
                "type": "nominal",
                "values": STANCE,
                "null_when": None,
                "description": "postura do citante (regra liberal)",
            },
            "reuse": {
                "type": "multi-label",
                "values": REUSE,
                "null_when": None,
                "description": "reuso efetivo; só quando o citante USA o trabalho",
            },
            "relation": {
                "type": "nominal",
                "values": RELATION,
                "null_when": None,
                "description": "vínculo de autoria; coauthor/self ficam fora do reuso externo",
            },
            "record_flags": {
                "type": "multi-label",
                "values": RECORD_FLAGS,
                "null_when": None,
                "description": "sinais do registro, não da citação",
            },
            "highlight": {
                "type": "nominal",
                "values": HIGHLIGHT,
                "null_when": None,
                "editorial": True,
                "excluded_from_statistics": True,
            },
            "claims": {
                "type": "list",
                "values": "ids de data/claims/claims.json",
                "null_when": None,
            },
        },
        "migration_rules": MIGRATION_RULES,
        "v1_projection": {
            "flag_priority": V1_FLAG_PRIORITY,
            "role": "bibliography_only se presence == reference_list_only; "
            "wrongly_interpreted se accuracy == misrepresented; senão depth",
            "v1_roles": V1_ROLES,
            "v1_flags": V1_FLAGS,
        },
        "crosswalk": CROSSWALK,
        "scheme_vocabularies": SCHEME_VOCABULARIES,
        "codebook_exemplars": exemplars,
    }

    if args.dry_run:
        print("== --dry-run: nada gravado")
        return 0
    dump_json(classify, data / "classify.json")
    dump_json(orfas, data / "classify_orfas.json")
    dump_json(taxonomy, data / "taxonomy_v2.json")
    print("== Gravados:")
    for p in ("classify.json", "classify_orfas.json", "taxonomy_v2.json"):
        print(f"  {data / p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
