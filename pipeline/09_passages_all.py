"""Etapa 9: localiza a passagem citante em todo texto disponível.

Duas estratégias: sobrenome no corpo (estilo autor-ano) e número da referência
seguido até as ocorrências no corpo (estilo numérico).
"""
import json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(f"{ROOT}/config.json")); SUR = CFG["author_surname"]

def clean(s): return re.sub(r"\s+"," ", s or "").strip()

def is_bib_line(w):
    """Heurística: janela que parece entrada de bibliografia, não uso no texto."""
    return (re.search(rf"{SUR},?\s*W", w) and
            len(re.findall(r"\b(19|20)\d{2}\b", w)) >= 2 and
            re.search(r"(doi|Sustain|Transport|pp\.|vol\.|\d+\s*[-–]\s*\d+)", w, re.I))

def by_name(t):
    out=[]
    for m in re.finditer(SUR, t):
        w = clean(t[max(0,m.start()-700): m.end()+700])
        if is_bib_line(w) and SUR+" et al" not in w[:250]: continue
        out.append(w)
    return out

def by_number(t):
    m = re.search(r"(?im)^\s*(references|bibliography|refer[eê]ncias|literature cited)\s*$", t)
    tail = t[m.end():] if m else t[int(len(t)*0.55):]
    body = t[:m.start()] if m else t
    num=None
    for pat in (rf"\[(\d{{1,3}})\][^\[\]]{{0,500}}?{SUR}",
                rf"(?m)^\s*(\d{{1,3}})[.)]\s+[^\n]{{0,500}}?{SUR}",
                rf"(?m)^\s*(\d{{1,3}})\s*\n[^\n]{{0,300}}?{SUR}"):
        mm = re.search(pat, tail, re.S)
        if mm: num = mm.group(1); break
    if not num: return [], None
    out=[]
    for mm in re.finditer(rf"\[[^\]\n]{{0,60}}\b{re.escape(num)}\b[^\]\n]{{0,60}}\]", body):
        out.append(clean(body[max(0,mm.start()-650): mm.end()+650]))
    return out, num

M=json.load(open(f"{ROOT}/data/master.json"))
stats={"com_texto":0,"com_passagem":0,"so_bibliografia":0,"nao_achou":0}
for key,blk in M.items():
    for r in blk["citing"]:
        p = r.get("text_path")
        if not p or not os.path.exists(f"{ROOT}/{p}"): continue
        stats["com_texto"]+=1
        t=open(f"{ROOT}/{p}",encoding="utf-8",errors="ignore").read()
        ps, how = [], []
        n = by_name(t)
        if n: ps+=n; how.append("nome")
        bn, num = by_number(t)
        if bn: ps+=bn; how.append(f"num[{num}]")
        seen=set(); ded=[]
        for x in ps:
            k=re.sub(r"\W","",x.lower())[:70]
            if k not in seen: seen.add(k); ded.append(x)
        r["passages"]=ded[:4]; r["passage_how"]=how
        if ded: stats["com_passagem"]+=1
        elif SUR in t: r["citation_status"]="bibliography_only"; stats["so_bibliografia"]+=1
        else: r["citation_status"]="not_found"; stats["nao_achou"]+=1

json.dump(M,open(f"{ROOT}/data/master.json","w"),ensure_ascii=False,indent=1)
CL=json.load(open(f"{ROOT}/data/classify.json"))
novos=[r for k,b in M.items() for r in b["citing"]
       if r.get("passages") and not CL.get((r.get("doi") or "").lower())]
print(f"com texto ............ {stats['com_texto']}")
print(f"com passagem ......... {stats['com_passagem']}")
print(f"so na bibliografia ... {stats['so_bibliografia']}")
print(f"nao encontrado ....... {stats['nao_achou']}")
print(f"\nPASSAGENS NOVAS PARA CLASSIFICAR: {len(novos)}")
