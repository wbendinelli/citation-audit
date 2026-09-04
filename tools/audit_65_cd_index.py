#!/usr/bin/env python3
"""Etapa 65: índice de disrupção (CD) sobre R_valid de cada artigo-foco.

Implementa Funk & Owen-Smith (2017) e Wu, Wang & Evans (2019): para uma
janela W_t = obras publicadas em [Y_p, Y_p+t] (Y_p = ano do artigo-foco),
classifica toda obra de W_t que cita o foco p e/ou alguma referência
válida r em R_valid (data/cd/refs_audit_<artigo>.json, produzido por
audit_64_refs_audit.py) em três grupos:

  n_i = cita p, cita 0 de R_valid
  n_j = cita p, cita >=1 de R_valid
  n_k = não cita p, cita >=1 de R_valid

  CD_t     = (n_i - n_j) / (n_i + n_j + n_k)           Funk & Owen-Smith
  CD_nok   = (n_i - n_j) / (n_i + n_j)                 Wu & Yan (2019), sem n_k no denominador
  DI_l     = mesma fórmula de CD_t, mas "cita R" exige citar >= l membros
             de R_valid (não só >=1) -- Bornmann et al. (2020); l=2 e l=5.
             Um citante de p com menos de l refs conta em n_i^l; um
             citante que NÃO cita p mas cita entre 1 e l-1 refs fica de
             fora do universo de DI_l inteiro (não é n_i, n_j nem n_k --
             ver nota de decisões ambíguas no fim do arquivo).
  Holst    = CD_t com n_i restrito a citantes com referenced_works_count
             != 0 (obras sem lista de referências recuperável no OpenAlex
             não contam como evidência genuína de "não cita R").

Janelas t em {1,3,5,10}, e a variante estrita (Y_p, Y_p+t] (exclui o
próprio ano de publicação) como sensibilidade. Para o grains (2019), a
janela t=10 nominal (2019-2029) ainda não aconteceu na data da execução
-- o script usa t = min(10, ano_atual - Y_p) nesse slot e marca
`truncated: true`.

Incerteza: bootstrap percentil 95% (B=2000, seed=20260904) sobre as obras
da janela, para todo indicador. Leave-one-reference-out em CD5 (janela
t=5, base): recomputa CD5 removendo cada r de R_valid, um de cada vez, e
lista as 5 referências com maior |delta|. Cruzamento com data/classify.json
em t=5 (status i/j) x role e x stance, mais teste exato de Fisher (i/j) x
(role substantivo = supporting/foundational, ou não) via hipergeométrica
exata (math.comb, sem scipy).

Dados: (a) TODOS os citantes de p, sem filtro de data (para checar contra
cited_by_count e permitir o cruzamento com classify.json);
(b) para cada r em R_valid, todos os citantes de r com publication_year
em [Y_p, Y_p+10] -- a pertença de uma obra a essas listas por-referência é
o que dá n_k e a contagem "quantos de R_valid essa obra cita" (DI_l) *sem*
nunca buscar a lista de referências completa de cada citante (o produto
citantes-de-p x |R_valid| explodiria). Para os citantes de p, a contagem
"cita r" é recomputada também a partir do `referenced_works` deles
próprios (que já vem no select) só para logar discrepâncias contra a
pertença acima -- é a pertença que decide a classificação, não
`referenced_works`.

Uso:
  python3 tools/audit_65_cd_index.py                    processa todos os artigos (demora minutos)
  python3 tools/audit_65_cd_index.py --paper airline     só um artigo
  python3 tools/audit_65_cd_index.py --cap-per-ref 500   limita citantes buscados por referência
  python3 tools/audit_65_cd_index.py --selftest          só roda os testes unitários das fórmulas (sem rede)
  python3 tools/audit_65_cd_index.py --backend s2        usa Semantic Scholar em vez do OpenAlex
                                                          (orçamento diário do OpenAlex zerado -- ver
                                                          s2_client.py; IDs passam a ser S2 paperId,
                                                          mapeados de R_valid via data/cd/id_map_<artigo>.json)
  python3 tools/audit_65_cd_index.py --help
"""

import argparse
import collections
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
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

CFG = auditlib.load_config()
B_BOOTSTRAP = 2000
SEED = 20260904
NOMINAL_T = (1, 3, 5, 10)
SUBSTANTIVE_ROLES = {"supporting", "foundational"}


# ================= fórmulas núcleo =================


def cd_index(ni, nj, nk):
    den = ni + nj + nk
    return (ni - nj) / den if den else None


def cd_nok_index(ni, nj):
    den = ni + nj
    return (ni - nj) / den if den else None


def counts_l(cp, rc, l):
    """cp, rc: arrays numpy (bool, int) do mesmo tamanho. Devolve as
    máscaras booleanas (is_i, is_j, is_k) pro limiar l de "cita R"."""
    is_j = cp & (rc >= l)
    is_i = cp & (rc < l)
    is_k = (~cp) & (rc >= l)
    return is_i, is_j, is_k


# ================= Fisher exato (hipergeométrica exata) =================


def hyper_pmf(x, row1, row2, col1):
    n = row1 + row2
    return comb(row1, x) * comb(row2, col1 - x) / comb(n, col1)


def fisher_exact_2x2(table):
    """p bicaudal exato: soma das probabilidades hipergeométricas <= a
    probabilidade da tabela observada, sobre o suporte inteiro dado as
    margens fixas. Só stdlib (math.comb) -- sem scipy."""
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
    p = sum(v for v in probs.values() if v <= pobs * (1 + eps))
    return min(1.0, p)


# ================= selftest (--selftest, sem rede) =================


def selftest():
    # toy graph do enunciado: n_i=3, n_j=1, n_k=2
    cd = cd_index(3, 1, 2)
    cdnok = cd_nok_index(3, 1)
    assert math.isclose(cd, 1 / 3, rel_tol=1e-9), cd
    assert math.isclose(cdnok, 0.5, rel_tol=1e-9), cdnok

    # caso construído para DI2 (ver docstring do módulo p/ a regra de
    # exclusão de quem não cita p e fica abaixo do limiar l)
    cp = np.array([True, True, True, False, False])
    rc = np.array([0, 1, 3, 2, 1])
    is_i, is_j, is_k = counts_l(cp, rc, 1)
    ni, nj, nk = int(is_i.sum()), int(is_j.sum()), int(is_k.sum())
    assert (ni, nj, nk) == (1, 2, 2), (ni, nj, nk)
    cd_base = cd_index(ni, nj, nk)
    assert math.isclose(cd_base, -0.2, rel_tol=1e-9), cd_base

    is_i2, is_j2, is_k2 = counts_l(cp, rc, 2)
    ni2, nj2, nk2 = int(is_i2.sum()), int(is_j2.sum()), int(is_k2.sum())
    assert (ni2, nj2, nk2) == (2, 1, 1), (
        ni2,
        nj2,
        nk2,
    )  # o 5o item (cp=False,rc=1) fica de fora
    di2 = cd_index(ni2, nj2, nk2)
    assert math.isclose(di2, 0.25, rel_tol=1e-9), di2

    # propriedades gerais: CD em [-1,1]; CD <= CD_nok quando numerador > 0
    for ni_, nj_, nk_ in [
        (3, 1, 2),
        (5, 0, 0),
        (10, 3, 7),
        (1, 0, 0),
        (0, 5, 3),
        (7, 7, 7),
    ]:
        v = cd_index(ni_, nj_, nk_)
        if v is not None:
            assert -1 - 1e-9 <= v <= 1 + 1e-9, (ni_, nj_, nk_, v)
            if ni_ - nj_ > 0:
                vn = cd_nok_index(ni_, nj_)
                assert v <= vn + 1e-9, (ni_, nj_, nk_, v, vn)

    # Fisher exato: tabela balanceada -> p=1; tabela com separação total -> p bem pequeno
    assert math.isclose(fisher_exact_2x2([[5, 5], [5, 5]]), 1.0, rel_tol=1e-6)
    p_extreme = fisher_exact_2x2([[10, 0], [0, 10]])
    assert p_extreme < 0.001, p_extreme
    # e bate com um valor de referência conhecido (tabela clássica de Fisher, chá/leite 3x3->2x2 análoga)
    p_ref = fisher_exact_2x2([[8, 2], [1, 5]])
    assert 0.01 < p_ref < 0.05, p_ref

    print(
        "selftest OK: CD=1/3 CD_nok=0.5 (toy n_i=3,n_j=1,n_k=2); "
        "DI2=0.25 (caso construído); CD em [-1,1]; CD<=CD_nok; fisher_exact_2x2."
    )


# ================= carga de refs_audit =================


def load_refs_audit(paper):
    path = auditlib.DATA / "cd" / f"refs_audit_{paper}.json"
    if not path.exists():
        raise SystemExit(
            f"erro: {path} não existe -- rode "
            f"'python3 tools/audit_64_refs_audit.py --paper {paper}' primeiro"
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve_windows(y_p, current_year, nominal=NOMINAL_T):
    """t nominal -> t realmente disponível (ano_atual - Y_p, capado em t) +
    flag de truncamento. Ver nota do módulo sobre o grains (2019)."""
    avail = max(0, current_year - y_p)
    return [
        {"t_nominal": t, "t": min(t, avail), "truncated": min(t, avail) < t}
        for t in nominal
    ]


# ================= coleta =================


def fetch_p_citers(client, p_id, r_valid_set):
    """TODOS os citantes do artigo-foco (sem filtro de ano)."""
    p_citers = {}
    for rec in client.works_citing(p_id, select=oax.SELECT_P_CITERS):
        wid = oax.short_id(rec["id"])
        refs = {oax.short_id(x) for x in (rec.get("referenced_works") or [])}
        p_citers[wid] = {
            "year": rec.get("publication_year"),
            "doi": auditlib.norm_doi(rec.get("doi")),
            "rwc": rec.get("referenced_works_count"),
            "refbased_r": sorted(refs & r_valid_set),
        }
    return p_citers


def fetch_r_citers(client, r_valid, y_p, cap_per_ref, max_workers=6):
    """Para cada r em R_valid, todos os citantes com publication_year em
    [Y_p, Y_p+10], em paralelo (uma referência por thread; a paginação
    por cursor dentro de uma referência é sequencial, mas referências
    diferentes não dependem umas das outras)."""
    cites_r_of = collections.defaultdict(set)
    work_year = {}
    counts_per_ref = {}

    def one(r):
        recs = list(
            client.works_citing(
                r,
                from_year=y_p,
                to_year=y_p + 10,
                select=oax.SELECT_R_CITERS,
                cap=cap_per_ref,
            )
        )
        return r, recs

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(one, r): r for r in r_valid}
        for done, fut in enumerate(as_completed(futs), start=1):
            r, recs = fut.result()
            counts_per_ref[r] = len(recs)
            for rec in recs:
                wid = oax.short_id(rec["id"])
                cites_r_of[wid].add(r)
                y = rec.get("publication_year")
                if y is not None:
                    work_year[wid] = y
            print(f"    [{done}/{len(r_valid)}] {r}: {len(recs)} citantes")
    return cites_r_of, work_year, counts_per_ref


def build_arrays(p_citers, cites_r_of, work_year):
    all_ids = sorted(set(p_citers) | set(cites_r_of))
    n = len(all_ids)
    years = np.empty(n, dtype=np.int32)
    cp = np.empty(n, dtype=bool)
    rc = np.empty(n, dtype=np.int32)
    rwc = np.empty(n, dtype=np.int32)
    for i, wid in enumerate(all_ids):
        if wid in p_citers:
            info = p_citers[wid]
            years[i] = info["year"] if info["year"] is not None else -1
            cp[i] = True
            rwc[i] = info["rwc"] if info["rwc"] is not None else -1
        else:
            y = work_year.get(wid)
            years[i] = y if y is not None else -1
            cp[i] = False
            rwc[i] = -1
        rc[i] = len(cites_r_of.get(wid, ()))
    return all_ids, years, cp, rc, rwc


def discrepancies(p_citers, cites_r_of):
    """Citantes de p onde referenced_works (deles) e a pertença nas
    listas por-referência (script 65) discordam sobre quais r eles
    citam. A pertença é usada na classificação; isto é só diagnóstico."""
    mism = []
    more_ref, more_memb = 0, 0
    for wid, info in p_citers.items():
        rb = set(info["refbased_r"])
        mb = cites_r_of.get(wid, set())
        if rb != mb:
            mism.append({"id": wid, "refbased": sorted(rb), "membership": sorted(mb)})
            if len(rb) > len(mb):
                more_ref += 1
            elif len(mb) > len(rb):
                more_memb += 1
    mism.sort(key=lambda x: x["id"])
    return {
        "n_checked": len(p_citers),
        "n_mismatch": len(mism),
        "n_referenced_works_has_more": more_ref,
        "n_membership_has_more": more_memb,
        "examples": mism[:20],
    }


# ================= indicadores por janela =================


def point_estimates(cp, rc, rwc):
    def agg(l):
        is_i, is_j, is_k = counts_l(cp, rc, l)
        return int(is_i.sum()), int(is_j.sum()), int(is_k.sum())

    ni, nj, nk = agg(1)
    ni2, nj2, nk2 = agg(2)
    ni5, nj5, nk5 = agg(5)
    is_i_h = cp & (rc < 1) & (rwc != 0)
    nih = int(is_i_h.sum())
    return {
        "n_i": ni,
        "n_j": nj,
        "n_k": nk,
        "CD": cd_index(ni, nj, nk),
        "CD_nok": cd_nok_index(ni, nj),
        "DI2": {"n_i": ni2, "n_j": nj2, "n_k": nk2, "value": cd_index(ni2, nj2, nk2)},
        "DI5": {"n_i": ni5, "n_j": nj5, "n_k": nk5, "value": cd_index(ni5, nj5, nk5)},
        "holst": {"n_i": nih, "n_j": nj, "n_k": nk, "CD": cd_index(nih, nj, nk)},
    }


def bootstrap_ci(cp, rc, rwc, B=B_BOOTSTRAP, seed=SEED):
    """Bootstrap percentil 95% sobre as obras da janela (reamostra com
    reposição, B réplicas), vetorizado em numpy. Devolve None-None quando
    a janela está vazia ou quando o indicador dá 0/0 em réplicas
    suficientes para o percentil cair em NaN nas duas pontas."""
    n = cp.size
    keys = ("CD", "CD_nok", "DI2", "DI5", "holst_CD")
    if n == 0:
        return {k: [None, None] for k in keys}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(B, n))
    CP, RC, RWC = cp[idx], rc[idx], rwc[idx]

    def ratio(ni, nj, nk):
        ni, nj, nk = ni.astype(np.float64), nj.astype(np.float64), nk.astype(np.float64)
        den = ni + nj + nk
        with np.errstate(invalid="ignore", divide="ignore"):
            r = (ni - nj) / den
        r[den == 0] = np.nan
        return r

    def ratio_nok(ni, nj):
        ni, nj = ni.astype(np.float64), nj.astype(np.float64)
        den = ni + nj
        with np.errstate(invalid="ignore", divide="ignore"):
            r = (ni - nj) / den
        r[den == 0] = np.nan
        return r

    def pct(arr):
        lo, hi = np.nanpercentile(arr, [2.5, 97.5])
        return [
            None if np.isnan(lo) else float(lo),
            None if np.isnan(hi) else float(hi),
        ]

    is_j1 = CP & (RC >= 1)
    is_i1 = CP & (RC < 1)
    is_k1 = (~CP) & (RC >= 1)
    ni1, nj1, nk1 = is_i1.sum(1), is_j1.sum(1), is_k1.sum(1)
    is_j2 = CP & (RC >= 2)
    is_i2 = CP & (RC < 2)
    is_k2 = (~CP) & (RC >= 2)
    ni2, nj2, nk2 = is_i2.sum(1), is_j2.sum(1), is_k2.sum(1)
    is_j5 = CP & (RC >= 5)
    is_i5 = CP & (RC < 5)
    is_k5 = (~CP) & (RC >= 5)
    ni5, nj5, nk5 = is_i5.sum(1), is_j5.sum(1), is_k5.sum(1)
    is_ih = CP & (RC < 1) & (RWC != 0)
    nih = is_ih.sum(1)

    return {
        "CD": pct(ratio(ni1, nj1, nk1)),
        "CD_nok": pct(ratio_nok(ni1, nj1)),
        "DI2": pct(ratio(ni2, nj2, nk2)),
        "DI5": pct(ratio(ni5, nj5, nk5)),
        "holst_CD": pct(ratio(nih, nj1, nk1)),
    }


def compute_window(mask, cp, rc, rwc):
    idx = np.nonzero(mask)[0]
    sub_cp, sub_rc, sub_rwc = cp[idx], rc[idx], rwc[idx]
    pe = point_estimates(sub_cp, sub_rc, sub_rwc)
    pe["ci_95"] = bootstrap_ci(sub_cp, sub_rc, sub_rwc)
    pe["n_window"] = int(idx.size)
    return pe, idx


# ================= leave-one-reference-out (CD5 base) =================


def loo_cd5(window_ids, cp5, cites_r_of, r_valid_sorted):
    n, R = len(window_ids), len(r_valid_sorted)
    if n == 0 or R == 0:
        return {}
    r_index = {r: j for j, r in enumerate(r_valid_sorted)}
    memb = np.zeros((n, R), dtype=np.int32)
    for i, wid in enumerate(window_ids):
        for r in cites_r_of.get(wid, ()):
            j = r_index.get(r)
            if j is not None:
                memb[i, j] = 1
    rc_full = memb.sum(axis=1)
    rc_minus = (
        rc_full[:, None] - memb
    )  # (n, R): rc de cada obra sem a referência da coluna
    cp_col = cp5[:, None]
    is_j = cp_col & (rc_minus >= 1)
    is_i = cp_col & (rc_minus == 0)
    is_k = (~cp_col) & (rc_minus >= 1)
    ni = is_i.sum(axis=0).astype(np.float64)
    nj = is_j.sum(axis=0).astype(np.float64)
    nk = is_k.sum(axis=0).astype(np.float64)
    den = ni + nj + nk
    with np.errstate(invalid="ignore", divide="ignore"):
        cd_minus = (ni - nj) / den
    cd_minus[den == 0] = np.nan
    return {
        r_valid_sorted[j]: (None if np.isnan(cd_minus[j]) else float(cd_minus[j]))
        for j in range(R)
    }


# ================= cruzamento com classify.json (t=5 base) =================


def role_or_depth(entry):
    """`classify.json` schema 1 guarda o eixo em `role`; schema 2
    (METHOD.md@v2, migrado em 2026-09-04 -- ver CLAUDE.md e
    auditlib.TAXONOMIA_V2) removeu `role` do topo da entrada e usa
    `depth`, com o MESMO vocabulário para os papéis substantivos que
    interessam aqui ("supporting"/"foundational" --
    auditlib.TAXONOMIA_V2["depth"]["values"], e a própria
    auditlib.role_flag_v1() projeta v2->v1 fazendo role=depth fora do
    caso "misrepresented"). Conferido nos dados: data/classify.json deste
    repositório já está em schema 2 hoje (0/104 entradas com "role", só
    "depth") -- sem este fallback, `entry.get("role")` abaixo devolveria
    None para toda entrada, e o cruzamento i/j x papel substantivo (e o
    teste de Fisher sobre ele) sairia degenerado (tabela com uma coluna
    inteira zerada), mascarando qualquer sinal real. Mantém a leitura de
    `role` primeiro para não quebrar se o arquivo voltar a ser schema 1."""
    r = entry.get("role")
    return r if r is not None else entry.get("depth")


def crosstab(window_ids, cp5, rc5, p_citers, classify_entries):
    role_counts = {"i": collections.Counter(), "j": collections.Counter()}
    stance_counts = {"i": collections.Counter(), "j": collections.Counter()}
    matched = {"i": 0, "j": 0}
    for wid, cp_, rc_ in zip(window_ids, cp5, rc5):
        if not cp_:
            continue
        status = "i" if rc_ == 0 else "j"
        info = p_citers.get(wid)
        doi = info["doi"] if info else None
        if not doi:
            continue
        entry = classify_entries.get(doi)
        if not entry:
            continue
        matched[status] += 1
        # "or 'sem_depth_role'": role_or_depth() devolve None de propósito
        # quando presence != in_text (reference_list_only/not_cited --
        # ver METHOD.md §16, "Só se aplica quando presence = in_text") --
        # um citante de p no grafo de citação pode muito bem ter uma
        # classificação dessas em classify.json (citação-fantasma: está
        # no grafo, mas o texto não discute o artigo-foco). Sem esta
        # coerção pra string, o dict de contagem mistura chave None com
        # chaves string, e json.dump(sort_keys=True) quebra tentando
        # comparar None < str (achado rodando o grains de verdade: o
        # airline não tinha nenhum caso assim entre os citantes de t=5,
        # o grains tem). Não afeta a classificação em si -- essa chave
        # nunca está em SUBSTANTIVE_ROLES de qualquer forma, com ou sem
        # a coerção.
        role_counts[status][role_or_depth(entry) or "sem_depth_role"] += 1
        stance_counts[status][entry.get("stance") or "sem_stance"] += 1
    a = sum(c for r, c in role_counts["i"].items() if r in SUBSTANTIVE_ROLES)
    b = matched["i"] - a
    c_ = sum(c for r, c in role_counts["j"].items() if r in SUBSTANTIVE_ROLES)
    d = matched["j"] - c_
    table = [[a, b], [c_, d]]
    return {
        "n_classified": matched,
        "role": {k: dict(v) for k, v in role_counts.items()},
        "stance": {k: dict(v) for k, v in stance_counts.items()},
        "fisher_substantive": {
            "table_rows_i_j__cols_substantive_other": table,
            "p_two_sided": fisher_exact_2x2(table),
        },
    }


# ================= por artigo =================


def process_paper(
    paper,
    client,
    cap_per_ref,
    snapshot_date,
    current_year,
    backend="openalex",
    remap=False,
):
    print(f"\n=== {paper} ({backend}) ===")
    refs_audit = load_refs_audit(paper)
    y_p = refs_audit["focal"][
        "year"
    ]  # SEMPRE do OpenAlex (refs_audit) -- ver decisão #3 em s2_client.py:
    # o campo "year" que o S2 devolve pro artigo-foco está errado nos dois artigos (checado manualmente),
    # então as janelas t nunca usam o "year" do S2, só o de refs_audit_<artigo>.json.
    focal_openalex_id = oax.short_id(refs_audit["focal"]["openalex_id"])
    cited_by_count = refs_audit["focal"]["cited_by_count"] or 0
    s2_citation_count = None
    id_mapping_out = None

    if backend == "s2":
        # retry_unmapped=remap (default False): por padrão, uma vez que
        # data/cd/id_map_<artigo>.json existe, esta chamada só LÊ (nenhuma
        # rede) -- essencial para a corrida "rodar 2x e comparar
        # byte-a-byte" não fazer chamadas novas na 2a vez (o que poderia
        # mudar quem está mapeado/sem-mapear entre as duas corridas e
        # quebrar a comparação). `--remap` liga retentativa das entradas
        # "unmapped" -- usado nas passadas de construção do id_map, não
        # nas corridas "oficiais" de CD index.
        id_map = s2c.ensure_id_map(
            client, paper, refs_audit, snapshot_date, retry_unmapped=remap
        )
        p_id = id_map["focal"]["s2_paper_id"]
        if not p_id:
            raise SystemExit(
                f"erro: não consegui resolver o artigo-foco '{paper}' no S2 "
                f"(DOI {refs_audit['focal']['doi']}) -- ver data/cd/id_map_{paper}.json"
            )
        s2_citation_count = id_map["focal"]["s2_citation_count"]
        # set() por precaução: duas referências distintas do PDF caindo no
        # mesmo paperId do S2 seria raro (exigiria um erro de busca por
        # título), mas sorted() sozinho não removeria a duplicata de
        # r_valid (viraria uma referência processada duas vezes em
        # fetch_r_citers/loo_cd5 -- redundante, não incorreto, mas sem
        # motivo para não blindar).
        r_valid = sorted({v["s2_paper_id"] for v in id_map["mapped"].values()})
        id_mapping_out = {
            "id_map_file": f"data/cd/id_map_{paper}.json",
            "n_r_valid_openalex": refs_audit["n_valid"],
            "n_mapped": id_map["n_mapped"],
            "n_unmapped": id_map["n_unmapped"],
            "unmapped": id_map["unmapped"],
        }
        print(
            f"  foco (S2 paperId) {p_id} -- R_valid mapeado: {len(r_valid)}/{refs_audit['n_valid']} "
            f"({id_map['n_unmapped']} sem mapeamento, ver data/cd/id_map_{paper}.json)"
        )
    else:
        p_id = focal_openalex_id
        r_valid = sorted(refs_audit["r_valid"])
    r_valid_set = set(r_valid)
    print(f"  foco {p_id} (ano {y_p}), R_valid = {len(r_valid)} referências")

    print("  buscando TODOS os citantes do foco (sem filtro de ano)...")
    p_citers = fetch_p_citers(client, p_id, r_valid_set)
    print(
        f"  {len(p_citers)} citantes do foco (OpenAlex cited_by_count = {cited_by_count})"
    )

    print(
        f"  buscando citantes de cada uma das {len(r_valid)} referências válidas "
        f"em [{y_p}, {y_p + 10}] (paralelo)..."
    )
    cites_r_of, work_year, counts_per_ref = fetch_r_citers(
        client, r_valid, y_p, cap_per_ref
    )
    print(f"  {len(cites_r_of)} obras distintas citam >=1 referência válida")

    disc = discrepancies(p_citers, cites_r_of)
    print(
        f"  discrepâncias referenced_works x pertença: {disc['n_mismatch']}/{disc['n_checked']}"
    )

    all_ids, years, cp, rc, rwc = build_arrays(p_citers, cites_r_of, work_year)

    windows_spec = resolve_windows(y_p, current_year)
    windows_out, windows_strict_out = {}, {}
    w5_ids = w5_cp = w5_rc = None

    for spec in windows_spec:
        t_nom, t_use, trunc = spec["t_nominal"], spec["t"], spec["truncated"]

        mask = (years >= y_p) & (years <= y_p + t_use)
        pe, idx = compute_window(mask, cp, rc, rwc)
        pe.update(t_nominal=t_nom, t=t_use, truncated=trunc)
        p_in_window = int((mask & cp).sum())
        assert pe["n_i"] + pe["n_j"] == p_in_window, (
            "bug: n_i+n_j != citantes de p na janela"
        )
        pe["checks"] = {
            "ni_plus_nj": pe["n_i"] + pe["n_j"],
            "p_citers_in_window": p_in_window,
            "ni_plus_nj_eq_p_citers_in_window": True,
            "ni_plus_nj_le_cited_by_count": (pe["n_i"] + pe["n_j"]) <= cited_by_count,
            "ni_plus_nj_le_s2_citation_count": (
                (pe["n_i"] + pe["n_j"]) <= s2_citation_count
                if s2_citation_count is not None
                else None
            ),
        }
        windows_out[str(t_nom)] = pe

        mask_s = (years > y_p) & (years <= y_p + t_use)
        pe_s, _idx_s = compute_window(mask_s, cp, rc, rwc)
        pe_s.update(t_nominal=t_nom, t=t_use, truncated=trunc)
        p_in_window_s = int((mask_s & cp).sum())
        assert pe_s["n_i"] + pe_s["n_j"] == p_in_window_s
        pe_s["checks"] = {
            "ni_plus_nj": pe_s["n_i"] + pe_s["n_j"],
            "p_citers_in_window": p_in_window_s,
            "ni_plus_nj_eq_p_citers_in_window": True,
            "ni_plus_nj_le_cited_by_count": (pe_s["n_i"] + pe_s["n_j"])
            <= cited_by_count,
            "ni_plus_nj_le_s2_citation_count": (
                (pe_s["n_i"] + pe_s["n_j"]) <= s2_citation_count
                if s2_citation_count is not None
                else None
            ),
        }
        windows_strict_out[str(t_nom)] = pe_s

        if t_nom == 5:
            w5_ids = [all_ids[i] for i in idx]
            w5_cp, w5_rc = cp[idx], rc[idx]

    cd5_full = windows_out["5"]["CD"]
    loo_map = loo_cd5(w5_ids, w5_cp, cites_r_of, r_valid) if w5_ids is not None else {}
    loo_rows = []
    for r in r_valid:
        cd_wo = loo_map.get(r)
        delta = None if (cd_wo is None or cd5_full is None) else (cd5_full - cd_wo)
        loo_rows.append({"r": r, "cd5_without_r": cd_wo, "delta": delta})
    loo_ranked = sorted(
        (x for x in loo_rows if x["delta"] is not None), key=lambda x: -abs(x["delta"])
    )

    classify_entries = auditlib.classify_entries(auditlib.load_classify())
    ct = (
        crosstab(w5_ids, w5_cp, w5_rc, p_citers, classify_entries)
        if w5_ids is not None
        else None
    )

    return {
        "paper": paper,
        "focal": {
            "doi": refs_audit["focal"]["doi"],
            "openalex_id": focal_openalex_id,
            "s2_paper_id": p_id if backend == "s2" else None,
            "year": y_p,
            "cited_by_count": cited_by_count,
            "s2_citation_count": s2_citation_count,
        },
        "n_r_valid": len(r_valid),
        "r_valid": r_valid,
        "id_mapping": id_mapping_out,
        "n_p_citers_all_time": len(p_citers),
        "checks_global": {
            "n_p_citers_all_time": len(p_citers),
            "cited_by_count": cited_by_count,
            "n_p_citers_le_cited_by_count": len(p_citers) <= cited_by_count,
            "s2_citation_count": s2_citation_count,
            "n_p_citers_le_s2_citation_count": (
                len(p_citers) <= s2_citation_count
                if s2_citation_count is not None
                else None
            ),
        },
        "citers_per_reference": counts_per_ref,
        "windows": windows_out,
        "windows_strict": windows_strict_out,
        "loo_cd5": {
            "cd5_full": cd5_full,
            "all": loo_rows,
            "top5_abs_delta": loo_ranked[:5],
        },
        "crosstab_t5": ct,
        "discrepancies_referenced_works_vs_membership": disc,
        "cap_per_ref": cap_per_ref,
    }


def fmt(x, nd=4):
    return "None" if x is None else f"{x:.{nd}f}"


def print_report(paper, result):
    w5 = result["windows"]["5"]
    print(
        f"\n--- {paper}: janela t=5 (t_real={w5['t']}, truncado={w5['truncated']}) ---"
    )
    print(
        f"  n_i={w5['n_i']}  n_j={w5['n_j']}  n_k={w5['n_k']}  n_janela={w5['n_window']}"
    )
    print(f"  CD5      = {fmt(w5['CD'])}   IC95% {w5['ci_95']['CD']}")
    print(f"  CD5_nok  = {fmt(w5['CD_nok'])}   IC95% {w5['ci_95']['CD_nok']}")
    print(f"  DI2      = {fmt(w5['DI2']['value'])}   IC95% {w5['ci_95']['DI2']}")
    print(f"  DI5      = {fmt(w5['DI5']['value'])}   IC95% {w5['ci_95']['DI5']}")
    print(f"  Holst CD = {fmt(w5['holst']['CD'])}   IC95% {w5['ci_95']['holst_CD']}")
    print(f"  checks: {w5['checks']}")
    print("  LOO top-5 |delta CD5| (referência removida -> CD5 sem ela):")
    for row in result["loo_cd5"]["top5_abs_delta"]:
        print(
            f"    {row['r']}: CD5_sem = {fmt(row['cd5_without_r'])}   delta = {fmt(row['delta'])}"
        )
    ct = result["crosstab_t5"]
    if ct:
        print(f"  crosstab i/j x role: {ct['role']}")
        f = ct["fisher_substantive"]
        print(
            f"  fisher (i/j x substantivo/outro): tabela={f['table_rows_i_j__cols_substantive_other']} "
            f"p={f['p_two_sided']:.4g}"
        )
    disc = result["discrepancies_referenced_works_vs_membership"]
    print(
        f"  discrepâncias referenced_works x pertença: {disc['n_mismatch']}/{disc['n_checked']}"
    )
    if result.get("backend") == "semanticscholar":
        foc = result["focal"]
        print(
            f"  citationCount: S2={foc['s2_citation_count']}  OpenAlex_cited_by_count={foc['cited_by_count']}"
        )
        idm = result.get("id_mapping") or {}
        if idm.get("n_unmapped"):
            print(
                f"  AVISO: {idm['n_unmapped']} referência(s) de R_valid sem mapeamento S2 "
                f"(excluídas -- ver data/cd/id_map_{paper}.json)"
            )
        caps = result.get("s2_pagination_caps_hit") or []
        if caps:
            print(
                f"  AVISO: teto de paginação do S2 (offset+limit<=10000) atingido em: {caps}"
            )


def parse_args():
    p = argparse.ArgumentParser(
        description="Índice de disrupção (CD, CD_nok, DI2, DI5, Holst) sobre R_valid de cada "
        "artigo-foco, com bootstrap, leave-one-reference-out e cruzamento com classify.json.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--paper",
        choices=sorted(CFG["papers"]),
        action="append",
        help="processa só este artigo (repetível); default: todos",
    )
    p.add_argument(
        "--cap-per-ref",
        type=int,
        default=None,
        help="válvula de segurança: limite de citantes buscados por referência (default: sem limite)",
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
        help="(só --backend s2) tenta de novo as referências de R_valid que ficaram sem "
        "mapeamento S2 numa corrida anterior, em vez de só ler data/cd/id_map_<artigo>.json "
        "como está; use em passadas de convergência do id_map, NÃO nas corridas oficiais "
        "(quebraria a comparação byte-a-byte entre duas corridas)",
    )
    p.add_argument(
        "--selftest",
        action="store_true",
        help="roda os testes unitários das fórmulas (CD, CD_nok, DI2, fisher_exact_2x2) e sai, sem rede",
    )
    return p.parse_args()


def main():
    args = parse_args()
    if args.selftest:
        selftest()
        return
    papers = args.paper or sorted(CFG["papers"])
    if args.backend == "s2":
        client = s2c.S2Client(use_cache=not args.no_cache)
        backend_name = "semanticscholar"
    else:
        client = oax.OpenAlexClient(use_cache=not args.no_cache)
        backend_name = "openalex"
    snapshot_date = datetime.now(tz=timezone.utc).date().isoformat()
    current_year = int(snapshot_date[:4])
    for paper in papers:
        before = (client.n_network, client.n_cache_hit, client.n_none)
        result = process_paper(
            paper,
            client,
            args.cap_per_ref,
            snapshot_date,
            current_year,
            backend=args.backend,
            remap=args.remap,
        )
        after = (client.n_network, client.n_cache_hit, client.n_none)
        net, hits, none_ = (after[i] - before[i] for i in range(3))
        result["snapshot_date"] = snapshot_date
        result["backend"] = backend_name
        result["requests"] = {
            "network": net,
            "cache_hits": hits,
            "none_responses": none_,
            "total": net + hits,
        }
        result["s2_pagination_caps_hit"] = (
            sorted(client.truncated_ids) if args.backend == "s2" else []
        )
        result["seed"] = SEED
        result["B"] = B_BOOTSTRAP
        out_path = auditlib.DATA / "cd" / f"cd_{paper}.json"
        oax.save_json(result, out_path)
        print(f"-> {out_path}")
        print_report(paper, result)
    print(
        f"\ntotal rede: {client.n_network}  cache: {client.n_cache_hit}  nulos: {client.n_none}"
    )


if __name__ == "__main__":
    main()

# ---------------- decisões ambíguas (ver relatório final) ----------------
# 1. DI_l restrito a citantes de p (a regra "quem não bate o limiar l cai
#    em n_i" só se aplica a quem cita p): o enunciado diz "a citer counts
#    as 'cites R' only if it cites >=l members of R_valid, else counts
#    toward n_i" -- lido ao pé da letra, isso jogaria QUALQUER citante
#    (inclusive quem não cita p) para n_i, o que não faz sentido (n_i é
#    por definição quem cita p). Interpretação implementada: a regra
#    reclassifica só quem já cita p entre n_i^l/n_j^l pelo limiar l; quem
#    não cita p e fica abaixo do limiar l simplesmente sai do universo de
#    DI_l (não conta em nenhum dos três grupos) -- é o desenho usual de
#    DI5 na literatura (Bornmann, Devarakonda, Tekles 2020).
# 2. Cruzamento com classify.json e LOO usam a janela t=5 base (não
#    estrita, l=1): o enunciado não fixa qual janela usar para o
#    cruzamento; t=5 é a janela "manchete" pedida no relatório final, e
#    LOO em CD5 é pedido explicitamente.
# 3. DOI dos citantes de p vem do próprio select da consulta (a),
#    ampliado com "doi" (select = SELECT_P_CITERS em openalex_client.py)
#    em vez de uma segunda chamada separada ou de cruzar com o campo
#    "openalex" de master.json -- o enunciado oferece as duas rotas como
#    alternativas ("use master.json openalex field or the citers' doi
#    from a second select"); usar direto evita repetir a paginação
#    inteira dos citantes de p só para pegar mais um campo.
# 4. "cites r" na classificação usa sempre a pertença nas listas
#    por-referência (nunca `referenced_works` do citante), inclusive para
#    quem cita p -- é o que o enunciado pede explicitamente ("never fetch
#    citers' full reference lists for n_k"); `referenced_works` dos
#    citantes de p é usado só para o log de discrepâncias.
# 5. --backend s2: y_p (ano do artigo-foco, base das janelas t) SEMPRE
#    vem de refs_audit_<artigo>.json (OpenAlex, via audit_64), nunca do
#    campo "year" que o S2 devolve para o artigo-foco -- checado
#    manualmente, esse campo está errado no S2 para os dois artigos (ver
#    decisão #3 em s2_client.py). `p_id`/`r_valid` passam a ser S2
#    paperId (mapeados de R_valid por data/cd/id_map_<artigo>.json,
#    construído por s2_client.ensure_id_map); o resto do pipeline
#    (fetch_p_citers, fetch_r_citers, build_arrays, bootstrap, LOO,
#    crosstab) não muda uma linha porque trata todo ID como string opaca.
# 6. role_or_depth() (usada em crosstab): data/classify.json está em
#    schema 2 (METHOD.md@v2) desde a migração de hoje -- não tem mais
#    `role` no topo da entrada, só `depth`. `entry.get("role")` sozinho
#    (o código original) devolveria None para as 104/104 entradas atuais
#    e degeneraria o cruzamento i/j x papel substantivo (e o Fisher sobre
#    ele) numa tabela com coluna zerada. Corrigido para ler `role` quando
#    presente (schema 1) e cair para `depth` quando não (schema 2) --
#    mesmo vocabulário nos dois para os papéis que importam aqui
#    ("supporting"/"foundational"), ver auditlib.role_flag_v1().
