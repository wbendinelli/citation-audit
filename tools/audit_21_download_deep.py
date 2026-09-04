"""Etapa 21: varre TODAS as localizações OA conhecidas (não só a melhor)."""

import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import auditlib

CFG = auditlib.load_config()
MAIL = CFG.get("mailto") or CFG.get("contact_email")
H = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch(u, timeout=75, ref=None):
    h = dict(H)
    if ref:
        h["Referer"] = ref
    with urllib.request.urlopen(
        urllib.request.Request(u, headers=h), timeout=timeout
    ) as r:
        return r.read(), r.headers.get("Content-Type", ""), r.geturl()


def save_and_extract(body, rid):
    p = auditlib.PDF / f"{rid}.pdf"
    p.write_bytes(body)
    return auditlib.pdftext(p)


def all_locations(doi):
    w = auditlib.jget(
        f"https://api.openalex.org/works/https://doi.org/{urllib.parse.quote(doi)}?mailto={MAIL}"
    )
    if not w:
        return []
    urls = []
    for L in w.get("locations") or []:
        src = (L.get("source") or {}).get("display_name") or ""
        # prioriza repositorio (green) sobre publisher
        rank = (
            0
            if (
                L.get("is_accepted")
                or L.get("version") == "submittedVersion"
                or "repositor" in src.lower()
                or "arxiv" in src.lower()
                or "hal" in src.lower()
                or "ssrn" in src.lower()
            )
            else 1
        )
        if L.get("pdf_url"):
            urls.append((rank, L["pdf_url"]))
        if L.get("landing_page_url"):
            urls.append((rank + 2, L["landing_page_url"]))
    ids = w.get("ids") or {}
    if ids.get("pmid") or ids.get("pmcid"):
        pmc = (ids.get("pmcid") or "").rsplit("/", 1)[-1]
        if pmc:
            urls.append(
                (
                    0,
                    f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmc}/fullTextXML",
                )
            )
    seen = set()
    out = []
    for r, u in sorted(urls):
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def grab(r):
    for u in all_locations(r.get("doi") or ""):
        try:
            body, ctype, final = fetch(u, ref="https://www.google.com/")
            if body[:4] == b"%PDF" or "pdf" in ctype.lower():
                t = save_and_extract(body, r["id"])
                if t:
                    return t, f"pdf:{final}"
            else:
                t = auditlib.strip_html(body)
                if len(t) > 2500:
                    return t, f"html:{final}"
                # procura link de PDF na landing page
                m = re.findall(
                    r'href="([^"]+\.pdf[^"]*)"', body.decode("utf-8", "ignore")
                )[:3]
                for href in m:
                    try:
                        pu = urllib.parse.urljoin(final, href)
                        b2, _c2, f2 = fetch(pu, ref=final)
                        if b2[:4] == b"%PDF":
                            t2 = save_and_extract(b2, r["id"])
                            if t2:
                                return t2, f"pdf:{f2}"
                    except Exception:
                        pass
        except Exception:
            continue
    return None, None


m = auditlib.load_master()
for key, blk in m["papers"].items():
    todo = [r for r in blk["citing"] if r["status"] == "oa_bloqueado"]
    print(f"\n=== {key}: reprocessando {len(todo)} bloqueados ===")
    ok = 0
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(grab, r): r for r in todo}
        for f in as_completed(futs):
            r = futs[f]
            try:
                t, s = f.result()
            except Exception:
                t, s = None, None
            if t:
                (auditlib.TEXT / f"{r['id']}.txt").write_text(t)
                r["text_path"] = f"text/{r['id']}.txt"
                r["text_source"] = s
                r["status"] = "tem_texto"
                ok += 1
    print(f"   recuperados: {ok}/{len(todo)}")

auditlib.save_master(m)
import collections

tot = collections.Counter()
print("\n" + "=" * 62)
for key, blk in m["papers"].items():
    c = collections.Counter(r["status"] for r in blk["citing"])
    tot += c
    print(f"{key:>8}: " + "  ".join(f"{k}={v}" for k, v in sorted(c.items())))
print(f"{'TOTAL':>8}: " + "  ".join(f"{k}={v}" for k, v in sorted(tot.items())))
