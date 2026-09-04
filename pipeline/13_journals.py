"""Etapa 13: banco de periódicos. Enriquece cada veículo com metadados do OpenAlex
(ISSN, editora, país, h-index, citedness de 2 anos) para permitir atribuição de tier."""
import json, os, re, time, unicodedata, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG  = json.load(open(f"{ROOT}/config.json")); MAIL = CFG["contact_email"]
M    = json.load(open(f"{ROOT}/data/master.json"))

def jget(u, tries=4):
    for a in range(tries):
        try:
            req = urllib.request.Request(u, headers={"Accept":"application/json",
                  "User-Agent":f"citation-audit/0.4 (mailto:{MAIL})"})
            with urllib.request.urlopen(req, timeout=60) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            time.sleep(min(12, 2**a))
        except Exception: time.sleep(min(12, 2**a))
    return None

def venue_norm(v):
    import html
    v = html.unescape(v or "").strip()
    v = re.sub(r"\s+", " ", v)
    v = re.sub(r"(Transportation Research Part [A-F])\s*:?\s*.*", r"\1", v)
    return re.sub(r"\s*[:,]\s*$", "", v)

# 1) resolve o source de cada citante direto pelo DOI (mais confiável que buscar por nome)
def source_de(doi):
    w = jget(f"https://api.openalex.org/works/https://doi.org/{urllib.parse.quote(doi)}?mailto={MAIL}")
    if not w: return None
    loc = (w.get("primary_location") or {}).get("source") or {}
    return {"source_id": loc.get("id"), "display_name": loc.get("display_name"),
            "issn_l": loc.get("issn_l"), "host": loc.get("host_organization_name"),
            "type": loc.get("type"), "work_type": w.get("type")}

alvos = {}
for k, b in M.items():
    for r in b["citing"]:
        if r.get("doi"): alvos[r["id"]] = r

print(f"resolvendo source de {len(alvos)} citantes com DOI...")
with ThreadPoolExecutor(max_workers=6) as ex:
    futs = {ex.submit(source_de, r["doi"]): r for r in alvos.values()}
    for f in as_completed(futs):
        r = futs[f]
        try: s = f.result()
        except Exception: s = None
        if s:
            r["source_id"]  = s["source_id"]
            r["venue"]      = s["display_name"] or r.get("venue")
            r["issn_l"]     = s["issn_l"]
            r["publisher"]  = s["host"]
            r["source_type"]= s["type"]
            r["work_type"]  = s["work_type"]

# 2) metadados do periódico, um por source_id
ids = sorted({r["source_id"] for r in alvos.values() if r.get("source_id")})
print(f"buscando metadados de {len(ids)} periódicos distintos...")
def meta(sid):
    s = jget(f"{sid.replace('https://openalex.org/','https://api.openalex.org/sources/')}?mailto={MAIL}")
    if not s: return sid, None
    st = s.get("summary_stats") or {}
    return sid, {"id":sid, "nome":s.get("display_name"), "issn_l":s.get("issn_l"),
        "issn":s.get("issn"), "editora":s.get("host_organization_name"),
        "pais":s.get("country_code"), "tipo":s.get("type"),
        "is_oa":s.get("is_oa"), "in_doaj":s.get("is_in_doaj"),
        "h_index":st.get("h_index"), "citedness_2a":st.get("2yr_mean_citedness"),
        "i10":st.get("i10_index"), "works":s.get("works_count"),
        "areas":[t.get("display_name") for t in (s.get("topics") or [])[:3]]}
JR = {}
with ThreadPoolExecutor(max_workers=6) as ex:
    for f in as_completed([ex.submit(meta, i) for i in ids]):
        sid, m = f.result()
        if m: JR[sid] = m
json.dump(JR, open(f"{ROOT}/data/journals.json","w"), ensure_ascii=False, indent=1)
json.dump(M,  open(f"{ROOT}/data/master.json","w"),  ensure_ascii=False, indent=1)
print(f"-> data/journals.json com {len(JR)} periódicos")
com = [m for m in JR.values() if m.get("citedness_2a") is not None]
print(f"   com citedness de 2 anos: {len(com)}/{len(JR)}")
