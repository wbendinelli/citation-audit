"""Fase C: localiza a passagem onde Bendinelli et al. e citado.
Fontes: (a) full text baixado, (b) contexts do Semantic Scholar."""
import json, os, re, time, urllib.request

HERE=os.path.dirname(os.path.abspath(__file__))
MAIL="wbendinelli@gmail.com"
TARGET_DOI={"grains":"10.1016/j.spc.2019.09.002","airline":"10.1016/j.tra.2016.01.001"}
TARGET_YEAR={"grains":("2019","2020"),"airline":("2016",)}

def jget(u,tries=5):
    for a in range(tries):
        try:
            r=urllib.request.Request(u,headers={"Accept":"application/json",
                "User-Agent":f"audit (mailto:{MAIL})"})
            with urllib.request.urlopen(r,timeout=90) as x: return json.load(x)
        except Exception: time.sleep(min(20,2**a))
    return None

def clean(s):
    s=re.sub(r"\s+"," ",s or "").strip()
    return s

def find_by_name(text, years):
    """Passagens com 'Bendinelli' no corpo (estilo autor-ano)."""
    out=[]
    for m in re.finditer(r"Bendinelli", text):
        a=max(0,m.start()-700); b=min(len(text), m.end()+700)
        win=clean(text[a:b])
        # descarta se parece linha de bibliografia
        if re.search(r"Bendinelli,?\s*W", win) and re.search(r"(doi|Transport|Sustainable Production)", win) \
           and len(re.findall(r"\b(19|20)\d{2}\b", win))>2 and "et al" not in win[:200]:
            continue
        out.append(win)
    return out

def find_by_number(text, years):
    """Estilo numerico: acha a entrada [N] da bibliografia com Bendinelli e busca [N] no corpo."""
    out=[]
    m=re.search(r"(?i)\n\s*(references|bibliography|referências)\s*\n", text)
    tail = text[m.end():] if m else text[int(len(text)*0.6):]
    num=None
    for pat in (r"\[(\d{1,3})\][^\[\]]{0,400}?Bendinelli",
                r"(?m)^\s*(\d{1,3})[.)]\s+[^\n]{0,400}?Bendinelli"):
        mm=re.search(pat, tail, re.S)
        if mm: num=mm.group(1); break
    if not num: return out, None
    body = text[:m.start()] if m else text
    for mm in re.finditer(rf"\[[^\]]*\b{re.escape(num)}\b[^\]]*\]", body):
        a=max(0,mm.start()-700); b=min(len(body), mm.end()+700)
        out.append(clean(body[a:b]))
    return out, num

inv=json.load(open(os.path.join(HERE,"inventory.json")))

# --- contexts do Semantic Scholar (indexado por DOI do citante) ---
s2ctx={}
for key,doi in TARGET_DOI.items():
    s2ctx[key]={}
    off=0
    while True:
        p=jget(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}/citations"
               f"?fields=contexts,intents,isInfluential,externalIds,title&limit=1000&offset={off}")
        if not p: break
        for e in p.get("data",[]):
            cp=e.get("citingPaper") or {}
            d=((cp.get("externalIds") or {}).get("DOI") or "").lower()
            if d:
                s2ctx[key][d]={"contexts":[clean(c) for c in (e.get("contexts") or [])],
                               "intents":e.get("intents") or [],
                               "isInfluential":bool(e.get("isInfluential"))}
        if len(p.get("data",[]))<1000: break
        off+=1000
    print(f"[{key}] S2 contexts para {sum(1 for v in s2ctx[key].values() if v['contexts'])} citantes")

stats={}
for key,blk in inv.items():
    n_ft=n_pass=0
    for it in blk["citing"]:
        passages=[]; how=[]
        if it.get("text_path") and os.path.exists(it["text_path"]):
            n_ft+=1
            txt=open(it["text_path"],encoding="utf-8",errors="ignore").read()
            byname=find_by_name(txt, TARGET_YEAR[key])
            bynum,num=find_by_number(txt, TARGET_YEAR[key])
            if byname: passages+=byname; how.append("fulltext:name")
            if bynum:  passages+=bynum;  how.append(f"fulltext:num[{num}]")
            if not passages and "Bendinelli" in txt:
                how.append("fulltext:bibliography_only")
            elif not passages:
                how.append("fulltext:not_found")
        d=(it.get("doi") or "").lower()
        s2=s2ctx.get(key,{}).get(d)
        if s2:
            it["s2_intents"]=s2["intents"]; it["s2_influential"]=s2["isInfluential"]
            if s2["contexts"]:
                passages+=s2["contexts"]; how.append("s2:contexts")
        # dedup por prefixo
        seen=set(); ded=[]
        for p in passages:
            k=p[:120].lower()
            if k not in seen: seen.add(k); ded.append(p)
        it["passages"]=ded[:6]; it["passage_source"]=how
        if ded: n_pass+=1
    stats[key]=(n_ft,n_pass,len(blk["citing"]))

json.dump(inv,open(os.path.join(HERE,"inventory.json"),"w"),ensure_ascii=False,indent=1)
print("\n"+"="*70)
for k,(ft,ps,tot) in stats.items():
    print(f"{k:>8}: {tot} citantes | {ft} com full text | {ps} COM PASSAGEM CLASSIFICAVEL ({100*ps/tot:.0f}%)")
