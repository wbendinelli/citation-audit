"""Etapa 2: baixa os citantes open access e extrai texto."""
import json, os, re, subprocess, urllib.request, urllib.error, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF, TXT = f"{ROOT}/pdf", f"{ROOT}/text"
os.makedirs(PDF, exist_ok=True); os.makedirs(TXT, exist_ok=True)
H = {"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
     "Accept":"text/html,application/xhtml+xml,application/pdf,application/xml;q=0.9,*/*;q=0.8",
     "Accept-Language":"en-US,en;q=0.9","Referer":"https://scholar.google.com/"}

def fetch(url, timeout=75):
    with urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type",""), r.geturl()

def strip_html(b):
    s = b.decode("utf-8","ignore")
    s = re.sub(r"(?is)<(script|style|nav|header|footer)[^>]*>.*?</\1>"," ",s)
    s = re.sub(r"(?s)<[^>]+>"," ",s)
    for a,c in [("&nbsp;"," "),("&amp;","&"),("&lt;","<"),("&gt;",">"),("&quot;",'"'),("&#39;","'")]:
        s = s.replace(a,c)
    return re.sub(r"[ \t]+"," ",s)

def pdf_text(b, rid):
    p = f"{PDF}/{rid}.pdf"; open(p,"wb").write(b)
    try:
        o = subprocess.run(["pdftotext","-q","-enc","UTF-8",p,"-"],capture_output=True,timeout=150)
        t = o.stdout.decode("utf-8","ignore")
        return t if len(t) > 2500 else None
    except Exception: return None

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
                t = pdf_text(body, rid)
                if t: return t, f"pdf:{final}"
            else:
                t = strip_html(body)
                if len(t) > 2500: return t, f"{'xml' if 'xml' in ctype.lower() else 'html'}:{final}"
        except Exception:
            continue
    return None, None

master = json.load(open(f"{ROOT}/data/master.json"))
for key, blk in master.items():
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
                open(f"{TXT}/{r['id']}.txt","w").write(t)
                r["text_path"] = f"text/{r['id']}.txt"; r["text_source"] = s
                r["status"] = "tem_texto"; ok += 1
            else:
                r["status"] = "oa_bloqueado"
    print(f"   obtidos: {ok}/{len(todo)}")

# reindexa os que ja tinham texto da rodada antiga
old = json.load(open(f"{ROOT}/data/inventory.json"))
oldmap = {}
for k,b in old.items():
    for it in b["citing"]:
        if it.get("text_path") and it.get("doi"):
            oldmap[it["doi"].lower()] = it["text_path"]
import shutil
for key, blk in master.items():
    for r in blk["citing"]:
        if r.get("text_path"): continue
        p = oldmap.get((r.get("doi") or "").lower())
        if p and os.path.exists(f"{ROOT}/{p}"):
            dest = f"{TXT}/{r['id']}.txt"
            if not os.path.exists(dest): shutil.copy(f"{ROOT}/{p}", dest)
            r["text_path"] = f"text/{r['id']}.txt"; r["status"] = "tem_texto"

json.dump(master, open(f"{ROOT}/data/master.json","w"), ensure_ascii=False, indent=1)
import collections
print("\n" + "="*60)
tot = collections.Counter()
for key, blk in master.items():
    c = collections.Counter(r["status"] for r in blk["citing"]); tot += c
    print(f"{key:>8}: " + "  ".join(f"{k}={v}" for k,v in sorted(c.items())))
print(f"{'TOTAL':>8}: " + "  ".join(f"{k}={v}" for k,v in sorted(tot.items())))
