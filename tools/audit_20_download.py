"""Etapa 20: baixa os citantes open access e extrai texto."""
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import auditlib

auditlib.PDF.mkdir(exist_ok=True)
auditlib.TEXT.mkdir(exist_ok=True)

H = {"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
     "Accept":"text/html,application/xhtml+xml,application/pdf,application/xml;q=0.9,*/*;q=0.8",
     "Accept-Language":"en-US,en;q=0.9","Referer":"https://scholar.google.com/"}

def fetch(url, timeout=75):
    with urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type",""), r.geturl()

def save_and_extract(body, rid):
    p = auditlib.PDF / f"{rid}.pdf"
    p.write_bytes(body)
    return auditlib.pdftext(p)

def routes(r):
    u = []
    if r.get("pmcid"):
        u.append(f"https://www.ebi.ac.uk/europepmc/webservices/rest/{r['pmcid']}/fullTextXML")
    if r.get("arxiv"):
        u.append(f"https://arxiv.org/pdf/{r['arxiv']}")
    if r.get("pdf"):  u.append(r["pdf"])
    if r.get("oa_landing"): u.append(r["oa_landing"])
    if r.get("landing"):    u.append(r["landing"])
    seen=set(); return [x for x in u if x and not (x in seen or seen.add(x))]

def grab(r):
    rid = r["id"]
    for url in routes(r):
        try:
            body, ctype, final = fetch(url)
            if body[:4] == b"%PDF" or "pdf" in ctype.lower():
                t = save_and_extract(body, rid)
                if t: return t, f"pdf:{final}"
            else:
                t = auditlib.strip_html(body)
                if len(t) > 2500: return t, f"{'xml' if 'xml' in ctype.lower() else 'html'}:{final}"
        except Exception:
            continue
    return None, None

master = auditlib.load_master()
for key, blk in master["papers"].items():
    todo = [r for r in blk["citing"] if r["status"] in ("oa_baixavel","oa_sem_pdf_direto")]
    print(f"\n=== {key}: baixando {len(todo)} ===")
    ok = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(grab, r): r for r in todo}
        for f in as_completed(futs):
            r = futs[f]
            try: t, s = f.result()
            except Exception: t, s = None, None
            if t:
                (auditlib.TEXT / f"{r['id']}.txt").write_text(t)
                r["text_path"] = f"text/{r['id']}.txt"; r["text_source"] = s
                r["status"] = "tem_texto"; ok += 1
            else:
                r["status"] = "oa_bloqueado"
    print(f"   obtidos: {ok}/{len(todo)}")

auditlib.save_master(master)
import collections
print("\n" + "="*60)
tot = collections.Counter()
for key, blk in master["papers"].items():
    c = collections.Counter(r["status"] for r in blk["citing"]); tot += c
    print(f"{key:>8}: " + "  ".join(f"{k}={v}" for k,v in sorted(c.items())))
print(f"{'TOTAL':>8}: " + "  ".join(f"{k}={v}" for k,v in sorted(tot.items())))
