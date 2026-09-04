"""Etapa 11: enriquece metadados faltantes e classifica o acesso de cada citante."""
import collections
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import auditlib

CFG = auditlib.load_config()
MAIL = CFG.get("mailto") or CFG.get("contact_email")


def enrich(rec):
    """Preenche buracos via OpenAlex, e acha a melhor rota OA via Unpaywall."""
    doi = rec.get("doi")
    if doi and (not rec.get("oa_status") or not rec.get("title") or not rec.get("venue")):
        w = auditlib.jget(f"https://api.openalex.org/works/https://doi.org/{urllib.parse.quote(doi)}?mailto={MAIL}")
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
        up = auditlib.jget(f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={MAIL}")
        b = (up or {}).get("best_oa_location") or {}
        if b.get("url_for_pdf"): rec["pdf"] = b["url_for_pdf"]
        elif b.get("url"):       rec["oa_landing"] = b["url"]
        if rec.get("is_oa") is None: rec["is_oa"] = bool(up and up.get("is_oa"))
    return rec

def triage(rec):
    """Classifica a rota de acesso de um registro sem texto. Nunca decide
    'tem_texto' — esse status só é atribuído por quem baixa e valida o
    arquivo de fato (audit_20/21/22 + audit_30)."""
    if not rec.get("doi"):                                     return "sem_doi"
    if rec.get("pdf") or rec.get("arxiv") or rec.get("pmcid"): return "oa_baixavel"
    if rec.get("is_oa") or rec.get("oa_landing"):              return "oa_sem_pdf_direto"
    return "fechado"

master = auditlib.load_master()
for key, blk in master["papers"].items():
    recs = blk["citing"]
    print(f"\n=== {key}: enriquecendo {len(recs)} registros ===")
    with ThreadPoolExecutor(max_workers=6) as ex:
        list(as_completed([ex.submit(enrich, r) for r in recs]))
    for i, r in enumerate(recs, 1):
        r["id"] = f"{key}_{i:03d}"
        # registro que já tem arquivo de texto validado em disco mantém
        # 'tem_texto' — a triagem só classifica quem ainda não tem texto.
        if r.get("status") == "tem_texto" and r.get("text_path") \
                and (auditlib.ROOT / r["text_path"]).exists():
            continue
        r["status"] = triage(r)
    c = collections.Counter(r["status"] for r in recs)
    for s in ("tem_texto","oa_baixavel","oa_sem_pdf_direto","fechado","sem_doi"):
        if c.get(s): print(f"   {s:>20}: {c[s]:>3}")
    print(f"   {'TOTAL':>20}: {len(recs):>3}")

auditlib.save_master(master)
print("\n-> data/master.json atualizado")
