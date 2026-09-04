"""Fase A: inventario de citantes + melhor rota de full text (OpenAlex + Unpaywall)."""
import json, urllib.request, urllib.error, time, os

MAIL = "wbendinelli@gmail.com"
TARGETS = {
    "grains":  {"doi":"10.1016/j.spc.2019.09.002", "year":2020,
                "label":"Post-harvest losses of grains (Sustainable Prod. & Consumption)"},
    "airline": {"doi":"10.1016/j.tra.2016.01.001", "year":2016,
                "label":"Airline delays / LCC entry (Transportation Research A)"},
}

def get(u, tries=5):
    for a in range(tries):
        try:
            r = urllib.request.Request(u, headers={"Accept":"application/json",
                "User-Agent":f"citation-audit/0.1 (mailto:{MAIL})"})
            with urllib.request.urlopen(r, timeout=60) as x:
                return json.load(x)
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            time.sleep(min(20, 2**a))
        except Exception:
            time.sleep(min(20, 2**a))
    return None

def best_fulltext_route(work):
    """Escolhe a melhor rota de texto completo, da mais confiavel para a menos."""
    ids = work.get("ids") or {}
    locs = (work.get("locations") or [])
    routes = []
    pmcid = next((str(v) for k,v in ids.items() if k=="pmid" and False), None)
    for L in locs:
        src = (L.get("source") or {})
        url = L.get("pdf_url") or ""
        land = L.get("landing_page_url") or ""
        blob = f"{url} {land}".lower()
        if "ncbi.nlm.nih.gov/pmc" in blob or (src.get("display_name") or "")=="PubMed Central":
            routes.append(("europepmc", land or url))
        elif "arxiv.org" in blob:
            routes.append(("arxiv", land or url))
        elif L.get("pdf_url"):
            routes.append(("pdf", L["pdf_url"]))
    # Unpaywall como rede de seguranca
    doi = (work.get("doi") or "").replace("https://doi.org/","")
    if doi:
        up = get(f"https://api.unpaywall.org/v2/{doi}?email={MAIL}")
        if up and up.get("best_oa_location"):
            b = up["best_oa_location"]
            if b.get("url_for_pdf"): routes.append(("pdf", b["url_for_pdf"]))
            elif b.get("url"):       routes.append(("html", b["url"]))
    seen, out = set(), []
    for kind, u in routes:
        if u and u not in seen:
            seen.add(u); out.append({"kind":kind, "url":u})
    return out

inventory = {}
for key, tgt in TARGETS.items():
    w = get(f"https://api.openalex.org/works/https://doi.org/{tgt['doi']}?mailto={MAIL}")
    wid = w["id"].rsplit("/",1)[-1]
    rows, cur = [], "*"
    while cur:
        p = get(f"https://api.openalex.org/works?filter=cites:{wid}&per-page=200&cursor={cur}&mailto={MAIL}")
        if not p: break
        rows += p.get("results", [])
        cur = p.get("meta",{}).get("next_cursor")
        if not p.get("results"): break
    print(f"[{key}] {len(rows)} citantes")

    items = []
    for i, c in enumerate(rows, 1):
        oa = c.get("open_access") or {}
        auth = [a["author"].get("display_name","") for a in (c.get("authorships") or [])[:3]]
        src = (c.get("primary_location") or {}).get("source") or {}
        routes = best_fulltext_route(c) if oa.get("is_oa") or c.get("has_fulltext") else []
        items.append({
            "n": i,
            "openalex": c.get("id"),
            "doi": (c.get("doi") or "").replace("https://doi.org/",""),
            "title": c.get("title"),
            "year": c.get("publication_year"),
            "venue": src.get("display_name"),
            "authors": auth,
            "oa_status": oa.get("oa_status"),
            "has_fulltext": c.get("has_fulltext"),
            "routes": routes,
        })
        if i % 15 == 0: print(f"   ...{i}")
    inventory[key] = {"target": TARGETS[key], "citing": items}

out = os.path.join(os.path.dirname(__file__), "inventory.json")
json.dump(inventory, open(out,"w"), ensure_ascii=False, indent=1)

print("\n" + "="*70)
for key, blk in inventory.items():
    items = blk["citing"]
    withroute = [x for x in items if x["routes"]]
    print(f"{key:>8}: {len(items):>3} citantes | {len(withroute):>3} com rota de full text "
          f"({100*len(withroute)/max(1,len(items)):.0f}%)")
print(f"\nsalvo em {out}")
