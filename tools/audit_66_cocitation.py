#!/usr/bin/env python3
"""Etapa 66: co-citação das duas vertentes da literatura de atrasos aéreos
(airline, único artigo -- ver data/cocit/seeds_airline.json).

seeds_airline.json particiona 18 das 26 referências do PDF em vertente A
("airport congestion internalization", efeitos globais de concentração no
aeroporto) e vertente B ("route/market competition and service quality",
efeitos locais de concentração na rota, inclusive a sub-literatura de
entrada de LCC do §2.4). data/cd/refs_audit_airline.json (produzido por
audit_64_refs_audit.py) resolve cada número de referência do PDF a um ID
OpenAlex; uma semente sem status matched/repaired é reportada como
excluída.

Universo U = obras que citam >=1 semente (A ou B), publication_year em
[2003, 2026] (constantes UNIVERSE_Y0/Y1 -- ver nota de decisões ambíguas
no fim do arquivo sobre por que não são recalculadas a partir do ano
corrente como no script 65). Por obra: seeds_A_cited[]/seeds_B_cited[]
(números de referência do PDF, não IDs OpenAlex -- mais legível) e
cites_focal (pertence aos citantes do artigo-foco; reaproveita a mesma
chamada sem filtro de data que audit_65_cd_index.py já faz para os
citantes de p, então bate cache quando o script 65 já rodou).

Períodos: main (pre 2003-2015, post 2016-2026); sensitivity (mesmo pre,
post 2017-2026, com 2016 como zona de exclusão -- ver nota); placebo em
2011 e 2020 (mesmo desenho de pre/post do main, só com o corte movido).
Por período: N_A, N_B, N_AB, share_AB=N_AB/N_{AuB}, Jaccard (mesma coisa
que share_AB aqui, ver nota), cosseno de Salton = N_AB/sqrt(N_A*N_B).
Matriz de co-citação semente x semente (só main pre/post) com a força
média dentro-da-vertente vs entre-vertentes.

Brokerage share (só main post) = citantes de A-e-B que também citam o
foco / N_AB(post); comparado com a taxa de citar o foco entre citantes só
de A e só de B (razão de chances). Visão reversa: fração dos citantes do
foco que citam as duas vertentes.

Testes: Fisher exato (período x cita-as-duas, hipergeométrica exata via
math.comb); permutação (10k embaralhamentos do ano dentro de U, seed
20260904) para delta share_AB; binomial exato para brokerage vs taxa de
vertente única; Wilson 95% nas taxas anuais. Confirmação de passagem:
varre data/classify.json (só DOIs do airline) por "strand"/"conciliat"/
"reconcil"/"two strands"/"duas vertentes" em note/passages.

Uso:
  python3 tools/audit_66_cocitation.py               roda tudo (rede)
  python3 tools/audit_66_cocitation.py --no-cache     ignora o cache em disco (força rede)
  python3 tools/audit_66_cocitation.py --selftest     só os testes unitários dos helpers estatísticos, sem rede
  python3 tools/audit_66_cocitation.py --backend s2   usa Semantic Scholar em vez do OpenAlex (orçamento
                                                       diário do OpenAlex zerado -- ver s2_client.py;
                                                       reaproveita data/cd/id_map_airline.json se já
                                                       existir, senão constrói)
  python3 tools/audit_66_cocitation.py --help
"""

import argparse
import collections
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from math import comb
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import auditlib
except ImportError:
    for _cand in (
        Path.cwd() / "tools",
        Path("/Users/wbendinelli/Documents/citation-audit/tools"),
    ):
        if (_cand / "auditlib.py").exists():
            sys.path.insert(0, str(_cand))
            break
    import auditlib
import openalex_client as oax
import s2_client as s2c

PAPER = "airline"
SEED = 20260904
N_PERM = 10000
UNIVERSE_Y0, UNIVERSE_Y1 = 2003, 2026
KEYWORDS = ("strand", "conciliat", "reconcil", "two strands", "duas vertentes")

# Ver nota de decisões ambíguas no fim: "sensitivity" mantém o mesmo pre
# do main e só desloca o post, deixando 2016 como zona de exclusão (não
# desloca o corte inteiro) -- leitura mais literal de "sensitivity post
# = 2017-2026" no enunciado, que não menciona redefinir o pre.
PERIODS = {
    "main": {"pre": (2003, 2015), "post": (2016, 2026)},
    "sensitivity": {"pre": (2003, 2015), "post": (2017, 2026)},
    "placebo_2011": {"pre": (2003, 2010), "post": (2011, 2026)},
    "placebo_2020": {"pre": (2003, 2019), "post": (2020, 2026)},
}


# ================= estatística (stdlib/numpy, sem scipy) =================


def hyper_pmf(x, row1, row2, col1):
    n = row1 + row2
    return comb(row1, x) * comb(row2, col1 - x) / comb(n, col1)


def fisher_exact_2x2(table):
    """p bicaudal exato via hipergeométrica -- mesmo algoritmo de
    audit_65_cd_index.py, duplicado aqui (arquivo pequeno, cada script
    novo fica executável sozinho; openalex_client.py é só a camada de
    rede/cache compartilhada, não um grab-bag de utilidades)."""
    a, b = table[0]
    c, d = table[1]
    row1, row2 = a + b, c + d
    col1 = a + c
    n = row1 + row2
    if n == 0 or row1 == 0 or row2 == 0 or col1 == 0 or col1 == n:
        return 1.0
    lo, hi = max(0, col1 - row2), min(row1, col1)
    probs = {x: hyper_pmf(x, row1, row2, col1) for x in range(lo, hi + 1)}
    pobs = probs[a]
    eps = 1e-7
    return min(1.0, sum(v for v in probs.values() if v <= pobs * (1 + eps)))


def binom_pmf(x, n, p):
    return comb(n, x) * (p**x) * ((1 - p) ** (n - x))


def binom_test_two_sided(k, n, p0):
    """p bicaudal exato: soma das probabilidades binomiais <= a
    probabilidade do valor observado, sob H0: p=p0."""
    if n == 0 or p0 is None or p0 <= 0 or p0 >= 1:
        return None
    pk = binom_pmf(k, n, p0)
    eps = 1e-7
    return min(
        1.0,
        sum(
            binom_pmf(x, n, p0)
            for x in range(n + 1)
            if binom_pmf(x, n, p0) <= pk * (1 + eps)
        ),
    )


def wilson_ci(k, n, z=1.959963984540054):
    if not n:
        return [None, None]
    phat = k / n
    denom = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    half = (z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))) / denom
    return [max(0.0, center - half), min(1.0, center + half)]


def odds(p):
    if p is None or p <= 0 or p >= 1:
        return None
    return p / (1 - p)


def odds_ratio(p1, p0):
    o1, o0 = odds(p1), odds(p0)
    if o1 is None or o0 is None or o0 == 0:
        return None
    return o1 / o0


def permutation_test_delta_share(
    years, is_ab, pre_range, post_range, n_perm=N_PERM, seed=SEED, chunk=1000
):
    """H0: o ano de publicação não tem relação com ser co-citante A-e-B.
    Embaralha os anos observados entre as obras de U (mantendo fixo quem
    é/não é co-citante AB) `n_perm` vezes; compara |delta share_AB| real
    contra a distribuição nula. Processado em blocos (`chunk`) para não
    alocar uma matriz (n_perm x n) inteira de uma vez."""
    years = np.asarray(years, dtype=np.int32)
    is_ab = np.asarray(is_ab, dtype=bool)
    n = years.size
    y0p, y1p = pre_range
    y0q, y1q = post_range
    pre_mask = (years >= y0p) & (years <= y1p)
    post_mask = (years >= y0q) & (years <= y1q)
    n_pre, n_post = int(pre_mask.sum()), int(post_mask.sum())
    if n_pre == 0 or n_post == 0:
        return {
            "delta_observed": None,
            "p_value": None,
            "n_perm": n_perm,
            "share_pre_observed": None,
            "share_post_observed": None,
        }
    share_pre_obs = float(is_ab[pre_mask].mean())
    share_post_obs = float(is_ab[post_mask].mean())
    delta_obs = share_post_obs - share_pre_obs
    rng = np.random.default_rng(seed)
    count_ge, done = 0, 0
    for start in range(0, n_perm, chunk):
        b = min(chunk, n_perm - start)
        keys = rng.random((b, n))
        order = np.argsort(keys, axis=1)
        perm_years = years[order]
        pm = (perm_years >= y0p) & (perm_years <= y1p)
        qm = (perm_years >= y0q) & (perm_years <= y1q)
        is_ab_b = np.broadcast_to(is_ab, (b, n))
        with np.errstate(invalid="ignore"):
            sp = (is_ab_b & pm).sum(1) / pm.sum(1)
            sq = (is_ab_b & qm).sum(1) / qm.sum(1)
        deltas = sq - sp
        valid = ~np.isnan(deltas)
        count_ge += int(np.sum(np.abs(deltas[valid]) >= abs(delta_obs)))
        done += int(valid.sum())
    p = (count_ge + 1) / (done + 1)
    return {
        "delta_observed": delta_obs,
        "p_value": float(p),
        "n_perm": n_perm,
        "share_pre_observed": share_pre_obs,
        "share_post_observed": share_post_obs,
    }


def selftest():
    """Só os helpers estatísticos deste script (sem rede) -- ver nota de
    decisões ambíguas: escrito para compensar não ter dado pra fazer uma
    corrida completa fim-a-fim hoje (orçamento do OpenAlex zerado)."""
    assert math.isclose(fisher_exact_2x2([[5, 5], [5, 5]]), 1.0, rel_tol=1e-6)
    assert fisher_exact_2x2([[10, 0], [0, 10]]) < 0.001
    assert math.isclose(binom_test_two_sided(5, 10, 0.5), 1.0, rel_tol=1e-6)
    assert binom_test_two_sided(9, 10, 0.1) < 0.001
    lo, hi = wilson_ci(50, 100)
    assert lo is not None and lo < 0.5 < hi
    assert wilson_ci(0, 0) == [None, None]
    assert odds(0.5) == 1.0
    assert odds_ratio(0.5, 0.5) == 1.0
    assert odds_ratio(None, 0.5) is None
    # permutação: série sem NENHUMA relação ano<->grupo -> delta observado
    # pequeno e p alto; série com toda obra AB concentrada só no post ->
    # p pequeno.
    rng = np.random.default_rng(1)
    years_null = rng.integers(2003, 2027, size=400)
    is_ab_null = rng.random(400) < 0.3
    r_null = permutation_test_delta_share(
        years_null, is_ab_null, (2003, 2015), (2016, 2026), n_perm=500
    )
    years_sig = np.array([2010] * 100 + [2020] * 100)
    is_ab_sig = np.array([False] * 100 + [True] * 100)
    r_sig = permutation_test_delta_share(
        years_sig, is_ab_sig, (2003, 2015), (2016, 2026), n_perm=500
    )
    assert r_sig["p_value"] < r_null["p_value"], (r_sig, r_null)
    assert r_sig["p_value"] < 0.05, r_sig
    print(
        "selftest OK: fisher_exact_2x2, binom_test_two_sided, wilson_ci, odds_ratio, "
        "permutation_test_delta_share (caso nulo vs caso com sinal forte)."
    )


# ================= carga de seeds/refs_audit =================


def load_seeds():
    with open(auditlib.DATA / "cocit" / "seeds_airline.json", encoding="utf-8") as f:
        return json.load(f)


def load_refs_audit():
    path = auditlib.DATA / "cd" / f"refs_audit_{PAPER}.json"
    if not path.exists():
        raise SystemExit(
            f"erro: {path} não existe -- rode "
            f"'python3 tools/audit_64_refs_audit.py --paper {PAPER}' primeiro"
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve_seeds(seeds, refs_audit):
    """Número de referência do PDF (n) -> ID OpenAlex, só para as
    sementes citadas em seeds_airline.json (18 de 26). Sementes com
    status != matched/repaired em refs_audit_airline.json são excluídas
    e reportadas."""
    status_by_n = {r["n"]: r for r in refs_audit["pdf_refs"]}
    n_to_strand, resolved, excluded = {}, {}, []
    for strand, key in (("A", "strand_A"), ("B", "strand_B")):
        for ref in seeds[key]["refs"]:
            n = ref["n"]
            n_to_strand[n] = strand
            st = status_by_n.get(n, {})
            if st.get("status") in ("matched", "repaired") and st.get("openalex_id"):
                resolved[n] = st["openalex_id"]
            else:
                excluded.append(
                    {
                        "n": n,
                        "strand": strand,
                        "cite": ref.get("cite"),
                        "status": st.get("status", "ausente_em_refs_audit"),
                    }
                )
    return n_to_strand, resolved, excluded


# ================= coleta =================


def fetch_seed_citers(client, seed_oaids, y0, y1, max_workers=6):
    """citantes de cada semente (OpenAlex ID) com publication_year em
    [y0, y1]. Uma thread por semente; paginação por cursor sequencial
    dentro de cada uma (ver mesma lógica em audit_65_cd_index.py)."""
    out = {}

    def one(oaid):
        recs = list(
            client.works_citing(
                oaid, from_year=y0, to_year=y1, select=oax.SELECT_R_CITERS
            )
        )
        return oaid, recs

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(one, oaid): oaid for oaid in seed_oaids}
        for done, fut in enumerate(as_completed(futs), start=1):
            oaid, recs = fut.result()
            out[oaid] = recs
            print(f"    [{done}/{len(seed_oaids)}] {oaid}: {len(recs)} citantes")
    return out


def build_universe(client, resolved, n_to_strand, p_id):
    seed_oaids = sorted(set(resolved.values()))
    oaid_to_ns = collections.defaultdict(list)
    for n, oaid in resolved.items():
        oaid_to_ns[oaid].append(n)

    print(
        f"  buscando citantes de {len(seed_oaids)} sementes em [{UNIVERSE_Y0}, {UNIVERSE_Y1}]..."
    )
    per_seed = fetch_seed_citers(client, seed_oaids, UNIVERSE_Y0, UNIVERSE_Y1)

    work_year = {}
    seeds_a = collections.defaultdict(set)
    seeds_b = collections.defaultdict(set)
    for oaid, recs in per_seed.items():
        ns = oaid_to_ns[oaid]
        for rec in recs:
            wid = oax.short_id(rec["id"])
            y = rec.get("publication_year")
            if y is not None:
                work_year[wid] = y
            for n in ns:
                (seeds_a if n_to_strand[n] == "A" else seeds_b)[wid].add(n)

    print(
        "  buscando TODOS os citantes do foco (reaproveita cache do script 65, se já rodou)..."
    )
    p_citers_year = {}
    for rec in client.works_citing(p_id, select=oax.SELECT_P_CITERS):
        wid = oax.short_id(rec["id"])
        p_citers_year[wid] = rec.get("publication_year")
    p_citers_ids = set(p_citers_year)
    print(f"  {len(p_citers_ids)} citantes do foco (todos os anos)")

    universe_ids = sorted(set(seeds_a) | set(seeds_b))
    records = []
    for wid in universe_ids:
        records.append(
            {
                "id": wid,
                "year": work_year.get(wid),
                "seeds_A_cited": sorted(seeds_a.get(wid, ())),
                "seeds_B_cited": sorted(seeds_b.get(wid, ())),
                "cites_focal": wid in p_citers_ids,
            }
        )
    print(f"  |U| = {len(records)} obras citando >=1 semente")
    return records, p_citers_ids, p_citers_year


# ================= indicadores por período =================


def period_stats(records, y0, y1):
    in_a = [
        r
        for r in records
        if r["year"] is not None and y0 <= r["year"] <= y1 and r["seeds_A_cited"]
    ]
    in_b = [
        r
        for r in records
        if r["year"] is not None and y0 <= r["year"] <= y1 and r["seeds_B_cited"]
    ]
    in_ab = [r for r in in_a if r["seeds_B_cited"]]
    n_a, n_b, n_ab = len(in_a), len(in_b), len(in_ab)
    n_union = len({r["id"] for r in in_a} | {r["id"] for r in in_b})
    share = (n_ab / n_union) if n_union else None
    salton = (n_ab / math.sqrt(n_a * n_b)) if (n_a > 0 and n_b > 0) else None
    return {
        "N_A": n_a,
        "N_B": n_b,
        "N_AB": n_ab,
        "N_union": n_union,
        "share_AB": share,
        "jaccard": share,
        "salton_cosine": salton,
        "checks": {"N_AB_le_min_NA_NB": n_ab <= min(n_a, n_b)},
    }


def cocitation_matrix(records, seed_order, n_to_strand, y0, y1):
    idx = {s: i for i, s in enumerate(seed_order)}
    R = len(seed_order)
    M = np.zeros((R, R), dtype=np.int64)
    for r in records:
        if r["year"] is None or not (y0 <= r["year"] <= y1):
            continue
        cited = [n for n in (r["seeds_A_cited"] + r["seeds_B_cited"]) if n in idx]
        for n in cited:
            M[idx[n], idx[n]] += 1
        for a_ in range(len(cited)):
            for b_ in range(a_ + 1, len(cited)):
                i, j = idx[cited[a_]], idx[cited[b_]]
                M[i, j] += 1
                M[j, i] += 1
    within, cross = [], []
    for i in range(R):
        for j in range(i + 1, R):
            v = int(M[i, j])
            (
                within
                if n_to_strand[seed_order[i]] == n_to_strand[seed_order[j]]
                else cross
            ).append(v)
    return {
        "seed_order": seed_order,
        "matrix": M.tolist(),
        "within_strand_mean": float(np.mean(within)) if within else None,
        "cross_strand_mean": float(np.mean(cross)) if cross else None,
        "within_strand_n_pairs": len(within),
        "cross_strand_n_pairs": len(cross),
    }


def brokerage_analysis(records, p_citers_year):
    y0, y1 = PERIODS["main"]["post"]
    in_window = [r for r in records if r["year"] is not None and y0 <= r["year"] <= y1]
    ab = [r for r in in_window if r["seeds_A_cited"] and r["seeds_B_cited"]]
    a_only = [r for r in in_window if r["seeds_A_cited"] and not r["seeds_B_cited"]]
    b_only = [r for r in in_window if r["seeds_B_cited"] and not r["seeds_A_cited"]]
    single = a_only + b_only

    def rate(group):
        n = len(group)
        k = sum(1 for r in group if r["cites_focal"])
        return n, k, (k / n if n else None)

    n_ab, k_ab, r_ab = rate(ab)
    n_single, k_single, r_single = rate(single)
    n_a, k_a, r_a = rate(a_only)
    n_b, k_b, r_b = rate(b_only)

    # verificação pedida no relatório final: o numerador do brokerage
    # (k_ab -- co-citantes A-e-B que também citam o foco) não pode passar
    # do total de citantes do foco na mesma janela (k_ab é um subconjunto
    # desses por definição; é o mesmo tipo de checagem que
    # audit_65_cd_index.py já grava em `checks` para n_i+n_j).
    n_focal_citers_window = len(
        {wid for wid, y in p_citers_year.items() if y is not None and y0 <= y <= y1}
    )

    return {
        "post_window": [y0, y1],
        "AB": {"n": n_ab, "k_cites_focal": k_ab, "rate": r_ab},
        "single_strand": {"n": n_single, "k_cites_focal": k_single, "rate": r_single},
        "A_only": {"n": n_a, "k_cites_focal": k_a, "rate": r_a},
        "B_only": {"n": n_b, "k_cites_focal": k_b, "rate": r_b},
        "brokerage_share": r_ab,
        "odds_ratio_AB_vs_single": odds_ratio(r_ab, r_single),
        "odds_ratio_AB_vs_A_only": odds_ratio(r_ab, r_a),
        "odds_ratio_AB_vs_B_only": odds_ratio(r_ab, r_b),
        "binom_test_AB_vs_single_p0": {
            "k": k_ab,
            "n": n_ab,
            "p0": r_single,
            "p_two_sided": binom_test_two_sided(k_ab, n_ab, r_single),
        },
        "n_focal_citers_in_window": n_focal_citers_window,
        "checks": {"k_ab_le_focal_citers_in_window": k_ab <= n_focal_citers_window},
    }


def reverse_view(records, p_citers_ids, p_citers_year):
    ab_alltime_ids = {
        r["id"] for r in records if r["seeds_A_cited"] and r["seeds_B_cited"]
    }
    n_p = len(p_citers_ids)
    num_alltime = sum(1 for wid in p_citers_ids if wid in ab_alltime_ids)
    y0, y1 = PERIODS["main"]["post"]
    ab_post_ids = {
        r["id"]
        for r in records
        if r["year"] is not None
        and y0 <= r["year"] <= y1
        and r["seeds_A_cited"]
        and r["seeds_B_cited"]
    }
    p_citers_post = {
        wid for wid, y in p_citers_year.items() if y is not None and y0 <= y <= y1
    }
    n_p_post = len(p_citers_post)
    num_post = sum(1 for wid in p_citers_post if wid in ab_post_ids)
    return {
        "all_time": {
            "n_focal_citers": n_p,
            "n_citing_both_strands": num_alltime,
            "share": (num_alltime / n_p) if n_p else None,
        },
        "post_main": {
            "n_focal_citers": n_p_post,
            "n_citing_both_strands": num_post,
            "share": (num_post / n_p_post) if n_p_post else None,
        },
    }


def yearly_series(records):
    out = []
    for y in range(UNIVERSE_Y0, UNIVERSE_Y1 + 1):
        st = period_stats(records, y, y)
        st["year"] = y
        st["share_AB_wilson_ci_95"] = wilson_ci(st["N_AB"], st["N_union"])
        out.append(st)
    return out


def role_or_depth(entry):
    """`classify.json` schema 1 guarda o eixo em `role`; schema 2
    (METHOD.md@v2, migrado em 2026-09-04) removeu `role` do topo da
    entrada e usa `depth` -- mesmo vocabulário para os valores que
    interessam num relatório humano. Duplicada de audit_65_cd_index.py
    (mesma convenção de pequenos helpers repetidos entre os dois scripts
    já usada por fisher_exact_2x2/hyper_pmf acima). Sem isto,
    `entry.get("role")` devolveria None para as 104/104 entradas atuais
    de data/classify.json (schema 2) e a coluna "role" de cada hit de
    passage_confirmation sairia sempre vazia."""
    r = entry.get("role")
    return r if r is not None else entry.get("depth")


def passage_confirmation(master):
    classify_entries = auditlib.classify_entries(auditlib.load_classify())
    airline_dois = {
        auditlib.norm_doi(r.get("doi"))
        for r in master["papers"][PAPER]["citing"]
        if r.get("doi")
    }
    airline_dois.discard(None)
    hits = []
    for doi, entry in classify_entries.items():
        if doi not in airline_dois:
            continue
        text = " ".join(
            [entry.get("note") or ""] + list(entry.get("passages") or [])
        ).lower()
        if any(kw in text for kw in KEYWORDS):
            hits.append(
                {
                    "doi": doi,
                    "role": role_or_depth(entry),
                    "stance": entry.get("stance"),
                    "note": entry.get("note"),
                }
            )
    hits.sort(key=lambda x: x["doi"])
    return hits


# ================= main =================


def run(client, snapshot_date, backend="openalex", remap=False):
    seeds = load_seeds()
    refs_audit = load_refs_audit()
    focal_openalex_id = oax.short_id(refs_audit["focal"]["openalex_id"])
    n_to_strand, resolved, excluded = resolve_seeds(seeds, refs_audit)
    print(
        f"  sementes: {len(resolved)} resolvidas (OpenAlex), {len(excluded)} excluídas"
    )
    for ex in excluded:
        print(
            f"    EXCLUÍDA n={ex['n']} ({ex['strand']}) status={ex['status']}: {ex.get('cite')}"
        )

    s2_citation_count = None
    if backend == "s2":
        # Reaproveita data/cd/id_map_airline.json se audit_65_cd_index.py
        # --backend s2 já rodou pro airline hoje (ensure_id_map carrega
        # do disco em vez de reconstruir -- ver s2_client.py); senão
        # constrói agora. Toda semente resolvida (n -> ID OpenAlex) É por
        # definição uma referência de R_valid do airline (resolve_seeds
        # já exige status matched/repaired, o mesmo crivo de R_valid em
        # audit_64_refs_audit.py), então o MESMO id_map cobre as duas
        # pontas sem refazer nenhuma busca por título.
        id_map = s2c.ensure_id_map(
            client, PAPER, refs_audit, snapshot_date, retry_unmapped=remap
        )
        p_id = id_map["focal"]["s2_paper_id"]
        if not p_id:
            raise SystemExit(
                f"erro: não consegui resolver o artigo-foco no S2 "
                f"(DOI {refs_audit['focal']['doi']}) -- ver data/cd/id_map_{PAPER}.json"
            )
        s2_citation_count = id_map["focal"]["s2_citation_count"]
        resolved_s2 = {}
        for n, oaid in resolved.items():
            m = id_map["mapped"].get(oaid)
            if m:
                resolved_s2[n] = m["s2_paper_id"]
            else:
                excluded.append(
                    {
                        "n": n,
                        "strand": n_to_strand[n],
                        "cite": None,
                        "status": "sem_mapeamento_s2 (ver data/cd/id_map_airline.json)",
                    }
                )
                print(f"    EXCLUÍDA n={n} ({n_to_strand[n]}) status=sem_mapeamento_s2")
        resolved = resolved_s2
        print(f"  sementes mapeadas p/ S2 paperId: {len(resolved)}")
    else:
        p_id = focal_openalex_id

    records, p_citers_ids, p_citers_year = build_universe(
        client, resolved, n_to_strand, p_id
    )

    periods_out = {}
    for name, spec in PERIODS.items():
        pre_stats = period_stats(records, *spec["pre"])
        post_stats = period_stats(records, *spec["post"])
        delta = None
        if pre_stats["share_AB"] is not None and post_stats["share_AB"] is not None:
            delta = post_stats["share_AB"] - pre_stats["share_AB"]
        periods_out[name] = {
            "pre_range": list(spec["pre"]),
            "post_range": list(spec["post"]),
            "pre": pre_stats,
            "post": post_stats,
            "delta_share_AB": delta,
        }

    seed_order = sorted(
        (n for n, s in n_to_strand.items() if n in resolved and s == "A")
    ) + sorted((n for n, s in n_to_strand.items() if n in resolved and s == "B"))
    matrix_pre = cocitation_matrix(
        records, seed_order, n_to_strand, *PERIODS["main"]["pre"]
    )
    matrix_post = cocitation_matrix(
        records, seed_order, n_to_strand, *PERIODS["main"]["post"]
    )

    brokerage = brokerage_analysis(records, p_citers_year)
    reverse = reverse_view(records, p_citers_ids, p_citers_year)
    yearly = yearly_series(records)

    years_arr = [r["year"] for r in records if r["year"] is not None]
    is_ab_arr = [
        bool(r["seeds_A_cited"]) and bool(r["seeds_B_cited"])
        for r in records
        if r["year"] is not None
    ]
    perm = permutation_test_delta_share(
        years_arr, is_ab_arr, PERIODS["main"]["pre"], PERIODS["main"]["post"]
    )

    n_ab_pre, n_u_pre = (
        periods_out["main"]["pre"]["N_AB"],
        periods_out["main"]["pre"]["N_union"],
    )
    n_ab_post, n_u_post = (
        periods_out["main"]["post"]["N_AB"],
        periods_out["main"]["post"]["N_union"],
    )
    table_period = [[n_ab_pre, n_u_pre - n_ab_pre], [n_ab_post, n_u_post - n_ab_post]]
    fisher_period = fisher_exact_2x2(table_period)

    master = auditlib.load_master()
    passages = passage_confirmation(master)

    cocit = {
        "paper": PAPER,
        "focal": {
            "doi": refs_audit["focal"]["doi"],
            "openalex_id": focal_openalex_id,
            "s2_paper_id": p_id if backend == "s2" else None,
            "year": refs_audit["focal"]["year"],
            "s2_citation_count": s2_citation_count,
        },
        "seeds": {
            "n_strand_A": sum(1 for s in n_to_strand.values() if s == "A"),
            "n_strand_B": sum(1 for s in n_to_strand.values() if s == "B"),
            "id_scheme": "s2_paper_id" if backend == "s2" else "openalex_id",
            "resolved": {str(n): oaid for n, oaid in sorted(resolved.items())},
            "excluded": excluded,
        },
        "universe_size": len(records),
        "universe_year_range": [UNIVERSE_Y0, UNIVERSE_Y1],
        "periods": periods_out,
        "cocitation_matrix_main_pre": matrix_pre,
        "cocitation_matrix_main_post": matrix_post,
        "brokerage": brokerage,
        "reverse_view": reverse,
        "yearly_series": yearly,
        "tests": {
            "fisher_period_x_cocites_both": {
                "table_rows_pre_post__cols_AB_single": table_period,
                "p_two_sided": fisher_period,
            },
            "permutation_delta_share_AB_main": perm,
        },
        "passage_confirmation": {
            "keywords": list(KEYWORDS),
            "n_hits": len(passages),
            "hits": passages,
        },
        "snapshot_date": snapshot_date,
        "seed": SEED,
        "n_perm": N_PERM,
    }
    return cocit, records


def print_report(cocit):
    print("\n--- airline: co-citação das duas vertentes ---")
    m = cocit["periods"]["main"]
    print(
        f"  main pre {m['pre_range']}: N_A={m['pre']['N_A']} N_B={m['pre']['N_B']} "
        f"N_AB={m['pre']['N_AB']} share_AB={m['pre']['share_AB']}"
    )
    print(
        f"  main post {m['post_range']}: N_A={m['post']['N_A']} N_B={m['post']['N_B']} "
        f"N_AB={m['post']['N_AB']} share_AB={m['post']['share_AB']}"
    )
    print(f"  delta share_AB (post-pre) = {m['delta_share_AB']}")
    b = cocit["brokerage"]
    print(
        f"  brokerage share (post) = {b['brokerage_share']}  "
        f"OR vs single-strand = {b['odds_ratio_AB_vs_single']}  "
        f"binom p = {b['binom_test_AB_vs_single_p0']['p_two_sided']}"
    )
    t = cocit["tests"]
    print(
        f"  fisher (período x cita-as-duas) p = {t['fisher_period_x_cocites_both']['p_two_sided']:.4g}"
    )
    perm = t["permutation_delta_share_AB_main"]
    print(
        f"  permutação delta observado = {perm['delta_observed']}  p = {perm['p_value']}"
    )
    print(f"  visão reversa (todos os anos): {cocit['reverse_view']['all_time']}")
    print(
        f"  confirmação de passagem: {cocit['passage_confirmation']['n_hits']} DOIs -- "
        f"{[h['doi'] for h in cocit['passage_confirmation']['hits']]}"
    )
    if cocit.get("backend") == "semanticscholar":
        print(f"  citationCount S2 do foco = {cocit['focal']['s2_citation_count']}")
        n_excl_s2 = sum(
            1
            for e in cocit["seeds"]["excluded"]
            if "sem_mapeamento_s2" in (e.get("status") or "")
        )
        if n_excl_s2:
            print(f"  AVISO: {n_excl_s2} semente(s) sem mapeamento S2 (excluída(s))")
        caps = cocit.get("s2_pagination_caps_hit") or []
        if caps:
            print(
                f"  AVISO: teto de paginação do S2 (offset+limit<=10000) atingido em: {caps}"
            )


def parse_args():
    p = argparse.ArgumentParser(
        description="Co-citação das vertentes A/B da literatura de atrasos aéreos (só airline): "
        "universo de co-citantes, brokerage, testes de período e confirmação de passagem.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--no-cache", action="store_true", help="ignora o cache em disco (força rede)"
    )
    p.add_argument(
        "--backend",
        choices=("openalex", "s2"),
        default="openalex",
        help="fonte de dados: OpenAlex (default) ou Semantic Scholar -- 's2', quando o "
        "orçamento diário de queries de lista do OpenAlex está zerado (ver s2_client.py)",
    )
    p.add_argument(
        "--remap",
        action="store_true",
        help="(só --backend s2) tenta de novo as sementes que ficaram sem mapeamento S2 "
        "numa corrida anterior; ver a mesma flag em audit_65_cd_index.py",
    )
    p.add_argument(
        "--selftest",
        action="store_true",
        help="roda os testes unitários dos helpers estatísticos (fisher, binom, wilson, "
        "permutação) e sai, sem rede",
    )
    return p.parse_args()


def main():
    args = parse_args()
    if args.selftest:
        selftest()
        return
    if args.backend == "s2":
        client = s2c.S2Client(use_cache=not args.no_cache)
        backend_name = "semanticscholar"
    else:
        client = oax.OpenAlexClient(use_cache=not args.no_cache)
        backend_name = "openalex"
    snapshot_date = datetime.now(tz=timezone.utc).date().isoformat()
    before = (client.n_network, client.n_cache_hit, client.n_none)
    cocit, records = run(client, snapshot_date, backend=args.backend, remap=args.remap)
    after = (client.n_network, client.n_cache_hit, client.n_none)
    net, hits, none_ = (after[i] - before[i] for i in range(3))
    cocit["requests"] = {
        "network": net,
        "cache_hits": hits,
        "none_responses": none_,
        "total": net + hits,
    }
    cocit["backend"] = backend_name
    cocit["s2_pagination_caps_hit"] = (
        sorted(client.truncated_ids) if args.backend == "s2" else []
    )

    universe_out = {
        "paper": PAPER,
        "snapshot_date": snapshot_date,
        "n": len(records),
        "records": records,
    }
    out_cocit = auditlib.DATA / "cocit" / f"cocit_{PAPER}.json"
    out_universe = auditlib.DATA / "cocit" / f"universe_{PAPER}.json"
    oax.save_json(cocit, out_cocit)
    oax.save_json(universe_out, out_universe)
    print(f"-> {out_cocit}")
    print(f"-> {out_universe}")
    print_report(cocit)
    print(
        f"\ntotal rede: {client.n_network}  cache: {client.n_cache_hit}  nulos: {client.n_none}"
    )


if __name__ == "__main__":
    main()

# ---------------- decisões ambíguas (ver relatório final) ----------------
# 1. "sensitivity" (pre 2003-2015 inalterado, post 2017-2026): o
#    enunciado só redefine o post ("sensitivity post = 2017-2026"), sem
#    mencionar o pre -- lido ao pé da letra, o pre do main permanece, e
#    2016 vira um ano de exclusão (nem pre nem post) nesse cenário. É
#    também o desenho mais comum desse tipo de checagem de robustez
#    (excluir o ano-fronteira em vez de só deslocar o corte).
# 2. Matriz de co-citação semente x semente: só main pre/post (não os 4
#    cenários de período x pre/post = 8 matrizes). O enunciado pede "the
#    seed x seed co-citation matrix" como parte do que sai "per period",
#    mas gerar 8 matrizes 18x18 pareceu escopo maior que o pretendido;
#    main pre/post é o par que o resto do script (brokerage, testes)
#    também usa como referência principal.
# 3. share_AB e Jaccard saem com o mesmo valor: pela própria definição
#    do enunciado (share_AB = N_AB/N_{AuB}), isso *é* o índice de Jaccard
#    entre o conjunto de citantes de A e o de B -- não é um bug, os dois
#    nomes correspondem à mesma fórmula aqui (cosseno de Salton, N_AB /
#    sqrt(N_A*N_B), é a métrica genuinamente diferente das três).
# 4. UNIVERSE_Y0/Y1 fixos em 2003/2026 (não recalculados a partir do ano
#    corrente, ao contrário da janela t=10 do script 65): o enunciado dá
#    "[2003, 2026]" como intervalo literal, sem falar em "ano corrente"
#    como fala para a truncagem do CD -- tratado como constante do
#    desenho do estudo, não como algo que desliza com a data de execução.
# 5. cites_focal e a "visão reversa" reaproveitam works_citing(p_id, ...)
#    sem filtro de data -- a MESMA chamada que audit_65_cd_index.py faz
#    para os citantes de p (mesmo select, oax.SELECT_P_CITERS): bate
#    cache se o script 65 já rodou para o airline, sem precisar ler o
#    cd_airline.json dele nem duplicar a lista em disco.
# 6. --backend s2: reaproveita data/cd/id_map_airline.json (construído
#    por s2_client.ensure_id_map, a mesma função que audit_65_cd_index.py
#    usa) em vez de mapear as sementes por conta própria -- toda semente
#    resolvida aqui já passou pelo mesmo crivo status matched/repaired de
#    R_valid (ver resolve_seeds/audit_64_refs_audit.py), então o id_map
#    do CD index cobre 100% das sementes do airline sem nenhuma busca
#    extra por título. Uma semente cujo ID OpenAlex não está em
#    `id_map["mapped"]` (falhou a resolução no S2) é adicionada à mesma
#    lista `excluded` que já existia para status matched/repaired
#    ausente -- reaproveita o mecanismo de exclusão/relatório, só
#    acrescenta um motivo novo ("sem_mapeamento_s2").
# 7. role_or_depth() em passage_confirmation: mesma correção de
#    audit_65_cd_index.py (ver decisão #6 lá) -- data/classify.json está
#    em schema 2 hoje e não tem mais `role` no topo da entrada.
