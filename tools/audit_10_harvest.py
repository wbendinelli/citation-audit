"""Etapa 10: colheita multi-fonte do grafo de citações.

Une OpenAlex + Semantic Scholar + OpenCitations (COCI/Crossref) + Europe PMC,
deduplica por DOI e por título normalizado, e classifica o acesso de cada citante.
"""
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import auditlib

CFG = auditlib.load_config()
MAIL = CFG.get("mailto") or CFG.get("contact_email")


# ---------------- fontes ----------------
def src_openalex(doi):
    w = auditlib.jget(f"https://api.openalex.org/works/https://doi.org/{doi}?mailto={MAIL}")
    if not w: return []
    wid = w["id"].rsplit("/", 1)[-1]
    out, cur = [], "*"
    while cur:
        p = auditlib.jget(f"https://api.openalex.org/works?filter=cites:{wid}&per-page=200&cursor={cur}&mailto={MAIL}")
        if not p: break
        for c in p.get("results", []):
            oa = c.get("open_access") or {}
            src = (c.get("primary_location") or {}).get("source") or {}
            out.append({
                "doi": auditlib.norm_doi(c.get("doi")), "title": c.get("title"),
                "year": c.get("publication_year"), "venue": src.get("display_name"),
                "type": c.get("type"), "oa_status": oa.get("oa_status"),
                "is_oa": oa.get("is_oa"), "openalex": c.get("id"),
                "has_fulltext": c.get("has_fulltext"),
                "pdf": next((L.get("pdf_url") for L in (c.get("locations") or []) if L.get("pdf_url")), None),
                "landing": (c.get("primary_location") or {}).get("landing_page_url"),
                "src": ["openalex"],
            })
        cur = p.get("meta", {}).get("next_cursor")
        if not p.get("results"): break
    return out

def src_s2(doi):
    out, off = [], 0
    F = "title,year,venue,externalIds,isOpenAccess,openAccessPdf,publicationTypes"
    while True:
        p = auditlib.jget(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}/citations"
                 f"?fields={F}&limit=1000&offset={off}")
        if not p: break
        for e in p.get("data", []):
            c = e.get("citingPaper") or {}
            ex = c.get("externalIds") or {}
            out.append({
                "doi": auditlib.norm_doi(ex.get("DOI")), "title": c.get("title"), "year": c.get("year"),
                "venue": c.get("venue"), "type": (c.get("publicationTypes") or [None])[0],
                "is_oa": c.get("isOpenAccess"), "oa_status": None,
                "pdf": (c.get("openAccessPdf") or {}).get("url"), "landing": None,
                "arxiv": ex.get("ArXiv"), "pmcid": ex.get("PubMedCentral"),
                "corpusid": ex.get("CorpusId"), "src": ["s2"],
            })
        if len(p.get("data", [])) < 1000: break
        off += 1000
    return out

def src_opencitations(doi):
    d = auditlib.jget(f"https://opencitations.net/index/api/v2/citations/doi:{urllib.parse.quote(doi)}")
    out = []
    for row in (d or []):
        m = re.search(r"doi:([^\s;]+)", row.get("citing", "") or "")
        if m:
            out.append({"doi": auditlib.norm_doi(m.group(1)), "title": None, "year": None,
                        "venue": None, "src": ["opencitations"]})
    return out

def src_europepmc(doi):
    s = auditlib.jget("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query="
             f"DOI:%22{urllib.parse.quote(doi)}%22&format=json")
    res = ((s or {}).get("resultList") or {}).get("result") or []
    if not res: return []
    r = res[0]; src, pid = r.get("source"), r.get("id")
    if not (src and pid): return []
    out, page = [], 1
    while page <= 10:
        d = auditlib.jget(f"https://www.ebi.ac.uk/europepmc/webservices/rest/{src}/{pid}"
                 f"/citations?page={page}&pageSize=1000&format=json")
        lst = ((d or {}).get("citationList") or {}).get("citation") or []
        if not lst: break
        for c in lst:
            out.append({"doi": auditlib.norm_doi(c.get("doi")), "title": c.get("title"),
                        "year": c.get("pubYear"), "venue": c.get("journalAbbreviation"),
                        "src": ["europepmc"]})
        if len(lst) < 1000: break
        page += 1
    return out

# ---------------- merge ----------------
def merge(records):
    by_doi, by_title, out = {}, {}, []
    for r in records:
        if not r.get("title") and not r.get("doi"): continue
        d, t = r.get("doi"), auditlib.norm_title(r.get("title"))
        tgt = by_doi.get(d) if d else None
        if tgt is None and t and len(t) > 25: tgt = by_title.get(t)
        if tgt is None:
            r["src"] = list(r.get("src") or [])
            out.append(r)
            if d: by_doi[d] = r
            if t and len(t) > 25: by_title[t] = r
        else:
            for k, v in r.items():
                if k == "src":
                    tgt["src"] = sorted(set(tgt["src"]) | set(v))
                elif v not in (None, "", []) and tgt.get(k) in (None, "", []):
                    tgt[k] = v
            if d and d not in by_doi: by_doi[d] = tgt
            if t and len(t) > 25 and t not in by_title: by_title[t] = tgt
    return out

papers = {}
for key, p in CFG["papers"].items():
    doi = p["doi"]
    print(f"\n=== {key} · {doi} ===")
    recs, counts = [], {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(fn, doi): name for name, fn in
                (("openalex", src_openalex), ("s2", src_s2),
                 ("opencitations", src_opencitations), ("europepmc", src_europepmc))}
        for f in as_completed(futs):
            name = futs[f]
            try: got = f.result() or []
            except Exception as e: got = []; print(f"   {name}: erro {e}")
            counts[name] = len(got); recs += got
    for n, c in sorted(counts.items()): print(f"   {n:>14}: {c:>4}")
    u = merge(recs)
    print(f"   {'UNIÃO':>14}: {len(u):>4}  (dedup por DOI + título)")
    papers[key] = {"target": p, "citing": u}

try:
    m = auditlib.load_master()
except FileNotFoundError:
    m = {"meta": {"schema": 1}, "papers": {}}
m["papers"] = papers
auditlib.save_master(m)
print("\n-> data/master.json")
