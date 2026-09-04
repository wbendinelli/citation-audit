"""Etapa 8: varredura ampla — tenta TODA localização conhecida de TODO registro com DOI
que ainda não tem texto, inclusive os marcados como fechados (pode haver cópia verde)."""
import json, os, re, subprocess, time, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF, TXT = f"{ROOT}/pdf", f"{ROOT}/text"
CFG = json.load(open(f"{ROOT}/config.json")); MAIL = CFG["contact_email"]
H = {"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
     "Accept":"text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
     "Accept-Language":"en-US,en;q=0.9","Referer":"https://www.google.com/"}
ANTIBOT = ("wiley.com","sciencedirect.com","tandfonline.com","springer.com",
           "taylorfrancis.com","sagepub.com")

def jget(u,t=3):
    for a in range(t):
        try:
            with urllib.request.urlopen(urllib.request.Request(u,
                 headers={"Accept":"application/json","User-Agent":f"audit (mailto:{MAIL})"}),timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code==404: return None
            time.sleep(2**a)
        except Exception: time.sleep(2**a)
    return None

def fetch(u,timeout=70):
    with urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type",""), r.geturl()

def strip_html(b):
    s=b.decode("utf-8","ignore")
    s=re.sub(r"(?is)<(script|style|nav|header|footer)[^>]*>.*?</\1>"," ",s)
    s=re.sub(r"(?s)<[^>]+>"," ",s)
    for a,c in [("&nbsp;"," "),("&amp;","&"),("&lt;","<"),("&gt;",">"),("&quot;",'"'),("&#39;","'")]: s=s.replace(a,c)
    return re.sub(r"[ \t]+"," ",s)

def pdftext(b,rid):
    p=f"{PDF}/{rid}.pdf"; open(p,"wb").write(b)
    try:
        o=subprocess.run(["pdftotext","-q","-enc","UTF-8",p,"-"],capture_output=True,timeout=150)
        t=o.stdout.decode("utf-8","ignore"); return t if len(t)>2500 else None
    except Exception: return None

def routes(doi):
    w=jget(f"https://api.openalex.org/works/https://doi.org/{urllib.parse.quote(doi)}?mailto={MAIL}")
    urls=[]
    if w:
        for L in (w.get("locations") or []):
            src=((L.get("source") or {}).get("display_name") or "").lower()
            repo = (L.get("is_accepted") or L.get("version")=="submittedVersion"
                    or any(k in src for k in ("repositor","arxiv","hal","ssrn","preprint","scielo","redalyc")))
            if L.get("pdf_url"):          urls.append((0 if repo else 2, L["pdf_url"]))
            if L.get("landing_page_url"): urls.append((1 if repo else 3, L["landing_page_url"]))
        pmc=((w.get("ids") or {}).get("pmcid") or "").rsplit("/",1)[-1]
        if pmc: urls.append((0,f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmc}/fullTextXML"))
    up=jget(f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={MAIL}")
    for loc in ((up or {}).get("oa_locations") or []):
        if loc.get("url_for_pdf"): urls.append((0 if loc.get("host_type")=="repository" else 2, loc["url_for_pdf"]))
        elif loc.get("url"):       urls.append((1 if loc.get("host_type")=="repository" else 3, loc["url"]))
    seen=set(); out=[]
    for r,u in sorted(urls):
        if u and u not in seen and not any(b in u for b in ANTIBOT):
            seen.add(u); out.append(u)
    return out

def grab(rec):
    for u in routes(rec["doi"]):
        try:
            body,ctype,final=fetch(u)
            if body[:4]==b"%PDF" or "pdf" in ctype.lower():
                t=pdftext(body,rec["id"])
                if t: return t,f"pdf:{final}"
            else:
                t=strip_html(body)
                if len(t)>2500: return t,f"html:{final}"
                for href in re.findall(r'href="([^"]+\.pdf[^"]*)"', body.decode("utf-8","ignore"))[:3]:
                    try:
                        b2,c2,f2=fetch(urllib.parse.urljoin(final,href))
                        if b2[:4]==b"%PDF":
                            t2=pdftext(b2,rec["id"])
                            if t2: return t2,f"pdf:{f2}"
                    except Exception: pass
        except Exception: continue
    return None,None

M=json.load(open(f"{ROOT}/data/master.json"))
todo=[r for k,b in M.items() for r in b["citing"]
      if r["status"]!="tem_texto" and r.get("doi")]
print(f"varrendo {len(todo)} registros com DOI e sem texto...")
ok=0
with ThreadPoolExecutor(max_workers=6) as ex:
    futs={ex.submit(grab,r):r for r in todo}
    for i,f in enumerate(as_completed(futs),1):
        r=futs[f]
        try: t,s=f.result()
        except Exception: t,s=None,None
        if t:
            open(f"{TXT}/{r['id']}.txt","w").write(t)
            r["text_path"]=f"text/{r['id']}.txt"; r["text_source"]=s; r["status"]="tem_texto"; ok+=1
        if i%25==0: print(f"   ...{i}/{len(todo)} (recuperados: {ok})")
print(f"\nRECUPERADOS NESTA VARREDURA: {ok}")
json.dump(M,open(f"{ROOT}/data/master.json","w"),ensure_ascii=False,indent=1)
import collections
c=collections.Counter(r["status"] for k,b in M.items() for r in b["citing"])
print(f"inventario: {sum(len(b['citing']) for b in M.values())}")
for k,v in sorted(c.items(),key=lambda x:-x[1]): print(f"  {k:>22}: {v:>3}")
