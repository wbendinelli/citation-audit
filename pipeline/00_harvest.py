"""Etapa 0: colheita multi-fonte do grafo de citações.

Une OpenAlex + Semantic Scholar + OpenCitations (COCI/Crossref) + Europe PMC,
deduplica por DOI e por título normalizado, e classifica o acesso de cada citante.
"""
import json, os, re, time, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CFG  = json.load(open(os.path.join(ROOT, "config.json")))
MAIL = CFG["contact_email"]

def jget(url, tries=5, headers=None):
    h = {"Accept": "application/json", "User-Agent": f"citation-audit/0.2 (mailto:{MAIL})"}
    if headers: h.update(headers)
    for a in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=90) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            time.sleep(min(25, 2 ** a))
        except Exception:
            time.sleep(min(25, 2 ** a))
    return None

def norm_doi(d):
    if not d: return None
    d = d.strip().lower()
    d = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", d)
    d = re.sub(r"^doi:", "", d)
    return d or None

def norm_title(t):
    if not t: return ""
    t = re.sub(r"<[^>]+>", " ", t).lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

# ---------------- fontes ----------------
def src_openalex(doi):
    w = jget(f"https://api.openalex.org/works/https://doi.org/{doi}?mailto={MAIL}")
    if not w: return []
    wid = w["id"].rsplit("/", 1)[-1]
    out, cur = [], "*"
    while cur:
        p = jget(f"https://api.openalex.org/works?filter=cites:{wid}&per-page=200&cursor={cur}&mailto={MAIL}")
        if not p: break
        for c in p.get("results", []):
            oa = c.get("open_access") or {}
            src = (c.get("primary_location") or {}).get("source") or {}
            out.append({
                "doi": norm_doi(c.get("doi")), "title": c.get("title"),
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
        p = jget(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}/citations"
                 f"?fields={F}&limit=1000&offset={off}")
        if not p: break
        for e in p.get("data", []):
            c = e.get("citingPaper") or {}
            ex = c.get("externalIds") or {}
            out.append({
                "doi": norm_doi(ex.get("DOI")), "title": c.get("title"), "year": c.get("year"),
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
    d = jget(f"https://opencitations.net/index/api/v2/citations/doi:{urllib.parse.quote(doi)}")
    out = []
    for row in (d or []):
        m = re.search(r"doi:([^\s;]+)", row.get("citing", "") or "")
        if m:
            out.append({"doi": norm_doi(m.group(1)), "title": None, "year": None,
                        "venue": None, "src": ["opencitations"]})
    return out

def src_europepmc(doi):
    s = jget("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query="
             f"DOI:%22{urllib.parse.quote(doi)}%22&format=json")
    res = ((s or {}).get("resultList") or {}).get("result") or []
    if not res: return []
    r = res[0]; src, pid = r.get("source"), r.get("id")
    if not (src and pid): return []
    out, page = [], 1
    while page <= 10:
        d = jget(f"https://www.ebi.ac.uk/europepmc/webservices/rest/{src}/{pid}"
                 f"/citations?page={page}&pageSize=1000&format=json")
        lst = ((d or {}).get("citationList") or {}).get("citation") or []
        if not lst: break
        for c in lst:
            out.append({"doi": norm_doi(c.get("doi")), "title": c.get("title"),
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
        d, t = r.get("doi"), norm_title(r.get("title"))
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

master = {}
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
    master[key] = {"target": p, "citing": u}

json.dump(master, open(os.path.join(ROOT, "data", "master.json"), "w"),
          ensure_ascii=False, indent=1)
print("\n-> data/master.json")
