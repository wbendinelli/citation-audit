#!/usr/bin/env python3
"""Etapa 64: auditoria das referências (R_valid) de cada artigo-foco.

O campo `referenced_works` do OpenAlex para os dois artigos-foco não é
confiável: contém stubs (IDs que não resolvem a metadado nenhum, tipo
"W66..."), referências que faltam (a bibliografia do PDF tem entradas que
o OpenAlex simplesmente não linkou) e -- pior -- referências falsas
(IDs que o OpenAlex lista como citados, mas cujo título não tem nada a
ver com nenhuma entrada da bibliografia real do PDF). Este script cruza
as duas fontes para montar o conjunto de referências válidas (R_valid)
que os scripts 65 e 66 usam.

Algoritmo (por artigo):
  1. busca o artigo-foco por DOI (config.json `papers.<artigo>.doi`);
  2. busca metadado de cada W em `referenced_works` do foco, em lotes de
     até 50 via `filter=ids.openalex:W1|W2|...`;
  3. casa cada referência do OpenAlex com a lista extraída do PDF
     (`data/cd/refs_pdf_<artigo>.json`) por DOI normalizado ou por
     similaridade de título (difflib) >= 0.85 com ano dentro de +-1;
     casamento por DOI só é aceito se o título também bater pelo menos
     fracamente (ver DOI_SANITY_FLOOR abaixo -- guarda contra DOI errado
     já impresso no PDF, ver nota nas decisões ambíguas no fim do
     arquivo);
  4. toda referência do PDF que sobra sem casar tenta reparo: DOI direto
     (`/works/https://doi.org/<doi>`) quando a referência do PDF tem DOI
     impresso, senão busca por título (`works?search=`), aceitando
     similaridade >= 0.90 e ano dentro de +-1 (ver nota sobre o desvio de
     "ano bate" para "ano +-1" no fim do arquivo);
  5. classifica cada referência do OpenAlex em matched/false_reference/stub
     e cada referência do PDF em matched/repaired/unresolvable.

R_valid = IDs OpenAlex das referências do PDF com status matched ou
repaired. Grava `data/cd/refs_audit_<artigo>.json`.

Uso:
  python3 tools/audit_64_refs_audit.py                  processa todos os artigos de config.json
  python3 tools/audit_64_refs_audit.py --paper grains    só um artigo (repetível)
  python3 tools/audit_64_refs_audit.py --no-cache        ignora o cache em disco (força rede)
  python3 tools/audit_64_refs_audit.py --help
"""

import argparse
import difflib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

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

CFG = auditlib.load_config()

# ---------------- limiares do algoritmo de casamento ----------------
TITLE_SIM_MATCH = 0.85  # passo 3: casamento OpenAlex-ref <-> PDF-ref
YEAR_TOL_MATCH = 1
YEAR_RELAX_SIM = (
    0.95  # título quase idêntico dispensa a checagem de ano (ver nota no fim)
)
TITLE_SIM_REPAIR = 0.90  # passo 4: reparo por busca de título
YEAR_TOL_REPAIR = 1  # desvio documentado de "ano bate" p/ "ano +-1"
DOI_SANITY_FLOOR = 0.40  # crivo de sanidade sobre casamento por DOI
DUP_SIM_FLOOR = 0.60  # ver nota sobre status "duplicate_of_matched"

FOCAL_SELECT = (
    "id,doi,title,publication_year,referenced_works,cited_by_count,counts_by_year"
)
REF_SELECT = (
    "id,doi,title,publication_year,authorships,cited_by_count,referenced_works_count"
)
REPAIR_SELECT = "id,doi,title,publication_year"


def sim_raw(a, b):
    """Razão difflib crua sobre o título normalizado, sem a variante
    'token sort' de sim() abaixo. Usada só pelo crivo de sanidade de DOI
    (DOI_SANITY_FLOOR): a variante token-sort é boa demais para esse job
    -- dois títulos sem nenhuma relação real podem convergir por
    coincidência de palavras curtas e comuns ("a", "and", "of", "in")
    quando reordenadas, o que é exatamente o cenário que o crivo de
    sanidade existe para pegar (ver nota no fim do arquivo: o par
    W1988530576 x "cold storages... Bihar" vai de 0.175 na razão crua
    para 0.45 na token-sort, o que destruiria o crivo se ele usasse
    sim() em vez de sim_raw())."""
    na, nb = auditlib.norm_title(a or ""), auditlib.norm_title(b or "")
    return difflib.SequenceMatcher(None, na, nb).ratio()


def sim(a, b):
    """Similaridade de título usada para CASAR (não para o crivo de
    sanidade de DOI, ver sim_raw acima): o máximo entre a razão difflib
    crua e a mesma razão sobre os títulos com as palavras reordenadas
    alfabeticamente ("token sort"). A segunda variante neutraliza
    diferenças de pura ordem de palavras (ex.: "quality service" vs
    "service quality") que a razão crua penaliza pesadamente mesmo sendo
    o mesmíssimo título -- ver nota no fim do arquivo."""
    na, nb = auditlib.norm_title(a or ""), auditlib.norm_title(b or "")
    r1 = difflib.SequenceMatcher(None, na, nb).ratio()
    ta, tb = " ".join(sorted(na.split())), " ".join(sorted(nb.split()))
    r2 = difflib.SequenceMatcher(None, ta, tb).ratio()
    return max(r1, r2)


def year_ok(y1, y2, tol):
    return y1 is None or y2 is None or abs(y1 - y2) <= tol


def load_pdf_refs(paper):
    path = auditlib.DATA / "cd" / f"refs_pdf_{paper}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def audit_paper(paper, client, snapshot_date):
    doi = CFG["papers"][paper]["doi"]
    focal_raw = client.work_by_doi(doi, select=FOCAL_SELECT)
    if not focal_raw:
        raise SystemExit(
            f"erro: não consegui resolver o artigo-foco '{paper}' pelo DOI {doi}"
        )
    focal_id = oax.short_id(focal_raw["id"])
    focal_year = focal_raw.get("publication_year")
    referenced_works_raw = sorted(
        {oax.short_id(x) for x in (focal_raw.get("referenced_works") or [])}
    )

    ref_meta = client.works_by_ids(referenced_works_raw, select=REF_SELECT)

    pdf_refs = load_pdf_refs(paper)
    pdf_by_n = {r["n"]: r for r in pdf_refs}

    claimed_pdf = {}  # n -> {"openalex_id", "status", "sim", "via"}
    oa_status = {}  # id curto -> {"status", "pdf_n", "sim"}

    # ---- passe 1: casamento por DOI normalizado (com crivo de sanidade) ----
    pdf_doi_index = {}
    for r in pdf_refs:
        d = auditlib.norm_doi(r.get("doi"))
        if d:
            pdf_doi_index.setdefault(d, []).append(r["n"])

    for oid, rec in ref_meta.items():
        d = auditlib.norm_doi(rec.get("doi"))
        if not d or d not in pdf_doi_index:
            continue
        for n in pdf_doi_index[d]:
            if n in claimed_pdf:
                continue
            pdf_title = pdf_by_n[n].get("title")
            oa_title = rec.get("title")
            if (
                oa_title
                and pdf_title
                and sim_raw(oa_title, pdf_title) < DOI_SANITY_FLOOR
            ):
                # DOI bate mas título não tem nada a ver -- DOI errado na
                # origem (ver nota no fim do arquivo). Não aceita; esta
                # referência do OpenAlex cai no pool de similaridade de
                # título abaixo (e vai acabar false_reference), e esta
                # referência do PDF segue para o reparo do passo 4.
                continue
            s = sim(oa_title, pdf_title) if (oa_title and pdf_title) else 1.0
            claimed_pdf[n] = {
                "openalex_id": oid,
                "status": "matched",
                "sim": round(s, 4),
                "via": "doi",
            }
            oa_status[oid] = {"status": "matched", "pdf_n": n, "sim": round(s, 4)}
            break

    # ---- passe 2: similaridade de título, atribuição gulosa por sim desc ----
    remaining_oids = [oid for oid in ref_meta if oid not in oa_status]
    remaining_ns = [n for n in pdf_by_n if n not in claimed_pdf]
    candidates = []
    for oid in remaining_oids:
        rec = ref_meta[oid]
        title, year = rec.get("title"), rec.get("publication_year")
        if not title:
            continue
        for n in remaining_ns:
            pr = pdf_by_n[n]
            s = sim(title, pr.get("title"))
            if s < TITLE_SIM_MATCH:
                continue
            # ano só é exigido (+-1) quando o título não é quase idêntico:
            # sim >= 1.0 acontece de vez em quando com ano bem diferente
            # (working paper vs. versão publicada, ou registro duplicado
            # do OpenAlex com metadado de ano ruim) -- ver nota no fim.
            if not year_ok(year, pr.get("year"), YEAR_TOL_MATCH) and s < YEAR_RELAX_SIM:
                continue
            candidates.append((s, oid, n))
    candidates.sort(key=lambda x: -x[0])
    for s, oid, n in candidates:
        if oid in oa_status or n in claimed_pdf:
            continue
        claimed_pdf[n] = {
            "openalex_id": oid,
            "status": "matched",
            "sim": round(s, 4),
            "via": "title",
        }
        oa_status[oid] = {"status": "matched", "pdf_n": n, "sim": round(s, 4)}

    # ---- referências OpenAlex resolvidas mas não casadas ----
    # Duas situações bem diferentes chegam aqui, e o relatório final fica
    # enganoso se as duas viram "false_reference" indiscriminadamente:
    #   (a) referência genuinamente estranha à bibliografia do PDF (título
    #       sem nenhuma relação com nenhuma das n entradas) -> false_reference;
    #   (b) o OpenAlex tem DOIS registros (IDs distintos) para o MESMO
    #       trabalho -- comum quando preprint e versão final não foram
    #       mesclados -- e o outro registro já "ganhou" o casamento com
    #       maior sim (ver caso W1487607581/W1547506455 do par n=2 do
    #       airline, nota no fim do arquivo). Isso não é uma citação
    #       falsa, é ruído de deduplicação do OpenAlex -> duplicate_of_matched.
    for oid, rec in ref_meta.items():
        if oid in oa_status:
            continue
        title = rec.get("title")
        best_n, best_s = None, 0.0
        if title:
            for n, pr in pdf_by_n.items():
                s = sim(title, pr.get("title"))
                if s > best_s:
                    best_s, best_n = s, n
        if (
            best_n is not None
            and best_s >= DUP_SIM_FLOOR
            and claimed_pdf.get(best_n, {}).get("status") == "matched"
        ):
            oa_status[oid] = {
                "status": "duplicate_of_matched",
                "pdf_n": best_n,
                "sim": round(best_s, 4),
            }
        else:
            oa_status[oid] = {
                "status": "false_reference",
                "pdf_n": best_n,
                "sim": round(best_s, 4),
            }

    # ---- IDs do referenced_works que nunca resolveram metadado -> stub ----
    for oid in referenced_works_raw:
        if oid not in oa_status:
            oa_status[oid] = {"status": "stub", "pdf_n": None, "sim": None}

    openalex_refs = []
    for oid in referenced_works_raw:
        st = oa_status[oid]
        rec = ref_meta.get(oid, {})
        openalex_refs.append(
            {
                "id": oid,
                "status": st["status"],
                "pdf_n": st.get("pdf_n"),
                "title": rec.get("title"),
                "year": rec.get("publication_year"),
                "sim": st.get("sim"),
            }
        )
    openalex_refs.sort(key=lambda r: r["id"])

    # ---- passo 4: reparo das referências do PDF que sobraram ----
    for n, r in pdf_by_n.items():
        if n in claimed_pdf:
            continue
        title, year, doi_n = (
            r.get("title"),
            r.get("year"),
            auditlib.norm_doi(r.get("doi")),
        )
        resolved, via = None, None
        if doi_n:
            w = client.work_by_doi(doi_n, select=REPAIR_SELECT)
            if w and w.get("title") and sim_raw(w["title"], title) >= DOI_SANITY_FLOOR:
                resolved, via = w, "doi"
            # DOI não resolveu OU falhou o crivo de sanidade -> tenta título
        if resolved is None:
            # per_page maior que o pedido no enunciado (3): o OpenAlex às
            # vezes tem duas entradas para o mesmo trabalho (preprint SSRN
            # + versão final na revista, ex. Prince & Simon 2015 abaixo) e
            # 3 resultados de title.search bastam para pegar as duas, mas
            # 5 dá mais folga sem custo real (ainda 1 chamada de rede).
            results = client.search_works(title, per_page=5, select=REPAIR_SELECT)
            best, best_s, best_dy = None, 0.0, None
            for cand in results:
                cy = cand.get("publication_year")
                s = sim(cand.get("title"), title)
                if s < TITLE_SIM_REPAIR:
                    continue
                if not year_ok(year, cy, YEAR_TOL_REPAIR) and s < YEAR_RELAX_SIM:
                    continue
                dy = abs(cy - year) if (cy is not None and year is not None) else 999
                # desempate: sim mais alta vence; sim empatada (diff < 1e-9,
                # ex. duas versões do mesmo artigo com título idêntico)
                # prefere o registro com ano mais perto do citado no PDF.
                if (
                    best is None
                    or s > best_s + 1e-9
                    or (abs(s - best_s) <= 1e-9 and dy < best_dy)
                ):
                    best_s, best, best_dy = s, cand, dy
            if best is not None and best_s >= TITLE_SIM_REPAIR:
                resolved, via = best, "title_search"
        if resolved:
            oid = oax.short_id(resolved["id"])
            claimed_pdf[n] = {
                "openalex_id": oid,
                "status": "repaired",
                "sim": round(sim(resolved.get("title"), title), 4),
                "via": via,
            }
        else:
            claimed_pdf[n] = {
                "openalex_id": None,
                "status": "unresolvable",
                "sim": None,
                "via": None,
            }

    pdf_refs_out = []
    for n in sorted(pdf_by_n):
        c = claimed_pdf[n]
        pdf_refs_out.append(
            {"n": n, "status": c["status"], "openalex_id": c["openalex_id"]}
        )

    r_valid = sorted(
        {
            c["openalex_id"]
            for c in claimed_pdf.values()
            if c["status"] in ("matched", "repaired") and c["openalex_id"]
        }
    )
    false_references = [r for r in openalex_refs if r["status"] == "false_reference"]
    duplicates_of_matched = [
        r for r in openalex_refs if r["status"] == "duplicate_of_matched"
    ]
    unresolvable = [
        {
            "n": n,
            "title": pdf_by_n[n].get("title"),
            "year": pdf_by_n[n].get("year"),
            "authors": pdf_by_n[n].get("authors"),
            "doi": pdf_by_n[n].get("doi"),
        }
        for n in sorted(pdf_by_n)
        if claimed_pdf[n]["status"] == "unresolvable"
    ]

    return {
        "focal": {
            "doi": doi,
            "openalex_id": focal_id,
            "year": focal_year,
            "cited_by_count": focal_raw.get("cited_by_count"),
        },
        "n_pdf": len(pdf_refs),
        "n_openalex_raw": len(referenced_works_raw),
        "n_valid": len(r_valid),
        "r_valid": r_valid,
        "openalex_refs": openalex_refs,
        "pdf_refs": pdf_refs_out,
        "false_references": false_references,
        "duplicates_of_matched": duplicates_of_matched,
        "unresolvable": unresolvable,
        "snapshot_date": snapshot_date,
        "requests": client.stats(),
    }


def print_summary(rows):
    print("\n" + "=" * 90)
    print(
        f"{'artigo':<10}{'n_pdf':>7}{'n_oa_raw':>10}{'n_valid':>9}"
        f"{'matched':>9}{'repaired':>10}{'unresolv':>10}{'false_ref':>11}{'dup':>6}{'stub':>7}"
    )
    for paper, res in rows:
        st_pdf = [r["status"] for r in res["pdf_refs"]]
        st_oa = [r["status"] for r in res["openalex_refs"]]
        print(
            f"{paper:<10}{res['n_pdf']:>7}{res['n_openalex_raw']:>10}{res['n_valid']:>9}"
            f"{st_pdf.count('matched'):>9}{st_pdf.count('repaired'):>10}"
            f"{st_pdf.count('unresolvable'):>10}{st_oa.count('false_reference'):>11}"
            f"{st_oa.count('duplicate_of_matched'):>6}{st_oa.count('stub'):>7}"
        )
    print("=" * 90)


def parse_args():
    p = argparse.ArgumentParser(
        description="Audita referenced_works do OpenAlex contra a bibliografia extraída do PDF "
        "de cada artigo-foco e monta o conjunto de referências válidas (R_valid).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--paper",
        choices=sorted(CFG["papers"]),
        action="append",
        help="processa só este artigo (repetível); default: todos os artigos de config.json",
    )
    p.add_argument(
        "--no-cache",
        action="store_true",
        help="ignora o cache em disco de data/cache/openalex/ (força nova busca na rede)",
    )
    return p.parse_args()


def main():
    args = parse_args()
    papers = args.paper or sorted(CFG["papers"])
    client = oax.OpenAlexClient(use_cache=not args.no_cache)
    snapshot_date = datetime.now(tz=timezone.utc).date().isoformat()
    rows = []
    for paper in papers:
        print(f"\n=== {paper} ===")
        res = audit_paper(paper, client, snapshot_date)
        out_path = auditlib.DATA / "cd" / f"refs_audit_{paper}.json"
        oax.save_json(res, out_path)
        print(
            f"  foco: {res['focal']['openalex_id']} (ano {res['focal']['year']}, "
            f"cited_by_count={res['focal']['cited_by_count']})"
        )
        print(f"  R_valid: {res['n_valid']}/{res['n_pdf']} referências do PDF")
        print(f"-> {out_path}")
        rows.append((paper, res))
    print_summary(rows)
    print(
        f"\nchamadas de rede: {client.n_network}  cache: {client.n_cache_hit}  "
        f"respostas nulas: {client.n_none}"
    )


if __name__ == "__main__":
    main()

# ---------------- decisões ambíguas (ver relatório final) ----------------
# 1. Crivo de sanidade em casamento por DOI (DOI_SANITY_FLOOR): a instrução
#    original só previa casar por DOI normalizado ou por similaridade de
#    título; descobri em desenvolvimento que refs_pdf_grains.json tem pelo
#    menos um DOI errado na própria extração do PDF (n=29, "cold storages
#    in the potato supply chain in Bihar", com o DOI de um manual de
#    neurocirurgia -- exatamente o W1988530576 citado no prompt como
#    referência falsa). Casar por DOI sem checar o título faria esse par
#    "bater" e contaminaria R_valid; o crivo (título tem que ter
#    similaridade >= 0.40 quando os dois lados têm título) resolve isso e
#    ainda deixa a referência do PDF cair no reparo por busca de título,
#    que encontra o artigo certo (W1887601576). IMPORTANTE: o crivo usa
#    sim_raw() (razão difflib crua), não sim() -- a variante "token sort"
#    da nota 3 abaixo inflava esse mesmo par de 0.175 para 0.45 (palavras
#    curtas e comuns como "and" convergem por acaso ao reordenar), o que
#    teria furado um crivo de 0.40 baseado em sim(). Descoberto rodando
#    o grains de verdade: a 1a versão do crivo (antes de sim_raw existir)
#    deixou passar W1988530576 como "matched" da ref 29 -- exatamente o
#    falso positivo que este crivo existe para barrar.
# 2. Tolerância de ano no reparo (passo 4): a instrução falava em "ano
#    bate", sem tolerância; usei +-1 (igual ao passo 3) porque o mesmo
#    caso acima só resolve com essa folga -- o PDF cita o working paper
#    como 2014, o OpenAlex indexa a versão como 2015.
# 3. sim() com variante "token sort" (palavras reordenadas em ordem
#    alfabética antes de comparar): descoberto testando o airline, onde
#    "Do low cost carriers provide low quality service" (OpenAlex) vs
#    "Do low cost carriers provide low service quality?" (PDF, ref 21) --
#    mesmíssimo artigo, só a ordem de duas palavras difere -- dava 0.83 de
#    razão difflib crua (abaixo do limiar 0.85) e ficaria fora de R_valid.
#    A variante de palavras reordenadas dá 1.0 para esse par sem abrir
#    margem para falso positivo (títulos genuinamente diferentes não
#    convergem só por reordenar palavras).
# 4. Ano como filtro leve, não rígido, no passo 3 e no passo 4
#    (YEAR_RELAX_SIM): mesmo airline, ref 6 e ref 18 batem título 1.0
#    (idêntico após normalizar) mas o ano do registro do OpenAlex difere
#    do ano impresso no PDF em 2 e 13 anos respectivamente -- working
#    paper vs. versão final, e um registro do OpenAlex com ano mal
#    indexado. Exigir ano +-1 sempre teria perdido as duas. A regra final:
#    +-1 ano é exigido só quando sim < 0.95; título quase idêntico passa
#    direto.
# 5. Status "duplicate_of_matched" (além dos três status oficiais de
#    referência do OpenAlex: matched/false_reference/stub): o OpenAlex às
#    vezes lista DOIS IDs para o mesmo trabalho real (registros não
#    mesclados -- ex.: airline ref 2, "Enhanced routines for instrumental
#    variables/GMM..." tem W1487607581 com título idêntico ao do PDF
#    (sim=1.0, vira matched) e W1547506455 com o título por extenso,
#    "...Generalized Method of Moments..." (sim=0.85 contra o PDF -- não
#    é o mesmo texto, é a mesma referência com abreviação diferente).
#    Rotular o segundo como "false_reference" (citação a um trabalho
#    estranho à bibliografia) seria enganoso -- ele não é uma referência
#    falsa, é ruído de deduplicação do OpenAlex sobre uma referência já
#    confirmada. Por isso: toda referência do OpenAlex sem casamento cujo
#    título mais próximo (sim >= 0.60) já foi reivindicado por outra
#    referência do OpenAlex vira "duplicate_of_matched" em vez de
#    "false_reference", com a lista separada em `duplicates_of_matched`.
#    Isso não muda R_valid (que só depende do status das referências do
#    PDF); só deixa `false_references` de fato só com citações estranhas
#    à bibliografia, que é o que a auditoria quer sinalizar.
