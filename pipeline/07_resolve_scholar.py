"""Etapa 7: tenta resolver DOI dos registros exclusivos do Scholar via Crossref/OpenAlex.

Os títulos vêm truncados, então a validação é por prefixo normalizado do título devolvido.
"""
import json, os, re, time, unicodedata, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG  = json.load(open(f"{ROOT}/config.json")); MAIL = CFG["contact_email"]

def norm(t):
    t = unicodedata.normalize("NFKD", t or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", t)).strip()

def jget(u, tries=4):
    h = {"Accept":"application/json","User-Agent":f"citation-audit/0.3 (mailto:{MAIL})"}
    for a in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            time.sleep(min(12, 2**a))
        except Exception: time.sleep(min(12, 2**a))
    return None

def resolve(rec):
    q = urllib.parse.quote(rec["title"][:120])
    want = norm(rec["title"])[:55]
    # Crossref
    d = jget(f"https://api.crossref.org/works?query.bibliographic={q}&rows=3&mailto={MAIL}")
    for it in ((d or {}).get("message") or {}).get("items", []):
        t = (it.get("title") or [""])[0]
        if norm(t).startswith(want[:45]) or want.startswith(norm(t)[:45]):
            rec["doi"] = (it.get("DOI") or "").lower()
            rec["venue"] = rec.get("venue") or (it.get("container-title") or [None])[0]
            rec["title"] = t
            rec["type"] = it.get("type")
            rec["resolved_by"] = "crossref"
            return rec
    # OpenAlex
    d = jget(f"https://api.openalex.org/works?search={q}&per-page=3&mailto={MAIL}")
    for w in (d or {}).get("results", []):
        t = w.get("title") or ""
        if norm(t).startswith(want[:45]) or want.startswith(norm(t)[:45]):
            oa = w.get("open_access") or {}
            src = (w.get("primary_location") or {}).get("source") or {}
            rec["doi"] = (w.get("doi") or "").replace("https://doi.org/","").lower() or None
            rec["title"] = t
            rec["venue"] = rec.get("venue") or src.get("display_name")
            rec["year"] = rec.get("year") or w.get("publication_year")
            rec["oa_status"] = oa.get("oa_status"); rec["is_oa"] = oa.get("is_oa")
            rec["pdf"] = next((L.get("pdf_url") for L in (w.get("locations") or []) if L.get("pdf_url")), None)
            rec["resolved_by"] = "openalex"
            return rec
    rec["resolved_by"] = None
    return rec

M = json.load(open(f"{ROOT}/data/master.json"))
todo = [r for k,b in M.items() for r in b["citing"] if r["status"] == "so_scholar"]
print(f"resolvendo {len(todo)} registros exclusivos do Scholar...")
with ThreadPoolExecutor(max_workers=4) as ex:
    list(as_completed([ex.submit(resolve, r) for r in todo]))

ok = 0
for r in todo:
    if r.get("doi"):
        ok += 1
        r["status"] = ("oa_baixavel" if r.get("pdf")
                       else ("oa_sem_pdf_direto" if r.get("is_oa") else "fechado"))
    else:
        r["status"] = "so_scholar_sem_doi"
json.dump(M, open(f"{ROOT}/data/master.json","w"), ensure_ascii=False, indent=1)

import collections
print(f"DOI resolvido: {ok}/{len(todo)}")
print("  por fonte:", dict(collections.Counter(r.get("resolved_by") for r in todo)))
tot = collections.Counter(r["status"] for k,b in M.items() for r in b["citing"])
print(f"\ninventario total: {sum(len(b['citing']) for b in M.values())}")
for k,v in sorted(tot.items(), key=lambda x:-x[1]): print(f"  {k:>22}: {v:>3}")
