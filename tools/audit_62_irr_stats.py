"""audit_62_irr_stats.py — estatísticas de confiabilidade entre codificadores
(inter-rater reliability) para o pacote cego de audit_61_irr_pack.py, mais
inferência com poder de predição (PPI) para as taxas do estudo.

Módulo + CLI. numpy + stdlib. Implementa:
  - α de Krippendorff nominal, ordinal e intervalar — fórmula geral com matriz
    de coincidências; valores ausentes tratados (a unidade entra se tem >= 2
    valores). Uma segunda implementação, direta pela definição (pares dentro
    de cada unidade), serve de validação cruzada em --selftest.
  - κ de Cohen sem peso, com peso linear e com peso quadrático
  - concordância bruta, prevalência por categoria,
    PABAK = (k·p_o − 1)/(k − 1)  (= 2·p_o − 1 para k = 2), AC1 de Gwet,
    Jaccard para conjuntos multi-rótulo
  - IC bootstrap percentílico sobre itens (B = 2000, semente fixa)
  - PPI (Angelopoulos, Bates, Fannjiang, Jordan & Zrnic 2023):
      θ̂_PP = média_N f(Ŷ) − média_n[f(Ŷ) − f(Y)]
      Var   = Var_N f(Ŷ)/N + Var_n[f(Ŷ) − f(Y)]/n,   IC normal
    e o λ de power tuning do PPI++ (Angelopoulos, Duchi & Zrnic 2023):
      λ̂ = Cov_n(f(Ŷ), f(Y)) / (Var_N f(Ŷ) · (1 + n/N)), recortado a [0, 1]

Uso:
  python3 tools/audit_62_irr_stats.py --c1 A.json --c2 B.json [--c3 C.json]
        [--human H.json] --key data/irr/pack_key.json --out data/irr/irr_stats.json
        [--B 2000] [--seed 20260904] [--lenient]
  python3 tools/audit_62_irr_stats.py --selftest [--root PATH]

Arquivos de codificador: {item_id: {presence, depth, stance, accuracy,
distortion, reuse[], claim_ids[], ...}} — campos extras são ignorados.
Itens marcados `codebook_exemplar` na chave ficam fora das estatísticas
primárias (o codificador os viu rotulados nos casos de fronteira); a linha
`sensitivity_with_exemplars` os inclui. Itens duplicados (`duplicate_of`)
alimentam só a concordância intra-codificador. `--human` é um arquivo no
mesmo formato com os rótulos humanos de um subconjunto aleatório; o PPI usa
`--c1` como rótulo de máquina f(Ŷ) sobre todos os itens.
"""

import argparse
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
JSON_KW = {"sort_keys": True, "indent": 1, "ensure_ascii": False}
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from audit_60_taxonomy_v2 import (
        ACCURACY,
        DEPTH,
        DISTORTION,
        PRESENCE,
        REUSE,
        STANCE,
    )
except ImportError:  # standalone
    PRESENCE = ["in_text", "reference_list_only", "not_cited"]
    DEPTH = ["drive_by", "brief_mention", "real_mention", "supporting", "foundational"]
    ACCURACY = ["accurate", "imprecise", "misrepresented"]
    DISTORTION = ["dead_end", "diversion", "transmutation", "relayed_attribution"]
    STANCE = ["none", "supporting", "contradictory"]
    REUSE = [
        "method_adoption",
        "result_validated",
        "dataset_reuse",
        "benchmarking",
        "work_extended",
    ]

NAN = float("nan")
SUBSTANTIVE = ("supporting", "foundational")
BINARY = ["no", "yes"]


def _isnan(x):
    return x is None or (isinstance(x, float) and math.isnan(x))


def _f(x):
    return None if _isnan(x) else float(x)


# =====================================================================
# núcleo estatístico
# =====================================================================


def _coincidence(data, categories):
    """Matriz de coincidências o_ck (Krippendorff): para cada unidade com
    m >= 2 valores, cada par ordenado de valores distintos por posição soma
    1/(m − 1)."""
    idx = {c: i for i, c in enumerate(categories)}
    K = len(categories)
    o = np.zeros((K, K))
    n_units = len(data[0]) if data else 0
    for u in range(n_units):
        vals = [idx[row[u]] for row in data if row[u] is not None]
        m = len(vals)
        if m < 2:
            continue
        w = 1.0 / (m - 1)
        for i in range(m):
            for j in range(m):
                if i != j:
                    o[vals[i], vals[j]] += w
    return o


def _delta2(metric, n_c, values=None):
    """δ² por par de categorias: nominal 0/1; intervalar (r_c − r_k)² sobre os
    postos (1..K) ou valores numéricos dados; ordinal (Σ_{g=c}^{k} n_g −
    (n_c + n_k)/2)² — usa as frequências marginais das coincidências."""
    K = len(n_c)
    if metric == "nominal":
        return 1.0 - np.eye(K)
    if metric == "interval":
        r = np.asarray(
            values if values is not None else np.arange(1, K + 1), dtype=float
        )
        return (r[:, None] - r[None, :]) ** 2
    if metric == "ordinal":
        d = np.zeros((K, K))
        for c in range(K):
            for k in range(c + 1, K):
                s = n_c[c : k + 1].sum() - (n_c[c] + n_c[k]) / 2.0
                d[c, k] = d[k, c] = s * s
        return d
    raise ValueError(f"métrica desconhecida: {metric}")


def krippendorff_alpha(data, metric="nominal", categories=None, values=None):
    """α = 1 − (n − 1) Σ_ck o_ck δ²_ck / Σ_ck n_c n_k δ²_ck.
    `data`: lista de linhas (uma por codificador), None = ausente.
    `categories`: ordem das categorias (define os postos em ordinal/intervalar)."""
    if categories is None:
        categories = sorted({v for row in data for v in row if v is not None}, key=str)
    o = _coincidence(data, categories)
    n_c = o.sum(axis=1)
    n = n_c.sum()
    if n < 2:
        return NAN
    d2 = _delta2(metric, n_c, values)
    D_o = (o * d2).sum()
    D_e = (np.outer(n_c, n_c) * d2).sum()
    if D_e == 0:
        return NAN
    return float(1.0 - (n - 1) * D_o / D_e)


def krippendorff_alpha_direct(data, metric="nominal", categories=None, values=None):
    """Implementação independente pela definição: α = 1 − D_o/D_e, com
    D_o = (1/n) Σ_u [Σ_{i≠j em u} δ²(v_i, v_j)] / (m_u − 1) e
    D_e = [Σ_{i≠j no conjunto agrupado} δ²(v_i, v_j)] / (n(n − 1)).
    Só para validação cruzada (O(n²))."""
    if categories is None:
        categories = sorted({v for row in data for v in row if v is not None}, key=str)
    idx = {c: i for i, c in enumerate(categories)}
    K = len(categories)
    units = []
    for u in range(len(data[0])):
        vals = [idx[row[u]] for row in data if row[u] is not None]
        if len(vals) >= 2:
            units.append(vals)
    pooled = [v for vals in units for v in vals]
    n = len(pooled)
    if n < 2:
        return NAN
    counts = np.bincount(pooled, minlength=K).astype(float)
    r = np.asarray(values if values is not None else np.arange(1, K + 1), dtype=float)

    def d2(a, b):
        if a == b:
            return 0.0
        if metric == "nominal":
            return 1.0
        if metric == "interval":
            return float((r[a] - r[b]) ** 2)
        lo, hi = min(a, b), max(a, b)
        return float((counts[lo : hi + 1].sum() - (counts[lo] + counts[hi]) / 2.0) ** 2)

    D_o = (
        sum(
            sum(d2(v[i], v[j]) for i in range(len(v)) for j in range(len(v)) if i != j)
            / (len(v) - 1)
            for v in units
        )
        / n
    )
    D_e = sum(
        d2(a, b) for i, a in enumerate(pooled) for j, b in enumerate(pooled) if i != j
    ) / (n * (n - 1))
    if D_e == 0:
        return NAN
    return float(1.0 - D_o / D_e)


def confusion(a, b, categories):
    idx = {c: i for i, c in enumerate(categories)}
    M = np.zeros((len(categories), len(categories)))
    for x, y in zip(a, b):
        if x is not None and y is not None:
            M[idx[x], idx[y]] += 1
    return M


def cohen_kappa(a, b, categories, weights=None):
    """κ = 1 − Σ w_ij p_ij / Σ w_ij p_i. p_.j, com w = 1 − I (sem peso),
    |i − j|/(K − 1) (linear) ou ((i − j)/(K − 1))² (quadrático)."""
    M = confusion(a, b, categories)
    n = M.sum()
    if n == 0:
        return NAN
    P = M / n
    pa, pb = P.sum(axis=1), P.sum(axis=0)
    K = len(categories)
    i = np.arange(K)
    if weights is None:
        W = 1.0 - np.eye(K)
    elif weights == "linear":
        W = np.abs(i[:, None] - i[None, :]) / max(K - 1, 1)
    elif weights == "quadratic":
        W = ((i[:, None] - i[None, :]) / max(K - 1, 1)) ** 2
    else:
        raise ValueError(weights)
    po_dis = (W * P).sum()
    pe_dis = (W * np.outer(pa, pb)).sum()
    if pe_dis == 0:
        return NAN
    return float(1.0 - po_dis / pe_dis)


def raw_agreement(a, b):
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if not pairs:
        return NAN
    return float(sum(x == y for x, y in pairs) / len(pairs))


def within_one(a, b, categories):
    """Concordância a ±1 posto (ordinal)."""
    rank = {c: i for i, c in enumerate(categories)}
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if not pairs:
        return NAN
    return float(sum(abs(rank[x] - rank[y]) <= 1 for x, y in pairs) / len(pairs))


def pabak(p_o, k=2):
    """PABAK de Byrt, Bishop & Carlin (1993): (k·p_o − 1)/(k − 1); k = 2 dá 2·p_o − 1."""
    if _isnan(p_o) or k < 2:
        return NAN
    return float((k * p_o - 1.0) / (k - 1.0))


def gwet_ac1(a, b, categories):
    """AC1 de Gwet: p_e = (1/(K − 1)) Σ_q π_q (1 − π_q), π_q = média entre os
    dois codificadores da proporção na categoria q."""
    M = confusion(a, b, categories)
    n = M.sum()
    if n == 0:
        return NAN
    P = M / n
    K = len(categories)
    p_o = float(np.trace(P))
    pi = (P.sum(axis=1) + P.sum(axis=0)) / 2.0
    p_e = float((pi * (1 - pi)).sum() / max(K - 1, 1))
    if p_e >= 1:
        return NAN
    return float((p_o - p_e) / (1 - p_e))


def prevalence(a, b, categories):
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    n = len(pairs)
    out = {}
    for c in categories:
        pa = sum(x == c for x, _ in pairs) / n if n else NAN
        pb = sum(y == c for _, y in pairs) / n if n else NAN
        out[c] = {
            "coder_a": _f(pa),
            "coder_b": _f(pb),
            "mean": _f((pa + pb) / 2) if n else None,
        }
    return out


def jaccard_sets(A, B):
    """Média por item de |A∩B|/|A∪B|; dois conjuntos vazios contam 1."""
    vals = []
    for x, y in zip(A, B):
        if x is None or y is None:
            continue
        x, y = set(x), set(y)
        vals.append(1.0 if not x and not y else len(x & y) / len(x | y))
    return float(np.mean(vals)) if vals else NAN


def bootstrap_block(stats_fn, n, B=2000, seed=20260904, level=0.95):
    """IC percentílico sobre itens para um bloco de estatísticas:
    `stats_fn(idx)` devolve {nome: valor} para os índices reamostrados."""
    if n == 0:
        return {}
    rng = np.random.default_rng(seed)
    acc = {}
    for _ in range(B):
        for k, v in stats_fn(rng.integers(0, n, n)).items():
            if not _isnan(v):
                acc.setdefault(k, []).append(v)
    out = {}
    for k, vals in acc.items():
        lo, hi = np.percentile(vals, [100 * (1 - level) / 2, 100 * (1 + level) / 2])
        out[k] = {"lo": float(lo), "hi": float(hi), "B_valid": len(vals)}
    return out


def z_value(alpha):
    """Quantil normal bilateral por bissecção sobre erf (sem scipy)."""
    target = 1 - alpha / 2
    lo, hi = 0.0, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if 0.5 * (1 + math.erf(mid / math.sqrt(2))) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def ppi_mean(f_hat_all, f_hat_lab, f_lab, alpha=0.05, tune=True):
    """PPI para a média. `tune=True` aplica o λ do PPI++; `tune=False` é o
    PPI original (λ = 1)."""
    yh = np.asarray(f_hat_all, dtype=float)
    yl_hat = np.asarray(f_hat_lab, dtype=float)
    yl = np.asarray(f_lab, dtype=float)
    N, n = len(yh), len(yl)
    if N == 0 or n == 0 or len(yl_hat) != n:
        return None
    var_hat = float(np.var(yh, ddof=1)) if N > 1 else 0.0
    if tune and n > 1 and var_hat > 0:
        cov = float(np.cov(yl_hat, yl, ddof=1)[0, 1])
        lam = min(max(cov / (var_hat * (1 + n / N)), 0.0), 1.0)
    else:
        lam = 1.0
    rect = yl - lam * yl_hat
    theta = float(lam * yh.mean() + rect.mean())
    var_rect = float(np.var(rect, ddof=1)) if n > 1 else 0.0
    var = (lam**2) * var_hat / N + var_rect / n
    se = math.sqrt(max(var, 0.0))
    z = z_value(alpha)
    var_cl = (float(np.var(yl, ddof=1)) if n > 1 else 0.0) / n
    se_cl = math.sqrt(var_cl)
    se_nv = math.sqrt(var_hat / N)
    return {
        "theta_pp": theta,
        "se": se,
        "ci": [theta - z * se, theta + z * se],
        "lambda": lam,
        "n_labelled": n,
        "N_machine": N,
        "classical_human_only": {
            "estimate": float(yl.mean()),
            "se": se_cl,
            "ci": [float(yl.mean()) - z * se_cl, float(yl.mean()) + z * se_cl],
        },
        "naive_machine_only": {
            "estimate": float(yh.mean()),
            "se": se_nv,
            "ci": [float(yh.mean()) - z * se_nv, float(yh.mean()) + z * se_nv],
        },
        "variance_ratio_vs_classical": (var / var_cl) if var_cl > 0 else None,
    }


# =====================================================================
# blocos por eixo
# =====================================================================


def _sub(seq, idx):
    return seq if idx is None else [seq[i] for i in idx]


def conf_dict(a, b, categories):
    M = confusion(a, b, categories)
    return {
        ca: {cb: int(M[i, j]) for j, cb in enumerate(categories)}
        for i, ca in enumerate(categories)
    }


def nominal_block(a, b, categories, B, seed):
    """κ, PABAK(k = |categorias|), AC1, α nominal, concordância bruta,
    prevalência e matriz de confusão para um eixo nominal."""
    K = len(categories)
    n_pairs = sum(1 for x, y in zip(a, b) if x is not None and y is not None)

    def stats(idx=None):
        aa, bb = _sub(a, idx), _sub(b, idx)
        po = raw_agreement(aa, bb)
        return {
            "raw_agreement": po,
            "kappa": cohen_kappa(aa, bb, categories),
            "pabak": pabak(po, K),
            "gwet_ac1": gwet_ac1(aa, bb, categories),
            "alpha_nominal": krippendorff_alpha([aa, bb], "nominal", categories),
        }

    point = {k: _f(v) for k, v in stats().items()}
    return {
        "n_pairs": n_pairs,
        "k_categories": K,
        "point": point,
        "ci95": bootstrap_block(stats, len(a), B, seed),
        "prevalence": prevalence(a, b, categories),
        "confusion": conf_dict(a, b, categories),
    }


def depth_block(a, b, B, seed):
    """Eixo ordinal: α ordinal (primário), α intervalar e nominal, κ quadrático,
    linear e sem peso, concordância exata e a ±1 posto, matriz 5×5."""
    n_pairs = sum(1 for x, y in zip(a, b) if x is not None and y is not None)
    one_sided = sum(1 for x, y in zip(a, b) if (x is None) != (y is None))

    def stats(idx=None):
        aa, bb = _sub(a, idx), _sub(b, idx)
        return {
            "alpha_ordinal": krippendorff_alpha([aa, bb], "ordinal", DEPTH),
            "alpha_interval": krippendorff_alpha([aa, bb], "interval", DEPTH),
            "alpha_nominal": krippendorff_alpha([aa, bb], "nominal", DEPTH),
            "kappa_quadratic": cohen_kappa(aa, bb, DEPTH, "quadratic"),
            "kappa_linear": cohen_kappa(aa, bb, DEPTH, "linear"),
            "kappa_unweighted": cohen_kappa(aa, bb, DEPTH),
            "exact_agreement": raw_agreement(aa, bb),
            "within_one_agreement": within_one(aa, bb, DEPTH),
        }

    point = {k: _f(v) for k, v in stats().items()}
    return {
        "n_pairs": n_pairs,
        "n_depth_null_one_side": one_sided,
        "ranks": {d: i + 1 for i, d in enumerate(DEPTH)},
        "point": point,
        "ci95": bootstrap_block(stats, len(a), B, seed),
        "prevalence": prevalence(a, b, DEPTH),
        "confusion": conf_dict(a, b, DEPTH),
    }


def jaccard_block(A, Bsets, B, seed):
    n_pairs = sum(1 for x, y in zip(A, Bsets) if x is not None and y is not None)

    def stats(idx=None):
        return {"jaccard_mean": jaccard_sets(_sub(A, idx), _sub(Bsets, idx))}

    return {
        "n_pairs": n_pairs,
        "point": {k: _f(v) for k, v in stats().items()},
        "ci95": bootstrap_block(stats, len(A), B, seed),
    }


def _get(labels, iid, field):
    rec = labels.get(iid)
    return None if rec is None else rec.get(field)


def _series(labels, items, field):
    return [_get(labels, i, field) for i in items]


def _binary(labels, items, fn):
    out = []
    for i in items:
        rec = labels.get(i)
        out.append(None if rec is None else ("yes" if fn(rec) else "no"))
    return out


def pair_analysis(la, lb, items, B, seed):
    """Relatório por eixo para um par de codificadores sobre `items`."""
    res = {
        "n_items": len(items),
        "n_coded_both": sum(1 for i in items if i in la and i in lb),
    }
    res["presence"] = nominal_block(
        _series(la, items, "presence"),
        _series(lb, items, "presence"),
        PRESENCE,
        B,
        seed,
    )
    res["presence"]["note"] = (
        "primário = concordância bruta; itens sem passagem têm presence fixado pela construção do pacote"
    )
    res["depth"] = depth_block(
        _series(la, items, "depth"), _series(lb, items, "depth"), B, seed
    )
    res["depth_substantive"] = nominal_block(
        _binary(la, items, lambda r: r.get("depth") in SUBSTANTIVE),
        _binary(lb, items, lambda r: r.get("depth") in SUBSTANTIVE),
        BINARY,
        B,
        seed,
    )
    res["depth_substantive"]["note"] = (
        "yes = supporting|foundational; depth null conta como no"
    )
    res["stance"] = nominal_block(
        _series(la, items, "stance"), _series(lb, items, "stance"), STANCE, B, seed
    )
    res["accuracy"] = nominal_block(
        _series(la, items, "accuracy"),
        _series(lb, items, "accuracy"),
        ACCURACY,
        B,
        seed,
    )
    res["accuracy_misrepresented"] = nominal_block(
        _binary(la, items, lambda r: r.get("accuracy") == "misrepresented"),
        _binary(lb, items, lambda r: r.get("accuracy") == "misrepresented"),
        BINARY,
        B,
        seed,
    )
    res["accuracy_not_accurate"] = nominal_block(
        _binary(
            la, items, lambda r: r.get("accuracy") in ("imprecise", "misrepresented")
        ),
        _binary(
            lb, items, lambda r: r.get("accuracy") in ("imprecise", "misrepresented")
        ),
        BINARY,
        B,
        seed,
    )
    reuse = {"per_tag": {}}
    for tag in REUSE:
        a = _binary(la, items, lambda r, t=tag: t in (r.get("reuse") or []))
        b = _binary(lb, items, lambda r, t=tag: t in (r.get("reuse") or []))
        if "yes" in a or "yes" in b:
            reuse["per_tag"][tag] = nominal_block(a, b, BINARY, B, seed)
        else:
            reuse["per_tag"][tag] = {
                "n_pairs": 0,
                "note": "nenhum codificador usou a tag",
            }
    reuse["any_reuse"] = nominal_block(
        _binary(la, items, lambda r: bool(r.get("reuse"))),
        _binary(lb, items, lambda r: bool(r.get("reuse"))),
        BINARY,
        B,
        seed,
    )
    reuse["jaccard"] = jaccard_block(
        _series(la, items, "reuse"), _series(lb, items, "reuse"), B, seed
    )
    res["reuse"] = reuse
    res["claim_ids"] = {
        "jaccard": jaccard_block(
            _series(la, items, "claim_ids"), _series(lb, items, "claim_ids"), B, seed
        )
    }
    # distortion: só onde os dois disseram accuracy != accurate
    both = [
        i
        for i in items
        if _get(la, i, "accuracy") in ("imprecise", "misrepresented")
        and _get(lb, i, "accuracy") in ("imprecise", "misrepresented")
    ]
    da, db = _series(la, both, "distortion"), _series(lb, both, "distortion")
    res["distortion"] = {
        "n_pairs_both_not_accurate": len(both),
        "raw_agreement": _f(raw_agreement(da, db)),
        "kappa": _f(cohen_kappa(da, db, DISTORTION)),
        "confusion": conf_dict(da, db, DISTORTION),
    }
    return res


def multi_alpha(labels, names, items):
    out = {"coders": list(names), "n_items": len(items)}
    for axis, cats, metric in (
        ("presence", PRESENCE, "nominal"),
        ("depth", DEPTH, "ordinal"),
        ("stance", STANCE, "nominal"),
        ("accuracy", ACCURACY, "nominal"),
    ):
        data = [_series(labels[n], items, axis) for n in names]
        out[axis] = {
            "metric": metric,
            "alpha": _f(krippendorff_alpha(data, metric, cats)),
        }
    return out


def intra_rater(labels, dup_pairs):
    rows = [(labels[o], labels[d]) for o, d in dup_pairs if o in labels and d in labels]
    n = len(rows)
    out = {"n_pairs": n, "n_pairs_in_key": len(dup_pairs)}
    for f in ("presence", "depth", "stance", "accuracy", "distortion"):
        out[f"{f}_agreement"] = (
            _f(np.mean([x.get(f) == y.get(f) for x, y in rows])) if n else None
        )
    out["reuse_jaccard"] = (
        _f(
            jaccard_sets(
                [x.get("reuse") for x, _ in rows], [y.get("reuse") for _, y in rows]
            )
        )
        if n
        else None
    )
    out["claim_ids_jaccard"] = (
        _f(
            jaccard_sets(
                [x.get("claim_ids") for x, _ in rows],
                [y.get("claim_ids") for _, y in rows],
            )
        )
        if n
        else None
    )
    out["all_axes_identical"] = (
        int(
            sum(
                all(
                    x.get(f) == y.get(f)
                    for f in ("presence", "depth", "stance", "accuracy", "distortion")
                )
                and set(x.get("reuse") or []) == set(y.get("reuse") or [])
                for x, y in rows
            )
        )
        if n
        else None
    )
    return out


PPI_INDICATORS = {
    "depth_substantive": lambda r: r.get("depth") in SUBSTANTIVE,
    "depth_drive_by": lambda r: r.get("depth") == "drive_by",
    "accuracy_misrepresented": lambda r: r.get("accuracy") == "misrepresented",
    "accuracy_not_accurate": lambda r: (
        r.get("accuracy") in ("imprecise", "misrepresented")
    ),
    "stance_contradictory": lambda r: r.get("stance") == "contradictory",
    "reuse_method_adoption": lambda r: "method_adoption" in (r.get("reuse") or []),
    "reuse_any": lambda r: bool(r.get("reuse")),
    "presence_reference_list_only": lambda r: (
        r.get("presence") == "reference_list_only"
    ),
}


def ppi_section(machine, human, items, alpha=0.05):
    all_items = [i for i in items if i in machine]
    labelled = [i for i in all_items if i in human]
    out = {
        "N_machine": len(all_items),
        "n_labelled": len(labelled),
        "alpha": alpha,
        "indicators": {},
    }
    for name, fn in PPI_INDICATORS.items():
        f_all = [float(fn(machine[i])) for i in all_items]
        f_hat_lab = [float(fn(machine[i])) for i in labelled]
        f_lab = [float(fn(human[i])) for i in labelled]
        out["indicators"][name] = {
            "ppi_plus_plus": ppi_mean(f_all, f_hat_lab, f_lab, alpha, tune=True),
            "ppi_classic": ppi_mean(f_all, f_hat_lab, f_lab, alpha, tune=False),
        }
    return out


# =====================================================================
# E/S e validação
# =====================================================================


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, **JSON_KW)
        f.write("\n")


def load_coder(path, lenient=False):
    """Lê {item_id: rótulos}; valida vocabulário e coerência de nulos.
    Violação de vocabulário aborta (ou vira ausente com --lenient);
    incoerência de nulos é só aviso."""
    raw = load_json(path)
    if not isinstance(raw, dict):
        raise SystemExit(f"{path}: esperado objeto {{item_id: rótulos}}")
    out, vocab_errs, warns = {}, [], []
    for iid, rec in raw.items():
        if not isinstance(rec, dict):
            vocab_errs.append(f"{iid}: valor não é objeto")
            continue
        r = {}
        for field, vocab in (
            ("presence", PRESENCE),
            ("depth", DEPTH),
            ("stance", STANCE),
            ("accuracy", ACCURACY),
            ("distortion", DISTORTION),
        ):
            v = rec.get(field)
            if v is not None and v not in vocab:
                vocab_errs.append(f"{iid}.{field}={v!r} fora do vocabulário")
                v = None
            r[field] = v
        for field, vocab in (("reuse", REUSE), ("claim_ids", None)):
            v = rec.get(field)
            v = [] if v is None else v
            if not isinstance(v, list):
                vocab_errs.append(f"{iid}.{field} não é lista")
                v = []
            if vocab is not None:
                bad = [t for t in v if t not in vocab]
                if bad:
                    vocab_errs.append(f"{iid}.{field} contém {bad} fora do vocabulário")
                    v = [t for t in v if t in vocab]
            r[field] = sorted(set(v))
        if r["presence"] != "in_text":
            for f in ("depth", "accuracy", "distortion"):
                if r[f] is not None:
                    warns.append(
                        f"{iid}.{f}={r[f]!r} com presence={r['presence']!r} (deveria ser null)"
                    )
        if r["accuracy"] in (None, "accurate") and r["distortion"] is not None:
            warns.append(
                f"{iid}.distortion={r['distortion']!r} com accuracy={r['accuracy']!r} (deveria ser null)"
            )
        if r["accuracy"] in ("imprecise", "misrepresented") and r["distortion"] is None:
            warns.append(f"{iid}.distortion ausente com accuracy={r['accuracy']!r}")
        out[iid] = r
    if vocab_errs and not lenient:
        raise SystemExit(
            f"{path}: {len(vocab_errs)} violações de vocabulário (use --lenient para tratá-las como ausentes):\n  "
            + "\n  ".join(vocab_errs[:20])
        )
    return out, {"vocabulary": vocab_errs, "null_coherence": warns}


# =====================================================================
# selftest
# =====================================================================

# Krippendorff (2011), "Computing Krippendorff's Alpha-Reliability": 4
# observadores, 12 unidades, valores 1–5, com ausentes. Publicado:
# α_nominal = 0,743; α_interval = 0,849; α_ordinal = 0,815.
KRIPP_2011 = [
    [1, 2, 3, 3, 2, 1, 4, 1, 2, None, None, None],
    [1, 2, 3, 3, 2, 2, 4, 1, 2, 5, None, 3],
    [None, 3, 3, 3, 2, 3, 4, 2, 2, 5, 1, None],
    [1, 2, 3, 3, 2, 4, 4, 1, 2, 5, 1, None],
]


def selftest(root, B=100, seed=20260904):
    results = []

    def check(name, ok, detail=""):
        results.append((name, bool(ok), detail))
        print(f"  [{'PASS' if ok else 'FALHA'}] {name} {detail}")

    print("== Selftest audit_62_irr_stats")
    cats = [1, 2, 3, 4, 5]
    a_nom = krippendorff_alpha(KRIPP_2011, "nominal", cats)
    a_int = krippendorff_alpha(KRIPP_2011, "interval", cats)
    a_ord = krippendorff_alpha(KRIPP_2011, "ordinal", cats)
    check(
        "(a) Krippendorff 2011, α nominal = 0,743",
        abs(a_nom - 0.743) < 5e-4,
        f"obtido {a_nom:.4f}",
    )
    check(
        "(a) Krippendorff 2011, α intervalar = 0,849",
        abs(a_int - 0.849) < 5e-4,
        f"obtido {a_int:.4f}",
    )
    d_ord = krippendorff_alpha_direct(KRIPP_2011, "ordinal", cats)
    check(
        "(a) α ordinal: matriz de coincidências == definição direta",
        abs(a_ord - d_ord) < 1e-12,
        f"obtido {a_ord:.4f} (publicado 0,815)",
    )
    check(
        "(a) α ordinal ≈ 0,815 (Krippendorff 2011)",
        abs(a_ord - 0.815) < 5e-4,
        f"obtido {a_ord:.4f}",
    )
    # validação cruzada em dados aleatórios com ausentes, 3 codificadores
    rng = np.random.default_rng(seed)
    ok_all = True
    for _ in range(20):
        data = [
            [
                (None if rng.random() < 0.2 else int(rng.integers(0, 4)))
                for _ in range(30)
            ]
            for _ in range(3)
        ]
        for metric in ("nominal", "ordinal", "interval"):
            x, y = (
                krippendorff_alpha(data, metric, [0, 1, 2, 3]),
                krippendorff_alpha_direct(data, metric, [0, 1, 2, 3]),
            )
            if not (_isnan(x) and _isnan(y)) and abs(x - y) > 1e-9:
                ok_all = False
    check(
        "(a) validação cruzada aleatória (3 codificadores, 20% ausentes, 3 métricas)",
        ok_all,
    )
    # (b) κ 2×2 de livro-texto: [[20,5],[10,15]] -> p_o = 0,70, p_e = 0,50, κ = 0,40
    a = ["y"] * 25 + ["n"] * 25
    b = ["y"] * 20 + ["n"] * 5 + ["y"] * 10 + ["n"] * 15
    k = cohen_kappa(a, b, ["n", "y"])
    check(
        "(b) κ de Cohen 2×2 [[20,5],[10,15]] = 0,40",
        abs(k - 0.4) < 1e-12,
        f"obtido {k:.4f}",
    )
    k_lin, k_quad = (
        cohen_kappa(a, b, ["n", "y"], "linear"),
        cohen_kappa(a, b, ["n", "y"], "quadratic"),
    )
    check(
        "(b) com 2 categorias κ sem peso == linear == quadrático",
        abs(k - k_lin) < 1e-12 and abs(k - k_quad) < 1e-12,
    )
    # (c) PABAK: identidade 2·p_o − 1 e igualdade com κ sob marginais uniformes [[40,10],[10,40]]
    a = ["y"] * 50 + ["n"] * 50
    b = ["y"] * 40 + ["n"] * 10 + ["y"] * 10 + ["n"] * 40
    po = raw_agreement(a, b)
    pb = pabak(po, 2)
    kk = cohen_kappa(a, b, ["n", "y"])
    check(
        "(c) PABAK = 2·p_o − 1 = 0,60",
        abs(pb - 0.6) < 1e-12,
        f"p_o={po:.2f} PABAK={pb:.4f}",
    )
    check("(c) PABAK == κ sob marginais uniformes", abs(pb - kk) < 1e-12, f"κ={kk:.4f}")
    ac1 = gwet_ac1(a, b, ["n", "y"])
    check(
        "(c) AC1 de Gwet == κ == PABAK nesse caso (π = 0,5)",
        abs(ac1 - 0.6) < 1e-12,
        f"AC1={ac1:.4f}",
    )
    # (d) PPI: n == N e f(Ŷ) == f(Y) -> θ̂_PP = média amostral (λ = 1 e λ ajustado)
    y = [float(v) for v in rng.integers(0, 2, 40)]
    for tune in (False, True):
        r = ppi_mean(y, y, y, tune=tune)
        check(
            f"(d) PPI n == N, f(Ŷ) == f(Y), tune={tune}: θ̂_PP == média",
            abs(r["theta_pp"] - float(np.mean(y))) < 1e-12,
            f"θ̂={r['theta_pp']:.4f} média={np.mean(y):.4f} λ={r['lambda']:.3f}",
        )
    # (e) Jaccard e casos degenerados
    check(
        "(e) Jaccard [{a,b},{}] vs [{a},{}] = média(0,5; 1) = 0,75",
        abs(jaccard_sets([["a", "b"], []], [["a"], []]) - 0.75) < 1e-12,
    )
    check(
        "(e) κ indefinido (NaN) quando só uma categoria aparece",
        _isnan(cohen_kappa(["a"] * 5, ["a"] * 5, ["a", "b"])),
    )
    check(
        "(e) α = 1 sob concordância perfeita com variação",
        abs(krippendorff_alpha([[1, 2, 3, 1], [1, 2, 3, 1]], "nominal") - 1.0) < 1e-12,
    )
    # (f) ponta a ponta: c1 contra si mesmo, se o pacote existe
    irr = root / "data" / "irr"
    c1p, keyp = irr / "irr_c1_from_v2.json", irr / "pack_key.json"
    if c1p.exists() and keyp.exists():
        c1, _ = load_coder(c1p)
        key = load_json(keyp)
        originals = sorted(i for i, k in key.items() if not k.get("duplicate_of"))
        primary = [i for i in originals if not key[i].get("codebook_exemplar")]
        res = pair_analysis(c1, c1, primary, B, seed)
        vals = []
        for axis in (
            "presence",
            "depth",
            "depth_substantive",
            "stance",
            "accuracy",
            "accuracy_misrepresented",
        ):
            for k, v in res[axis]["point"].items():
                if k.startswith(("kappa", "alpha")) or k in (
                    "raw_agreement",
                    "exact_agreement",
                ):
                    vals.append((axis, k, v))
        bad = [
            (ax, k, v) for ax, k, v in vals if v is not None and abs(v - 1.0) > 1e-12
        ]
        undefined = [(ax, k) for ax, k, v in vals if v is None]
        check(
            "(f) ponta a ponta c1 vs c1: todo α e κ definidos == 1,0",
            not bad,
            f"{len(vals) - len(undefined)} estatísticas == 1; indefinidas (categoria única): {undefined}",
        )
    else:
        print("  [----] (f) ponta a ponta: pacote ausente em data/irr, pulado")
    n_fail = sum(1 for _, ok, _ in results if not ok)
    print(f"== {len(results) - n_fail}/{len(results)} testes ok")
    return 1 if n_fail else 0


# =====================================================================
# CLI
# =====================================================================


def _fmt(x):
    return "  n/d" if x is None else f"{x:6.3f}"


def print_summary(result):
    for pair, blocks in result["pairs"].items():
        for scope in ("primary", "sensitivity_with_exemplars"):
            r = blocks[scope]
            print(
                f"== {pair} [{scope}] itens={r['n_items']} codificados por ambos={r['n_coded_both']}"
            )
            d = r["depth"]["point"]
            print(
                f"  depth       α_ord={_fmt(d['alpha_ordinal'])} κ_quad={_fmt(d['kappa_quadratic'])} "
                f"exato={_fmt(d['exact_agreement'])} ±1={_fmt(d['within_one_agreement'])} (n={r['depth']['n_pairs']})"
            )
            for axis in (
                "depth_substantive",
                "stance",
                "accuracy",
                "accuracy_misrepresented",
                "presence",
            ):
                p = r[axis]["point"]
                print(
                    f"  {axis:<26} κ={_fmt(p['kappa'])} PABAK={_fmt(p['pabak'])} AC1={_fmt(p['gwet_ac1'])} "
                    f"bruta={_fmt(p['raw_agreement'])} (n={r[axis]['n_pairs']})"
                )
            ma = r["reuse"]["per_tag"].get("method_adoption", {})
            if ma.get("point"):
                print(
                    f"  reuse:method_adoption      κ={_fmt(ma['point']['kappa'])} bruta={_fmt(ma['point']['raw_agreement'])}"
                )
            print(
                f"  reuse:jaccard              {_fmt(r['reuse']['jaccard']['point']['jaccard_mean'])}"
            )
    for name, ir in result["intra_rater"].items():
        print(
            f"== intra-codificador {name}: pares={ir['n_pairs']} idênticos em todos os eixos={ir['all_axes_identical']} "
            f"depth={_fmt(ir['depth_agreement'])} stance={_fmt(ir['stance_agreement'])} accuracy={_fmt(ir['accuracy_agreement'])}"
        )
    if result.get("multi_coder_alpha"):
        m = result["multi_coder_alpha"]
        print(
            "== α multi-codificador: "
            + ", ".join(
                f"{ax}={_fmt(m[ax]['alpha'])}"
                for ax in ("presence", "depth", "stance", "accuracy")
            )
        )
    if result.get("ppi"):
        p = result["ppi"]
        print(f"== PPI (N={p['N_machine']}, n={p['n_labelled']})")
        for name, ind in p["indicators"].items():
            pp = ind["ppi_plus_plus"]
            if pp:
                print(
                    f"  {name:<30} θ̂_PP={pp['theta_pp']:.3f} IC95=[{pp['ci'][0]:.3f}, {pp['ci'][1]:.3f}] λ={pp['lambda']:.2f} "
                    f"| humano-só {pp['classical_human_only']['estimate']:.3f} | máquina-só {pp['naive_machine_only']['estimate']:.3f}"
                )


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--c1")
    ap.add_argument("--c2")
    ap.add_argument("--c3")
    ap.add_argument("--human", help="rótulos humanos de um subconjunto (PPI)")
    ap.add_argument("--key")
    ap.add_argument("--out")
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20260904)
    ap.add_argument(
        "--lenient",
        action="store_true",
        help="valor fora do vocabulário vira ausente em vez de abortar",
    )
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    root = args.root.resolve()
    if args.selftest:
        return selftest(root)
    if not (args.c1 and args.c2 and args.key and args.out):
        ap.error("--c1, --c2, --key e --out são obrigatórios (ou --selftest)")

    key = load_json(args.key)
    originals = sorted(i for i, k in key.items() if not k.get("duplicate_of"))
    dup_pairs = sorted(
        (k["duplicate_of"], i) for i, k in key.items() if k.get("duplicate_of")
    )
    exemplars = sorted(i for i in originals if key[i].get("codebook_exemplar"))
    primary = [i for i in originals if i not in set(exemplars)]

    coders = {"c1": args.c1, "c2": args.c2}
    if args.c3:
        coders["c3"] = args.c3
    labels, problems, coverage = {}, {}, {}
    for name, path in coders.items():
        labels[name], problems[name] = load_coder(path, args.lenient)
        missing = [i for i in key if i not in labels[name]]
        unknown = [i for i in labels[name] if i not in key]
        coverage[name] = {
            "coded": len(labels[name]),
            "missing_from_pack": len(missing),
            "missing_ids": missing[:50],
            "unknown_ids": unknown[:50],
        }
        for kind, lst in problems[name].items():
            if lst:
                print(f"  aviso {name} ({kind}): {len(lst)} — ex.: {lst[0]}")

    result = {
        "meta": {
            "coders": coders,
            "key": args.key,
            "B": args.B,
            "seed": args.seed,
            "n_items_original": len(originals),
            "n_primary": len(primary),
            "n_exemplars_excluded": len(exemplars),
            "exemplar_ids": exemplars,
            "n_duplicate_pairs": len(dup_pairs),
            "coverage": coverage,
            "validation": {
                n: {k: len(v) for k, v in p.items()} for n, p in problems.items()
            },
            "notes": [
                "primary exclui itens codebook_exemplar; sensitivity_with_exemplars inclui",
                "PABAK usa k = nº de categorias do eixo (k = 2 nos eixos binários => 2·p_o − 1)",
                "depth: α ordinal é a estatística primária; κ quadrático como segunda leitura",
                "IC95 = bootstrap percentílico sobre itens",
            ],
        },
        "pairs": {},
        "multi_coder_alpha": None,
        "intra_rater": {},
        "ppi": None,
    }
    for na, nb in itertools.combinations(coders, 2):
        result["pairs"][f"{na}_vs_{nb}"] = {
            "primary": pair_analysis(
                labels[na], labels[nb], primary, args.B, args.seed
            ),
            "sensitivity_with_exemplars": pair_analysis(
                labels[na], labels[nb], originals, args.B, args.seed
            ),
        }
    if len(coders) >= 3:
        result["multi_coder_alpha"] = {
            "primary": multi_alpha(labels, list(coders), primary),
            "sensitivity_with_exemplars": multi_alpha(labels, list(coders), originals),
        }
    for name in coders:
        result["intra_rater"][name] = intra_rater(labels[name], dup_pairs)
    if args.human:
        human, hp = load_coder(args.human, args.lenient)
        result["ppi"] = ppi_section(labels["c1"], human, originals)
        result["ppi"]["human_file"] = args.human
        result["ppi"]["validation"] = {k: len(v) for k, v in hp.items()}
    dump_json(result, args.out)
    print_summary(result)
    print(f"== Gravado: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
