"""Etapa 10: colheita multi-fonte do grafo de citações.

Une OpenAlex + Semantic Scholar + OpenCitations (COCI/Crossref) + Europe PMC,
deduplica por DOI e por título normalizado, e classifica o acesso de cada citante.
"""

import copy
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import auditlib

CFG = auditlib.load_config()
MAIL = CFG.get("mailto") or CFG.get("contact_email")


def json_da_fonte(url):
    """Falha de rede não pode parecer uma lista de citações vazia."""
    value = auditlib.jget(url, tries=2, timeout=30)
    if value is None:
        raise RuntimeError(f"fonte indisponível: {url.split('?')[0]}")
    return value


# ---------------- fontes ----------------
def src_openalex(doi):
    w = json_da_fonte(
        f"https://api.openalex.org/works/https://doi.org/{doi}?mailto={MAIL}"
    )
    if not w:
        return []
    wid = w["id"].rsplit("/", 1)[-1]
    out, cur = [], "*"
    while cur:
        p = json_da_fonte(
            f"https://api.openalex.org/works?filter=cites:{wid}&per-page=200&cursor={cur}&mailto={MAIL}"
        )
        if not p:
            break
        for c in p.get("results", []):
            oa = c.get("open_access") or {}
            src = (c.get("primary_location") or {}).get("source") or {}
            out.append(
                {
                    "doi": auditlib.norm_doi(c.get("doi")),
                    "title": c.get("title"),
                    "year": c.get("publication_year"),
                    "venue": src.get("display_name"),
                    "type": c.get("type"),
                    "oa_status": oa.get("oa_status"),
                    "is_oa": oa.get("is_oa"),
                    "openalex": c.get("id"),
                    "has_fulltext": c.get("has_fulltext"),
                    "pdf": next(
                        (
                            L.get("pdf_url")
                            for L in (c.get("locations") or [])
                            if L.get("pdf_url")
                        ),
                        None,
                    ),
                    "landing": (c.get("primary_location") or {}).get(
                        "landing_page_url"
                    ),
                    "src": ["openalex"],
                }
            )
        cur = p.get("meta", {}).get("next_cursor")
        if not p.get("results"):
            break
    return out


def src_s2(doi):
    out, off = [], 0
    F = "title,year,venue,externalIds,isOpenAccess,openAccessPdf,publicationTypes"
    while True:
        p = json_da_fonte(
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}/citations"
            f"?fields={F}&limit=1000&offset={off}"
        )
        if not p:
            break
        for e in p.get("data", []):
            c = e.get("citingPaper") or {}
            ex = c.get("externalIds") or {}
            out.append(
                {
                    "doi": auditlib.norm_doi(ex.get("DOI")),
                    "title": c.get("title"),
                    "year": c.get("year"),
                    "venue": c.get("venue"),
                    "type": (c.get("publicationTypes") or [None])[0],
                    "is_oa": c.get("isOpenAccess"),
                    "oa_status": None,
                    "pdf": (c.get("openAccessPdf") or {}).get("url"),
                    "landing": None,
                    "arxiv": ex.get("ArXiv"),
                    "pmcid": ex.get("PubMedCentral"),
                    "corpusid": ex.get("CorpusId"),
                    "src": ["s2"],
                }
            )
        if len(p.get("data", [])) < 1000:
            break
        off += 1000
    return out


def src_opencitations(doi):
    d = json_da_fonte(
        f"https://opencitations.net/index/api/v2/citations/doi:{urllib.parse.quote(doi)}"
    )
    out = []
    for row in d or []:
        m = re.search(r"doi:([^\s;]+)", row.get("citing", "") or "")
        if m:
            out.append(
                {
                    "doi": auditlib.norm_doi(m.group(1)),
                    "title": None,
                    "year": None,
                    "venue": None,
                    "src": ["opencitations"],
                }
            )
    return out


def src_europepmc(doi):
    s = json_da_fonte(
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query="
        f"DOI:%22{urllib.parse.quote(doi)}%22&format=json"
    )
    res = ((s or {}).get("resultList") or {}).get("result") or []
    if not res:
        return []
    r = res[0]
    src, pid = r.get("source"), r.get("id")
    if not (src and pid):
        return []
    out, page = [], 1
    while page <= 10:
        d = json_da_fonte(
            f"https://www.ebi.ac.uk/europepmc/webservices/rest/{src}/{pid}"
            f"/citations?page={page}&pageSize=1000&format=json"
        )
        lst = ((d or {}).get("citationList") or {}).get("citation") or []
        if not lst:
            break
        for c in lst:
            out.append(
                {
                    "doi": auditlib.norm_doi(c.get("doi")),
                    "title": c.get("title"),
                    "year": c.get("pubYear"),
                    "venue": c.get("journalAbbreviation"),
                    "src": ["europepmc"],
                }
            )
        if len(lst) < 1000:
            break
        page += 1
    return out


# ---------------- merge ----------------
def merge(records):
    by_doi, by_title, out = {}, {}, []
    for r in records:
        if not r.get("title") and not r.get("doi"):
            continue
        r = copy.deepcopy(r)
        r["doi"] = auditlib.norm_doi(r.get("doi"))
        d, t = r.get("doi"), auditlib.norm_title(r.get("title"))
        tgt = by_doi.get(d) if d else None
        if tgt is None and t and len(t) > 25:
            tgt = by_title.get(t)
        if tgt is None:
            r["src"] = list(r.get("src") or [])
            out.append(r)
            if d:
                by_doi[d] = r
            if t and len(t) > 25:
                by_title[t] = r
        else:
            if d and tgt.get("doi") and d != tgt["doi"]:
                tgt["alternate_dois"] = sorted(set(tgt.get("alternate_dois", [])) | {d})
            for k, v in r.items():
                if k in ("src", "alternate_dois"):
                    tgt[k] = sorted(set(tgt.get(k, [])) | set(v))
                elif v not in (None, "", []) and tgt.get(k) in (None, "", []):
                    tgt[k] = v
            if d and d not in by_doi:
                by_doi[d] = tgt
            if t and len(t) > 25 and t not in by_title:
                by_title[t] = tgt
    return out


def atualizar_registros(key, antigos, novos, excluidos=()):
    """União incremental: IDs, evidências e vereditos antigos têm prioridade."""
    # O inventário pode conter versões explicitamente mantidas pelo método.
    # Só os candidatos novos são fundidos; nunca recollapse decisões antigas.
    records = copy.deepcopy(antigos)
    by_doi = {auditlib.norm_doi(r.get("doi")): r for r in records if r.get("doi")}
    by_title = {
        auditlib.norm_title(r.get("title")): r
        for r in records
        if len(auditlib.norm_title(r.get("title"))) > 25
    }
    for novo in sorted(
        merge(novos),
        key=lambda r: (
            auditlib.norm_doi(r.get("doi")) or "",
            auditlib.norm_title(r.get("title")),
        ),
    ):
        d, t = (
            auditlib.norm_doi(novo.get("doi")),
            auditlib.norm_title(novo.get("title")),
        )
        if d in excluidos or (not d and not t):
            continue
        target = by_doi.get(d) if d else None
        if target is None and len(t) > 25:
            target = by_title.get(t)
        if target is None:
            target = copy.deepcopy(novo)
            target["doi"] = d
            records.append(target)
        else:
            merged = merge([target, novo])[0]
            target.clear()
            target.update(merged)
        if d:
            by_doi[d] = target
        if len(t) > 25:
            by_title[t] = target
    used = {r["id"] for r in antigos if r.get("id")}
    n = max(
        (
            int(rid.rsplit("_", 1)[1])
            for rid in used
            if rid.startswith(f"{key}_") and rid.rsplit("_", 1)[1].isdigit()
        ),
        default=0,
    )
    for r in records:
        if not r.get("id"):
            n += 1
            r["id"] = f"{key}_{n:03d}"
    return records


def main():
    try:
        master = auditlib.load_master()
    except FileNotFoundError:
        master = {"meta": {"schema": 1}, "papers": {}}
    excluidos = set(auditlib.classify_entries(auditlib.load_classify_orfas()))
    execution = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "script": "audit_10_harvest.py",
        "papers": {},
    }
    for key, paper in CFG["papers"].items():
        print(f"\n=== {key} · {paper['doi']} ===", flush=True)
        recs, sources = [], {}
        # A ordem das fontes é fixa, independente da ordem das respostas.
        with ThreadPoolExecutor(max_workers=4) as ex:
            futs = {
                name: ex.submit(fn, paper["doi"])
                for name, fn in (
                    ("openalex", src_openalex),
                    ("s2", src_s2),
                    ("opencitations", src_opencitations),
                    ("europepmc", src_europepmc),
                )
            }
            for name, future in futs.items():
                try:
                    got = future.result()
                    sources[name] = {"status": "ok", "records": len(got)}
                    recs.extend(got)
                except Exception as exc:
                    sources[name] = {"status": "indisponivel", "error": str(exc)}
                print(f"   {name}: {sources[name]}", flush=True)
        block = master["papers"].setdefault(key, {"target": paper, "citing": []})
        before = block["citing"]
        after = atualizar_registros(key, before, recs, excluidos)
        previous_ids = {r["id"] for r in before}
        added = [r["id"] for r in after if r["id"] not in previous_ids]
        block["citing"] = after
        execution["papers"][key] = {
            "sources": sources,
            "before": len(before),
            "after": len(after),
            "added_ids": added,
            "excluded_archived_dois": sorted(
                {r.get("doi") for r in recs if r.get("doi") in excluidos}
            ),
        }
        print(
            f"   inventário: {len(before)} -> {len(after)}; novos: {len(added)}",
            flush=True,
        )
    auditlib.save_master(master)
    auditlib._dump(execution, auditlib.DATA / "harvest_latest.json")
    print("-> data/master.json e data/harvest_latest.json")


if __name__ == "__main__":
    main()
