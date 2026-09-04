"""Etapa 41: tier de periódico.

Funde as duas etapas do round anterior (14_tiers + 15_scimago) num único
passe idempotente. Regra única, sempre recalculada do zero — nunca herda
`tier`/`tier_base` de uma rodada anterior:

  tier_proxy = corte por `citedness_2a` (2yr_mean_citedness do OpenAlex):
               T1 >= 6.0, T2 >= 3.5, T3 >= 2.0, senão T4.
  Se o ISSN casa com o CSV do Scimago -> tier = quartil do Scimago,
    tier_base = "Scimago SJR Best Quartile" (mesmo quando o Scimago não
    atribui quartil ao periódico naquele ano — o valor vem como "-").
  Senão -> tier = tier_proxy, tier_base = "proxy OpenAlex (sem
    correspondência no Scimago)".

Uso:
  python3 tools/audit_41_scimago.py           casa com o CSV e grava journals.json
  python3 tools/audit_41_scimago.py --check   só valida o journals.json já commitado (sem rede, sem CSV)
"""
import collections
import csv
import re
import sys

import auditlib

CORTES = [(6.0, "T1"), (3.5, "T2"), (2.0, "T3"), (0.0, "T4")]
SCIMAGO_CSV = auditlib.DATA / "scimago" / "scimagojr_2025.csv"


def tier_proxy_de(citedness):
    if citedness is None:
        return None
    for lim, t in CORTES:
        if citedness >= lim:
            return t
    return "T4"


def tier_e_base(tier_proxy, scimago):
    """A regra única de tier — mesma função usada para gravar e para
    conferir, de modo que as duas nunca possam divergir."""
    if scimago is not None:
        return scimago.get("quartil"), "Scimago SJR Best Quartile"
    return tier_proxy, "proxy OpenAlex (sem correspondência no Scimago)"


def checar(journals):
    erros = []
    for sid, m in journals.items():
        tp = tier_proxy_de(m.get("citedness_2a"))
        tier, base = tier_e_base(tp, m.get("scimago"))
        if m.get("tier_proxy") != tp:
            erros.append(f"{sid} ({m.get('nome')}): tier_proxy={m.get('tier_proxy')!r}, esperado {tp!r}")
        if m.get("tier") != tier:
            erros.append(f"{sid} ({m.get('nome')}): tier={m.get('tier')!r}, esperado {tier!r}")
        if m.get("tier_base") != base:
            erros.append(f"{sid} ({m.get('nome')}): tier_base={m.get('tier_base')!r}, esperado {base!r}")
    return erros


# ---------------- só usado no modo de gravação (lê o CSV) ----------------

def norm_issn(s):
    return {re.sub(r"[^0-9X]", "", x.upper()) for x in re.split(r"[,\s]+", s or "") if x.strip()}

def num(s):
    s = (s or "").strip().replace(",", ".")
    try: return float(s)
    except ValueError: return None

def ler_scimago(path):
    idx, linhas = {}, 0
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        for row in csv.DictReader(f, delimiter=";"):
            linhas += 1
            for i in norm_issn(row.get("Issn")):
                if len(i) == 8: idx.setdefault(i, row)
    return idx, linhas

def scimago_de(row):
    if row is None:
        return None
    cats = row.get("Categories") or ""
    return {
        "titulo": row.get("Title"),
        "sjr": num(row.get("SJR")),
        "quartil": (row.get("SJR Best Quartile") or "").strip() or None,
        "h_index": num(row.get("H index")),
        "areas": (row.get("Areas") or "").strip(),
        "categorias": cats.strip(),
        "quartis_por_area": dict(re.findall(r"([^;()]+?)\s*\((Q[1-4])\)", cats)),
        "editora": (row.get("Publisher") or "").strip(),
        "pais": (row.get("Country") or "").strip(),
        "regiao": (row.get("Region") or "").strip(),
        "rank": num(row.get("Rank")),
        "tipo": (row.get("Type") or "").strip(),
        "open_access": (row.get("Open Access") or "").strip(),
        "citacoes_doc_2a": num(row.get("Citations / Doc. (2years)")),
        "overton": num(row.get("Overton")),   # citações em documento de política
        "cobertura": (row.get("Coverage") or "").strip(),
    }


CHECK = "--check" in sys.argv[1:]
journals = auditlib.load_journals()

if CHECK:
    erros = checar(journals)
    if erros:
        print(f"VIOLAÇÕES DA REGRA DE TIER: {len(erros)}")
        for e in erros: print(f"  {e}")
        sys.exit(1)
    print(f"ok: {len(journals)} periódicos satisfazem a regra de tier (--check, sem rede/CSV)")
else:
    if not SCIMAGO_CSV.exists():
        raise SystemExit(f"CSV do Scimago não encontrado em {SCIMAGO_CSV}")
    print(f"lendo {SCIMAGO_CSV.relative_to(auditlib.ROOT)}")
    idx, linhas = ler_scimago(SCIMAGO_CSV)
    print(f"{linhas} periódicos no Scimago, {len(idx)} ISSNs indexados")

    casou = 0
    for sid, m in journals.items():
        issns = norm_issn(m.get("issn_l") or "") | norm_issn(" ".join(m.get("issn") or []))
        row = next((idx[i] for i in issns if i in idx), None)
        sc = scimago_de(row)
        if sc is not None: casou += 1
        tp = tier_proxy_de(m.get("citedness_2a"))
        tier, base = tier_e_base(tp, sc)
        m["scimago"], m["tier_proxy"], m["tier"], m["tier_base"] = sc, tp, tier, base

    auditlib.save_journals(journals)
    print(f"\ncasaram {casou}/{len(journals)} periódicos com o Scimago")
    q = collections.Counter(m["scimago"]["quartil"] for m in journals.values() if m.get("scimago"))
    print("quartis:", dict(sorted(q.items(), key=lambda x: str(x[0]))))
    falt = sorted(m["nome"] for m in journals.values() if not m.get("scimago"))
    print(f"\nsem correspondência ({len(falt)}) — conferir se são repositório ou periódico novo:")
    for n in falt[:20]: print(f"   {n}")

    erros = checar(journals)
    assert not erros, f"regra de tier inconsistente logo após gravar: {erros}"
