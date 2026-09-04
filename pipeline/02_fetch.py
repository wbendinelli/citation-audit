"""Fase B: baixa full text dos citantes e converte para texto puro."""
import json, os, re, subprocess, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
RAW, TXT = os.path.join(HERE,"raw"), os.path.join(HERE,"text")
MAIL = "wbendinelli@gmail.com"
UA = f"Mozilla/5.0 (compatible; citation-audit/0.1; mailto:{MAIL})"

def fetch_bytes(url, timeout=70):
    req = urllib.request.Request(url, headers={"User-Agent":UA,
        "Accept":"text/html,application/xhtml+xml,application/pdf,application/xml,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type","")

def strip_html(b):
    s = b.decode("utf-8","ignore")
    s = re.sub(r"(?is)<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    for a,b_ in [("&nbsp;"," "),("&amp;","&"),("&lt;","<"),("&gt;",">"),
                 ("&#x2013;","-"),("&quot;",'"'),("&#39;","'")]:
        s = s.replace(a,b_)
    return re.sub(r"[ \t]+"," ", s)

def europepmc_xml(url):
    m = re.search(r"(PMC\d+)", url or "")
    if not m: return None
    u = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{m.group(1)}/fullTextXML"
    b,_ = fetch_bytes(u)
    return strip_html(b)

def pdf_to_text(b, tag):
    p = os.path.join(RAW, f"{tag}.pdf")
    open(p,"wb").write(b)
    try:
        out = subprocess.run(["pdftotext","-q","-enc","UTF-8",p,"-"],
                             capture_output=True, timeout=120)
        return out.stdout.decode("utf-8","ignore")
    except Exception:
        return None

def get_text(item, key):
    tag = f"{key}_{item['n']:03d}"
    for route in item["routes"]:
        kind, url = route["kind"], route["url"]
        try:
            if kind == "europepmc":
                t = europepmc_xml(url)
                if t and len(t) > 3000: return t, f"europepmc:{url}"
                continue
            body, ctype = fetch_bytes(url)
            if b"%PDF" == body[:4] or "pdf" in ctype.lower():
                t = pdf_to_text(body, tag)
                if t and len(t) > 3000: return t, f"pdf:{url}"
            else:
                t = strip_html(body)
                if t and len(t) > 3000: return t, f"html:{url}"
        except Exception as e:
            continue
    return None, None

inv = json.load(open(os.path.join(HERE,"inventory.json")))
results = {}
for key, blk in inv.items():
    todo = [x for x in blk["citing"] if x["routes"]]
    print(f"\n[{key}] baixando {len(todo)} citantes com rota...")
    ok = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(get_text, it, key): it for it in todo}
        for f in as_completed(futs):
            it = futs[f]
            try: text, src = f.result()
            except Exception: text, src = None, None
            if text:
                p = os.path.join(TXT, f"{key}_{it['n']:03d}.txt")
                open(p,"w").write(text)
                it["text_path"], it["text_source"], it["chars"] = p, src, len(text)
                ok += 1
            else:
                it["text_path"] = None
    print(f"[{key}] full text obtido: {ok}/{len(todo)}")
    results[key] = ok

json.dump(inv, open(os.path.join(HERE,"inventory.json"),"w"), ensure_ascii=False, indent=1)
print("\ninventory.json atualizado")
