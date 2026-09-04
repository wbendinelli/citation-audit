#!/usr/bin/env python3
"""Etapa 68 (stage_e): compara as taxas medidas em `data/classify.json` (eixos
v2: presence/depth/stance/accuracy/reuse/relation/record_flags) contra taxas
publicadas na literatura de citation-function analysis, reunidas em
`docs/revisao-literatura.md`.

Denominadores (calculados a partir dos dados, nunca hard-coded):
  D_read = todas as entradas classificadas (104)
  D_text = presence == in_text
  D_ind  = in_text com relation == independent
  D_pop  = população METHOD.md §9 (DOI + editora estabelecida + artigo de
           periódico, sem capítulo/anais/preprint) interseção classificadas

Cada indicador é reportado numerador/denominador/taxa + IC95% de Wilson,
por artigo (airline/grains) e pooled, ao lado do número publicado
correspondente, sua fonte, e as ressalvas de comparabilidade e de
verificação que `docs/revisao-literatura.md` já documenta (§5–§6) --
nenhum número da literatura é usado sem checar se a própria revisão o
marcou como não verificado.

Raiz de INSUMOS (`--root`) vs. raiz de SAÍDA (auto-detectada por
`__file__`): mesmo esquema de `audit_67_ghost_audit.py` -- ver a docstring
de lá. Este script também lê `<auto-raiz>/data/ghost_audit.json`, escrito
por audit_67 na MESMA pasta de saída (não em `--root`): rode audit_67
primeiro.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

SELF_ROOT = Path(__file__).resolve().parents[1]
OUT_DATA = SELF_ROOT / "data"
STAGE_C_CLASSIFY_FALLBACK = SELF_ROOT.parent / "stage_c" / "data" / "classify.json"

_JSON_KW = {"ensure_ascii": False, "indent": 1, "sort_keys": True}


def dump_json(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, **_JSON_KW)
        f.write("\n")


def load_classify_v2(explicit_path, root):
    """Idêntico em intenção ao homônimo de audit_67_ghost_audit.py --
    duplicado deliberadamente (ver docstring do módulo lá: cada script
    fica autocontido para sobreviver a uma mudança de pasta sem levar um
    terceiro arquivo junto)."""
    was_explicit = explicit_path is not None
    path = (
        Path(explicit_path).resolve()
        if explicit_path
        else (root / "data" / "classify.json")
    )

    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    entries = (
        raw["entries"]
        if (isinstance(raw, dict) and "meta" in raw and "entries" in raw)
        else raw
    )

    is_v2 = any(("presence" in v) for v in entries.values())
    fallback_used = False
    warn = None
    if not is_v2 and not was_explicit:
        fallback_used = True
        warn = (
            f"AVISO: {path} ainda está no esquema v1 (role/flag); "
            f"usando fallback documentado {STAGE_C_CLASSIFY_FALLBACK}"
        )
        print(warn)
        with open(STAGE_C_CLASSIFY_FALLBACK, encoding="utf-8") as f:
            raw = json.load(f)
        entries = (
            raw["entries"]
            if (isinstance(raw, dict) and "meta" in raw and "entries" in raw)
            else raw
        )
        path = STAGE_C_CLASSIFY_FALLBACK
        is_v2 = any(("presence" in v) for v in entries.values())
        if not is_v2:
            raise SystemExit(
                f"ERRO: fallback {path} também não está em v2 (presence/depth/...)."
            )
    elif not is_v2 and was_explicit:
        raise SystemExit(
            f"ERRO: --classify {path} está em v1 (role/flag), passado explicitamente "
            f"-- sem fallback automático sobre escolha explícita."
        )
    return entries, {"path": str(path), "fallback_used": fallback_used, "warning": warn}


def is_book_doi(doi):
    suf = doi.split("/", 1)[1] if "/" in doi else ""
    return (
        suf.startswith("978")
        or "9781" in suf
        or "9780" in suf
        or doi.startswith("10.1007/978")
    )


def in_population_87(rec, editoras_estabelecidas):
    doi = rec.get("doi")
    if not doi:
        return False
    prefix = doi.split("/", 1)[0]
    if prefix not in editoras_estabelecidas:
        return False
    return not is_book_doi(doi)


def wilson_ci(k, n, z=1.959963984540054):
    if n == 0:
        return (0.0, 0.0)
    k = np.asarray(k, dtype=float)
    n = np.asarray(n, dtype=float)
    phat = k / n
    denom = 1.0 + z * z / n
    center = phat + z * z / (2 * n)
    margin = z * np.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))
    lo = round(float(max(0.0, (center - margin) / denom)), 6)
    hi = round(float(min(1.0, (center + margin) / denom)), 6)
    if lo < 1e-9:
        lo = 0.0
    if hi > 1 - 1e-9:
        hi = 1.0
    return (lo, hi)


def rate_block(k, n):
    lo, hi = wilson_ci(k, n)
    rate = round(k / n, 6) if n else None
    return {
        "numerator": int(k),
        "denominator": int(n),
        "rate": rate,
        "ci95_wilson": [lo, hi],
    }


PAPERS = ("airline", "grains")


def per_paper_and_pooled(dois_num, dois_den, doi_to_paper):
    """`dois_num`/`dois_den` são sets de DOI. Devolve {"pooled":..., "airline":..., "grains":...}
    com rate_block em cada, restringindo por artigo via doi_to_paper.

    Interseta `dois_num` com `dois_den` ANTES de contar. Para a maioria das
    linhas isto é redundante por construção (o numerador já nasce como
    subconjunto do denominador, ex. misrep_dois ⊆ D_text). Mas para as
    linhas de fantasma (audit_67) `genuine_dois` vem das 13 candidatas
    inteiras, não pré-filtrado por D_body/D_pop -- sem a interseção aqui,
    ghost_D_pop contava grains_061 (genuine, mas FORA da população 87) no
    numerador de uma taxa cujo denominador é só a população, inflando 0/7
    para 1/7. Bug real, pego rodando o script e comparando com o resumo
    que audit_67_ghost_audit.py já imprime para o mesmo denominador."""
    dois_num = set(dois_num) & set(dois_den)
    dois_den = set(dois_den)
    out = {"pooled": rate_block(len(dois_num), len(dois_den))}
    for p in PAPERS:
        den_p = {d for d in dois_den if doi_to_paper.get(d) == p}
        num_p = {d for d in dois_num if doi_to_paper.get(d) == p}
        out[p] = rate_block(len(num_p), len(den_p))
    return out


# =======================================================================
# Publicados: cada bloco carrega o texto exatamente como aparece em
# docs/revisao-literatura.md §5 (números) e §6 (flags de não verificado),
# checado linha a linha antes de escrever este script.
# =======================================================================
PENDENTE = {"verification_status": "pendente", "verificado_em": None}


def pub(
    value, source, field, n_published=None, comparability_note="", review_flag=None
):
    d = {
        "published": value,
        "source": source,
        "field": field,
        "n_published": n_published,
        "comparability_note": comparability_note,
        "review_flag": review_flag,
    }
    d.update(PENDENTE)
    return d


PUB_GHOST = pub(
    "1.4%",
    "Boyack, van Eck, Colavizza & Waltman (2018), Journal of Informetrics 12(1), 59-73 "
    "(DOI 10.1016/j.joi.2017.11.005)",
    "multidisciplinar (corpus PMC-OA + Elsevier de texto completo)",
    n_published="~5 milhões de artigos de texto completo (subconjunto Elsevier citado aqui)",
    comparability_note=(
        "descompasso de unidade: Boyack mede % de REFERÊNCIAS não mencionadas no corpo, sobre XML "
        "estruturado do publisher com casamento referência<->marcador confiável; aqui o numerador é "
        "'genuine' (presence==reference_list_only sobrevivendo à decomposição de audit_67) sobre "
        "entradas classificadas (D_read), sobre o subconjunto com corpo real comprovado em disco "
        "(D_body), ou sobre a população METHOD.md (D_pop) -- populações e método de deteção "
        "diferentes. docs/revisao-literatura.md nota que nossa taxa bruta 13/104=12,5% é ~9x a "
        "de Boyack e recomenda reportar separadamente genuine/extraction_failure/body_unavailable "
        "antes de comparar -- exatamente o que audit_67_ghost_audit.py faz."
    ),
    review_flag=(
        "não verificado: número vem de um único trecho de busca, não do texto completo do "
        "preprint arXiv:1710.03094; também checar se referências não casadas foram excluídas "
        "a montante em vez de contadas."
    ),
)

PUB_MISREP_MAJOR = pub(
    "sem equivalente direto de 'erro maior' isolado na literatura consultada",
    "Jergas & Baethge (2015), PeerJ 3:e1364; PMC8386904 (2021, ortopedia)",
    "medicina / ortopedia e medicina esportiva",
    n_published=None,
    comparability_note=(
        "nosso 'misrepresented' é a categoria MAIOR (leitura substancialmente errada do que o "
        "artigo diz); estudos de erro de citação em geral contam qualquer proposição não "
        "sustentada, incluindo erros menores (Jergas & Baethge: total 25,4%, dos quais 8,5% "
        "'minor' isolado -- a fração 'major' não é dada e NÃO deve ser inferida por subtração, "
        "por instrução explícita da revisão). O comparador mais direto para a categoria maior "
        "isolada é o 'completamente infundada' de PMC8386904 (2021): 2,8%."
    ),
    review_flag="taxa de erro maior de Jergas & Baethge não confirmada -- só total 25,4% e menor 8,5% o são; não inferir por subtração (ver docs/revisao-literatura.md §6).",
)

PUB_MISREP_TOTAL = pub(
    "25.4% (Jergas & Baethge); 13.1-20.4% (Wakeling et al., implícito 16.6%); 13.6% (ortopedia, PMC8386904)",
    "Jergas & Baethge (2015) PeerJ 3:e1364; Wakeling et al. (2025) JASIST; PMC8386904 (2021)",
    "medicina (meta-análise 28 estudos); survey multidisciplinar (2648 respostas); ortopedia/medicina esportiva",
    n_published=2648,
    comparability_note=(
        "análogo ao 'total' de Jergas & Baethge: aqui somamos accuracy in {misrepresented, "
        "imprecise} sobre D_text, o mais próximo do critério 'qualquer proposição não "
        "sustentada' usado nesses estudos. Wakeling et al. é o único que pergunta aos PRÓPRIOS "
        "autores como creem que sua obra é citada -- comparador mais direto se o interesse é a "
        "perspectiva do autor citado, que é exatamente o desenho deste estudo."
    ),
    review_flag=None,
)

PUB_CONTRA = pub(
    "2.40% (2.44% na subamostra)",
    "Catalini, Lacetera & Oettl (2015), PNAS 112(45), 13823-13826 (DOI 10.1073/pnas.1502280112); "
    "comparável a Athar (2011), ACL 2011 Student Session, ~2.8% negativo",
    "imunologia (Catalini et al.); PLN/ciência da computação, corpus ACL (Athar)",
    n_published=15000,
    comparability_note=(
        "'contradictory' aqui usa a regra deliberadamente liberal do codebook (METHOD.md §6): "
        "qualquer contraponto conta, mesmo sem linguagem hostil e mesmo quando o citante também "
        "usa o artigo como baseline -- provavelmente mais inclusiva que o critério de Catalini "
        "et al. (incapacidade de replicar, discordância ou inconsistência com resultado/teoria "
        "prévios)."
    ),
    review_flag=None,
)

PUB_PERFUNCTORY = pub(
    "41%",
    "Moravcsik & Murugesan (1975), Social Studies of Science 5(1), 86-92 (DOI 10.1177/030631277500500106)",
    "sociologia da ciência / ciência da ciência",
    n_published=None,
    comparability_note=(
        "'perfunctory' de Moravcsik é a citação em bloco/afirmação genérica que qualquer fonte "
        "da área sustentaria -- mapeamento direto para drive_by + brief_mention no codebook "
        "(ver crosswalk em data/taxonomy_v2.json). docs/revisao-literatura.md também lista SciCite "
        "58% background e Teufel >60% Neut como comparadores adicionais para este nível; se a "
        "taxa medida cair entre 40-60%, está alinhada à literatura."
    ),
    review_flag=(
        "verificado só via fontes secundárias (Teufel et al. 2006 e a literatura de citation-"
        "function); o original de 1975 é pago e não foi lido diretamente (ver docs/revisao-"
        "literatura.md §6)."
    ),
)

PUB_IMPORTANT = pub(
    "14.6%",
    "Valenzuela, Ha & Etzioni (2015), AAAI-15 Workshop on Scholarly Big Data",
    "ciência da computação (Semantic Scholar / AAAI)",
    n_published=465,
    comparability_note=(
        "'important' de Valenzuela é binário (important/incidental), com a regra uses/extends="
        "important e related-work/comparison=incidental -- mapeamento razoável para "
        "supporting+foundational no nosso eixo ordinal depth."
    ),
    review_flag=(
        "o valor 14,6% e o n=465 pares estão confirmados; só os RÓTULOS dos quatro níveis "
        "ordinais de importância não estão confirmados (ver docs/revisao-literatura.md §6)."
    ),
)

PUB_BACKGROUND = pub(
    "58% (SciCite, Background); >60% (Teufel 2006, Neut)",
    "Cohan et al. (2019) SciCite (11.020 instâncias); Teufel, Siddharthan & Tidhar (2006), Proc. 7th SIGdial",
    "ciência da computação + medicina (SciCite, corpus Semantic Scholar); PLN (Teufel, anotação de função de citação)",
    n_published=11020,
    comparability_note=(
        "construção composta local (drive_by+brief_mention+real_mention sem reuso) não tem "
        "equivalente de rótulo único: SciCite e Teufel são esquemas de rótulo ÚNICO por citação, "
        "enquanto aqui depth e reuse são eixos ortogonais -- a comparação é aproximada, não uma "
        "identidade de definição."
    ),
    review_flag=(
        "SciCite: tamanho (11.020) e distribuição 58/29/13% vêm de fonte secundária, não "
        "verificados diretamente. Teufel: tamanho do corpus além de '116 documentos' e a cifra "
        "'2.829 citações' não confirmados; kappa=0,72 e '>60% Neut' vêm de fontes secundárias; "
        "o PDF original retornou binário na tentativa de extração (ver docs/revisao-literatura.md §6)."
    ),
)

PUB_REUSE = pub(
    None,
    None,
    None,
    n_published=None,
    comparability_note="sem comparador publicado localizado para taxa de reuso metodológico efetivo sobre citações independentes.",
    review_flag=None,
)

PUB_SELF = pub(
    None,
    "Bornmann & Leibel (2025/2026), arXiv:2508.12735 (também em MetaROR)",
    "metaciência / bibliometria",
    n_published=None,
    comparability_note=(
        "sem comparador numérico publicado para a fração de autocitação/citação de coautor. "
        "Bornmann & Leibel dão o VOCABULÁRIO conceitual (accuracy/bias/noise) em que "
        "autocitação e duplicata se encaixam na célula de 'citation bias' (distorção "
        "direcional sistemática) -- não um número a comparar."
    ),
    review_flag=None,
)

PUB_DUPLICATE = pub(
    None,
    "Bornmann & Leibel (2025/2026), arXiv:2508.12735 (também em MetaROR)",
    "metaciência / bibliometria",
    n_published=None,
    comparability_note="sem comparador publicado; mesmo enquadramento conceitual de 'citation bias' que a linha self/coauthor.",
    review_flag=None,
)


def main():
    ap = argparse.ArgumentParser(
        description="Compara taxas medidas em classify.json contra taxas publicadas da literatura de citation-function analysis."
    )
    ap.add_argument(
        "--root",
        type=str,
        default=None,
        help="raiz do repositório citation-audit (default: inferida de __file__)",
    )
    ap.add_argument(
        "--classify",
        type=str,
        default=None,
        help="caminho para classify.json (default: <root>/data/classify.json, com fallback documentado)",
    )
    args = ap.parse_args()

    root = Path(args.root).resolve() if args.root else SELF_ROOT
    sys.path.insert(0, str(root / "tools"))
    import auditlib

    cfg = auditlib.load_config()
    master = auditlib.load_master()
    editoras_estabelecidas = cfg["editoras_estabelecidas"]
    entries, classify_meta = load_classify_v2(args.classify, root)

    ghost_audit_path = OUT_DATA / "ghost_audit.json"
    if not ghost_audit_path.exists():
        raise SystemExit(
            f"ERRO: {ghost_audit_path} não existe. Rode audit_67_ghost_audit.py primeiro "
            f"(este script lê o resultado dele para a linha de taxa-fantasma)."
        )
    with open(ghost_audit_path, encoding="utf-8") as f:
        ghost_audit = json.load(f)
    ghost_entries = ghost_audit["entries"]

    # mapa doi -> paper, e doi -> registro (para D_pop)
    doi_to_paper = {}
    doi_to_rec = {}
    for key, block in master["papers"].items():
        for r in block["citing"]:
            d = (r.get("doi") or "").lower()
            if d:
                doi_to_paper[d] = key
                doi_to_rec[d] = r

    missing_paper = [d for d in entries if d not in doi_to_paper]
    if missing_paper:
        print(
            f"AVISO: {len(missing_paper)} DOI(s) de classify.json não resolvem a nenhum registro de master.json: {missing_paper}"
        )

    all_dois = set(entries.keys())

    def is_in_text(doi):
        return entries[doi].get("presence") == "in_text"

    def is_independent(doi):
        return entries[doi].get("relation") == "independent"

    def is_in_pop(doi):
        rec = doi_to_rec.get(doi)
        return bool(rec) and in_population_87(rec, editoras_estabelecidas)

    D_read = all_dois
    D_text = {d for d in all_dois if is_in_text(d)}
    D_ind = {d for d in D_text if is_independent(d)}
    D_pop = {d for d in all_dois if is_in_pop(d)}

    # contagens-base impressas para reconciliação direta com o arquivo de classificação
    base_counts = {
        "D_read": len(D_read),
        "D_text": len(D_text),
        "D_ind": len(D_ind),
        "D_pop": len(D_pop),
    }

    rows = []

    # -------------------- 1-3: fantasma (lidos de ghost_audit.json) --------------------
    ghost_dois_all = set(ghost_entries.keys())
    genuine_dois = {
        d for d in ghost_dois_all if ghost_entries[d]["category"] == "genuine"
    }
    body_real_dois = {d for d in ghost_dois_all if ghost_entries[d]["body_is_real"]}
    ghost_pop_dois = {d for d in ghost_dois_all if ghost_entries[d]["in_population_87"]}

    for label, den_set, extra_note in (
        ("ghost_D_read", D_read, "D_read = todas as 104 classificadas."),
        (
            "ghost_D_body",
            body_real_dois,
            "D_body = só as 13 reference_list_only com corpo real comprovado em disco (ver audit_67_ghost_audit.py); n pequeno, IC largo por desenho.",
        ),
        (
            "ghost_D_pop",
            ghost_pop_dois,
            (
                "D_pop aqui É A INTERSEÇÃO ESPECÍFICA 'população 87 ∩ os 13 fantasma candidatos' (7 entradas), NÃO o D_pop geral "
                f"deste script (população ∩ todas as 104 = {len(D_pop)}). Terceira linha de taxa-fantasma acrescentada por "
                "decisão do agente: a tarefa definiu D_pop como denominador disponível mas não o atribuiu explicitamente a "
                "nenhuma linha da lista de indicadores -- replicar aqui o terceiro denominador que audit_67 já calcula "
                "pareceu a leitura mais defensável, em vez de deixar D_pop sem uso. Ver relatório final do agente."
            ),
        ),
    ):
        rows.append(
            {
                "indicator": label,
                "description": "citação 'fantasma' (só na lista de referências) -- numerador = categoria 'genuine' de audit_67_ghost_audit.py.",
                "denominator_label": label.split("_", 1)[1],
                "denominator_note": extra_note,
                "results": per_paper_and_pooled(genuine_dois, den_set, doi_to_paper),
                **PUB_GHOST,
            }
        )

    # -------------------- 4-5: misrepresented --------------------
    misrep_dois = {d for d in D_text if entries[d].get("accuracy") == "misrepresented"}
    rows.append(
        {
            "indicator": "misrepresented_major",
            "description": "accuracy == misrepresented (categoria MAIOR de erro de citação) sobre D_text.",
            "denominator_label": "D_text",
            "results": per_paper_and_pooled(misrep_dois, D_text, doi_to_paper),
            **PUB_MISREP_MAJOR,
        }
    )
    misrep_or_imprecise_dois = {
        d
        for d in D_text
        if entries[d].get("accuracy") in ("misrepresented", "imprecise")
    }
    rows.append(
        {
            "indicator": "misrepresented_plus_imprecise_total",
            "description": "accuracy in {misrepresented, imprecise} sobre D_text -- análogo ao 'total' dos estudos de erro de citação.",
            "denominator_label": "D_text",
            "results": per_paper_and_pooled(
                misrep_or_imprecise_dois, D_text, doi_to_paper
            ),
            **PUB_MISREP_TOTAL,
        }
    )

    # -------------------- 6: contradictory --------------------
    contra_dois = {d for d in D_text if entries[d].get("stance") == "contradictory"}
    rows.append(
        {
            "indicator": "contradictory",
            "description": "stance == contradictory sobre D_text.",
            "denominator_label": "D_text",
            "results": per_paper_and_pooled(contra_dois, D_text, doi_to_paper),
            **PUB_CONTRA,
        }
    )

    # -------------------- 7: perfunctory --------------------
    perfunctory_dois = {
        d for d in D_text if entries[d].get("depth") in ("drive_by", "brief_mention")
    }
    rows.append(
        {
            "indicator": "perfunctory",
            "description": "depth in {drive_by, brief_mention} sobre D_text.",
            "denominator_label": "D_text",
            "results": per_paper_and_pooled(perfunctory_dois, D_text, doi_to_paper),
            **PUB_PERFUNCTORY,
        }
    )

    # -------------------- 8: important --------------------
    important_dois = {
        d for d in D_text if entries[d].get("depth") in ("supporting", "foundational")
    }
    rows.append(
        {
            "indicator": "important",
            "description": "depth in {supporting, foundational} sobre D_text.",
            "denominator_label": "D_text",
            "results": per_paper_and_pooled(important_dois, D_text, doi_to_paper),
            **PUB_IMPORTANT,
        }
    )

    # -------------------- 9: background-like --------------------
    background_dois = {
        d
        for d in D_text
        if entries[d].get("depth") in ("drive_by", "brief_mention", "real_mention")
        and not (entries[d].get("reuse") or [])
    }
    rows.append(
        {
            "indicator": "background_like",
            "description": "depth in {drive_by, brief_mention, real_mention} E reuse vazio, sobre D_text.",
            "denominator_label": "D_text",
            "results": per_paper_and_pooled(background_dois, D_text, doi_to_paper),
            **PUB_BACKGROUND,
        }
    )

    # -------------------- 10: method reuse --------------------
    reuse_dois = {d for d in D_ind if (entries[d].get("reuse") or [])}
    rows.append(
        {
            "indicator": "method_reuse",
            "description": "qualquer tag de reuse não vazia, sobre D_ind (in_text E relation==independent).",
            "denominator_label": "D_ind",
            "results": per_paper_and_pooled(reuse_dois, D_ind, doi_to_paper),
            **PUB_REUSE,
        }
    )

    # -------------------- 11: self/coauthor --------------------
    self_coauthor_dois = {
        d for d in D_read if entries[d].get("relation") in ("self", "coauthor")
    }
    rows.append(
        {
            "indicator": "self_or_coauthor",
            "description": "relation in {self, coauthor} sobre D_read.",
            "denominator_label": "D_read",
            "results": per_paper_and_pooled(self_coauthor_dois, D_read, doi_to_paper),
            **PUB_SELF,
        }
    )

    # -------------------- 12: duplicate_publication --------------------
    duplicate_dois = {
        d
        for d in D_read
        if "duplicate_publication" in (entries[d].get("record_flags") or [])
    }
    rows.append(
        {
            "indicator": "duplicate_publication",
            "description": "'duplicate_publication' in record_flags, sobre D_read.",
            "denominator_label": "D_read",
            "results": per_paper_and_pooled(duplicate_dois, D_read, doi_to_paper),
            **PUB_DUPLICATE,
        }
    )

    # -------------------- reconciliação: contagens brutas direto da fonte --------------------
    reconciliation = {
        "n_classify_entries": len(all_dois),
        "n_in_text": len(D_text),
        "n_in_text_independent": len(D_ind),
        "n_population_87_intersect_classified": len(D_pop),
        "n_reference_list_only": len(ghost_dois_all),
        "n_ghost_genuine_per_audit_67": len(genuine_dois),
        "n_misrepresented": len(misrep_dois),
        "n_misrepresented_or_imprecise": len(misrep_or_imprecise_dois),
        "n_contradictory": len(contra_dois),
        "n_perfunctory_drive_by_or_brief_mention": len(perfunctory_dois),
        "n_important_supporting_or_foundational": len(important_dois),
        "n_background_like": len(background_dois),
        "n_method_reuse_any_tag": len(reuse_dois),
        "n_self_or_coauthor": len(self_coauthor_dois),
        "n_duplicate_publication": len(duplicate_dois),
    }

    out = {
        "meta": {
            "script": "audit_68_base_rates.py",
            "root_insumos": str(root),
            "classify_source": classify_meta,
            "ghost_audit_source": str(ghost_audit_path),
        },
        "denominators": base_counts,
        "rows": rows,
        "reconciliation_counts": reconciliation,
    }

    out_path = OUT_DATA / "base_rates.json"
    dump_json(out, out_path)

    # -------------------- tabela impressa --------------------
    print()
    print(f"base_rates.json escrito em {out_path}")
    print(
        f"classify usado: {classify_meta['path']} (fallback_used={classify_meta['fallback_used']})"
    )
    print()
    print("denominadores:", base_counts)
    print()
    hdr = f"{'indicador':38s} {'den':8s} {'pooled n/d':12s} {'taxa':8s} {'IC95% Wilson':20s} {'publicado':30s}"
    print(hdr)
    print("-" * len(hdr))
    for row in rows:
        pooled = row["results"]["pooled"]
        rate_s = f"{pooled['rate'] * 100:.2f}%" if pooled["rate"] is not None else "n/d"
        ci_s = (
            f"[{pooled['ci95_wilson'][0] * 100:.2f}%, {pooled['ci95_wilson'][1] * 100:.2f}%]"
            if pooled["denominator"]
            else "n/d"
        )
        pub_s = (
            str(row["published"])[:30]
            if row["published"] is not None
            else "sem comparador"
        )
        print(
            f"{row['indicator']:38s} {row['denominator_label']:8s} {pooled['numerator']}/{pooled['denominator']:<9d} {rate_s:8s} {ci_s:20s} {pub_s:30s}"
        )
    print()
    print("contagens de reconciliação (direto de classify.json):")
    for k, v in reconciliation.items():
        print(f"   {k}: {v}")


if __name__ == "__main__":
    main()
