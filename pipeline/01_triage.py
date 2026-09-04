"""Etapa 1: enriquece metadados faltantes e classifica o acesso de cada citante."""
import json, os, re, time, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG  = json.load(open(f"{ROOT}/config.json")); MAIL = CFG["contact_email"]

def jget(url, tries=4):
    h = {"Accept":"application/json","User-Agent":f"citation-audit/0.2 (mailto:{MAIL})"}
    for a in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            time.sleep(min(15,2**a))
        except Exception: time.sleep(min(15,2**a))
    return None

def enrich(rec):
    """Preenche buracos via OpenAlex, e acha a melhor rota OA via Unpaywall."""
    doi = rec.get("doi")
    if doi and (not rec.get("oa_status") or not rec.get("title") or not rec.get("venue")):
        w = jget(f"https://api.openalex.org/works/https://doi.org/{urllib.parse.quote(doi)}?mailto={MAIL}")
        if w:
            oa = w.get("open_access") or {}
            src = (w.get("primary_location") or {}).get("source") or {}
            rec.setdefault("title", w.get("title")); rec["title"] = rec.get("title") or w.get("title")
            rec["year"]      = rec.get("year") or w.get("publication_year")
            rec["venue"]     = rec.get("venue") or src.get("display_name")
            rec["type"]      = rec.get("type") or w.get("type")
            rec["oa_status"] = rec.get("oa_status") or oa.get("oa_status")
            rec["is_oa"]     = oa.get("is_oa") if rec.get("is_oa") is None else rec["is_oa"]
            rec["has_fulltext"] = w.get("has_fulltext")
            if not rec.get("pdf"):
                rec["pdf"] = next((L.get("pdf_url") for L in (w.get("locations") or []) if L.get("pdf_url")), None)
            rec["landing"] = rec.get("landing") or (w.get("primary_location") or {}).get("landing_page_url")
    if doi and not rec.get("pdf"):
        up = jget(f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={MAIL}")
        b = (up or {}).get("best_oa_location") or {}
        if b.get("url_for_pdf"): rec["pdf"] = b["url_for_pdf"]
        elif b.get("url"):       rec["oa_landing"] = b["url"]
        if rec.get("is_oa") is None: rec["is_oa"] = bool(up and up.get("is_oa"))
    return rec

def triage(rec, have):
    if rec.get("id") in have or rec.get("doi") in have: return "tem_texto"
    if not rec.get("doi"):                              return "sem_doi"
    if rec.get("pdf") or rec.get("arxiv") or rec.get("pmcid"): return "oa_baixavel"
    if rec.get("is_oa") or rec.get("oa_landing"):       return "oa_sem_pdf_direto"
    return "fechado"

# DOIs cujo texto ja temos da rodada anterior
old = json.load(open(f"{ROOT}/data/inventory.json"))
have = set()
for k, b in old.items():
    for it in b["citing"]:
        if it.get("text_path") and (it.get("doi")): have.add(it["doi"].lower())

master = json.load(open(f"{ROOT}/data/master.json"))
import collections
for key, blk in master.items():
    recs = blk["citing"]
    print(f"\n=== {key}: enriquecendo {len(recs)} registros ===")
    with ThreadPoolExecutor(max_workers=6) as ex:
        list(as_completed([ex.submit(enrich, r) for r in recs]))
    for i, r in enumerate(recs, 1):
        r["id"] = f"{key}_{i:03d}"
        r["status"] = triage(r, have)
    c = collections.Counter(r["status"] for r in recs)
    for s in ("tem_texto","oa_baixavel","oa_sem_pdf_direto","fechado","sem_doi"):
        if c.get(s): print(f"   {s:>20}: {c[s]:>3}")
    print(f"   {'TOTAL':>20}: {len(recs):>3}")

json.dump(master, open(f"{ROOT}/data/master.json","w"), ensure_ascii=False, indent=1)
print("\n-> data/master.json atualizado")
