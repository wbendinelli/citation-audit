"""Fase B2: rotas alternativas (headers de browser, Europe PMC por DOI, S2 openAccessPdf)."""
import json, os, re, subprocess, urllib.request, urllib.error, time
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE=os.path.dirname(os.path.abspath(__file__)); RAW=os.path.join(HERE,"raw"); TXT=os.path.join(HERE,"text")
MAIL="wbendinelli@gmail.com"
BROWSER={"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
         "Accept":"text/html,application/xhtml+xml,application/pdf,application/xml;q=0.9,*/*;q=0.8",
         "Accept-Language":"en-US,en;q=0.9"}

def raw_get(url, timeout=70, extra=None):
    h=dict(BROWSER)
    if extra: h.update(extra)
    req=urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type",""), r.geturl()

def strip_html(b):
    s=b.decode("utf-8","ignore")
    s=re.sub(r"(?is)<(script|style|nav|header|footer)[^>]*>.*?</\1>"," ",s)
    s=re.sub(r"(?s)<[^>]+>"," ",s)
    for a,b_ in [("&nbsp;"," "),("&amp;","&"),("&lt;","<"),("&gt;",">"),("&quot;",'"'),("&#39;","'")]:
        s=s.replace(a,b_)
    return re.sub(r"[ \t]+"," ",s)

def pdf_text(b,tag):
    p=os.path.join(RAW,f"{tag}.pdf"); open(p,"wb").write(b)
    try:
        o=subprocess.run(["pdftotext","-q","-enc","UTF-8",p,"-"],capture_output=True,timeout=120)
        return o.stdout.decode("utf-8","ignore")
    except Exception: return None

def jget(u):
    try:
        req=urllib.request.Request(u,headers={"User-Agent":f"audit (mailto:{MAIL})","Accept":"application/json"})
        with urllib.request.urlopen(req,timeout=60) as r: return json.load(r)
    except Exception: return None

def candidate_urls(item):
    """Gera rotas extras alem das ja tentadas."""
    out=[]
    doi=item.get("doi") or ""
    # 1. Europe PMC por DOI (pega OA fora do PMC tambem)
    if doi:
        s=jget("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query="
               f"DOI:%22{urllib.parse.quote(doi)}%22&resultType=core&format=json")
        try:
            res=(s or {}).get("resultList",{}).get("result",[])
            for r in res[:1]:
                if r.get("pmcid"):
                    out.append(("europepmc",
                      f"https://www.ebi.ac.uk/europepmc/webservices/rest/{r['pmcid']}/fullTextXML"))
                for ft in (r.get("fullTextUrlList",{}) or {}).get("fullTextUrl",[]):
                    if ft.get("availability") in ("Open access","Free"):
                        out.append(("auto", ft.get("url")))
        except Exception: pass
    # 2. Semantic Scholar openAccessPdf
    if doi:
        s2=jget(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=openAccessPdf")
        u=((s2 or {}).get("openAccessPdf") or {}).get("url")
        if u: out.append(("auto",u))
    # 3. rotas originais de novo, com headers de browser
    for r in item.get("routes",[]): out.append(("auto", r["url"]))
    seen=set(); ded=[]
    for k,u in out:
        if u and u not in seen: seen.add(u); ded.append((k,u))
    return ded

import urllib.parse
def try_item(item,key):
    tag=f"{key}_{item['n']:03d}"
    for kind,url in candidate_urls(item):
        try:
            body,ctype,final=raw_get(url)
            if kind=="europepmc" or "xml" in ctype.lower():
                t=strip_html(body)
                if t and len(t)>3000: return t,f"europepmc:{url}"
            if body[:4]==b"%PDF" or "pdf" in ctype.lower():
                t=pdf_text(body,tag)
                if t and len(t)>3000: return t,f"pdf:{final}"
            else:
                t=strip_html(body)
                if t and len(t)>3000: return t,f"html:{final}"
        except Exception:
            continue
    return None,None

inv=json.load(open(os.path.join(HERE,"inventory.json")))
for key,blk in inv.items():
    todo=[x for x in blk["citing"] if not x.get("text_path")]
    print(f"\n[{key}] rodada 2: {len(todo)} pendentes")
    ok=0
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs={ex.submit(try_item,it,key):it for it in todo}
        for f in as_completed(futs):
            it=futs[f]
            try: t,s=f.result()
            except Exception: t,s=None,None
            if t:
                p=os.path.join(TXT,f"{key}_{it['n']:03d}.txt"); open(p,"w").write(t)
                it["text_path"],it["text_source"],it["chars"]=p,s,len(t); ok+=1
    tot=len([x for x in blk["citing"] if x.get("text_path")])
    print(f"[{key}] +{ok} nesta rodada | total com full text: {tot}/{len(blk['citing'])}")

json.dump(inv,open(os.path.join(HERE,"inventory.json"),"w"),ensure_ascii=False,indent=1)
