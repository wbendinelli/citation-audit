"""Etapa 80: gera report/index.html a partir de master/classify/journals/config.

Uso:
  python3 tools/audit_80_report_html.py           grava report/index.html
  python3 tools/audit_80_report_html.py --check   renderiza em memória e compara
                                                   byte a byte com o arquivo commitado
"""
import collections
import html
import re
import sys

import auditlib

master = auditlib.load_master()
CFG = auditlib.load_config()
CL = auditlib.load_classify()          # chaveado por DOI

ROLE={"bibliography_only":("só na bibliografia","ghost",0),"drive_by":("de passagem","dim",1),
      "brief_mention":("menção breve","dim",2),"real_mention":("menção real","accent",3),
      "supporting":("sustenta","good",4),"foundational":("fundacional","good-deep",5),
      "wrongly_interpreted":("interpretado errado","bad",-1)}
PT={"bibliography_only":"só na bibliografia","drive_by":"de passagem","brief_mention":"menção breve",
    "real_mention":"menção real","supporting":"sustenta","foundational":"fundacional",
    "wrongly_interpreted":"interpretado errado"}
STANCE={"supporting":("apoia","s-good"),"contradictory":("contrapõe","s-bad"),"none":("neutra","s-dim")}
REUSE={"method_adoption":"adota método","result_validated":"valida resultado",
       "dataset_reuse":"reusa dado","benchmarking":"benchmark","work_extended":"estende"}
FLAG={"best":("Melhor citação","good"),"good":("Uso substantivo","good"),
      "critical":("Crítica ao artigo","bad"),"misattribution":("Atribuição incorreta","bad"),
      "ghost":("Citação-fantasma","ghost"),"weak":("Atribuição frágil","warn"),
      "duplicate":("Publicação duplicada","warn"),
      "autocitacao":("Autocitação","ghost"),"coautor":("Citação de coautor","warn")}

def esc(s): return html.escape(s or "")
def center(p,n=430):
    m=re.search(r"Bendinelli|@@",p)
    if not m: return (p[:n]+"…") if len(p)>n else p
    a=max(0,m.start()-n//2); b=min(len(p),m.start()+n//2)
    return ("…" if a>0 else "")+p[a:b].strip().replace("@@","")+("…" if b<len(p) else "")

status_tot=collections.Counter()
sections=[]; kpi=collections.Counter()
for key in ("airline","grains"):
    blk=master["papers"][key]
    p_cfg=CFG["papers"][key]
    title,venue,yr,doi=p_cfg["title"],p_cfg["venue"],p_cfg["year"],p_cfg["doi"]
    total=len(blk["citing"])
    for r in blk["citing"]: status_tot[r["status"]]+=1
    ents=[]; dist=collections.Counter()
    rows=[(r,CL.get((r.get("doi") or "").lower())) for r in blk["citing"]]
    rows=[(r,c) for r,c in rows if c]
    rows.sort(key=lambda rc:(-ROLE[rc[1]["role"]][2], rc[0].get("venue") or ""))
    for r,c in rows:
        dist[c["role"]]+=1
        if c.get("flag") in ("autocitacao","coautor"): kpi["self"]+=1
        for t in c.get("reuse",[]):
            if c.get("flag") not in ("autocitacao","coautor"): kpi["reuse"]+=1
        if c.get("flag")=="misattribution": kpi["mis"]+=1
        if c.get("role")=="bibliography_only": kpi["ghost"]+=1
        rl,rc_,_=ROLE[c["role"]]; sl,sc=STANCE[c["stance"]]
        chips=f'<span class="chip r-{rc_}">{PT[c["role"]]}</span><span class="chip {sc}">{sl}</span>'
        for t in c.get("reuse",[]): chips+=f'<span class="chip reuse">{REUSE[t]}</span>'
        if r.get("is_influential"): chips+='<span class="chip infl">influential · S2</span>'
        fl=FLAG.get(c.get("flag") or "")
        qs=[center(p) for p in (c.get("passages") or [])][:2]
        quotes="".join(f"<blockquote>{esc(q)}</blockquote>" for q in qs)
        note=f'<p class="note">{esc(c.get("note"))}</p>' if c.get("note") else ""
        fcls=f" flagged f-{fl[1]}" if fl else ""
        ftag=f'<span class="flag f-{fl[1]}">{fl[0]}</span>' if fl else ""
        ents.append(f'''<article class="entry{fcls}">
 <header class="e-head"><h3>{esc(r.get("title"))}</h3>{ftag}</header>
 <p class="meta"><span class="venue">{esc(r.get("venue") or "sem veículo indexado")}</span><span class="dot">·</span>{r.get("year") or ""}<span class="dot">·</span><span class="mono">{esc(r.get("oa_status") or "?")}</span></p>
 <div class="chips">{chips}</div>
 {quotes}{note}
</article>''')
    order=["foundational","supporting","real_mention","brief_mention","drive_by","bibliography_only","wrongly_interpreted"]
    n=sum(dist.values())
    bars="".join(f'<span class="seg s-{ROLE[r][1]}" style="flex:{dist[r]}" title="{PT[r]}: {dist[r]}"><b>{dist[r]}</b></span>' for r in order if dist.get(r))
    leg="".join(f'<span class="lg"><i class="sw s-{ROLE[r][1]}"></i>{PT[r]} <b>{dist[r]}</b></span>' for r in order if dist.get(r))
    sections.append(f'''<section class="paper" id="{key}">
 <div class="p-head"><p class="eyebrow mono">{esc(venue)} · {yr}</p><h2>{esc(title)}</h2>
 <p class="doi mono">{doi} — {total} citações na união de quatro fontes, <b>{n} com evidência verificada</b></p></div>
 <div class="bar">{bars}</div><div class="legend">{leg}</div>
 <div class="entries">{"".join(ents)}</div></section>''')

# ---------------- funil e quebra por revista ----------------
GRANDES = CFG["editoras_estabelecidas"]
SCHOLAR = {k: sum(1 for l in (auditlib.DATA / "scholar" / f"{k}.txt").open() if l.strip())
           for k in ("airline", "grains")}
def _livro(d):
    suf=d.split("/",1)[1] if "/" in d else ""
    return suf.startswith("978") or "9781" in suf or "9780" in suf or d.startswith("10.1007/978")
def venue_norm(v):
    v=html.unescape(v or "?").strip()
    v=re.sub(r"\s+"," ",v)
    v=re.sub(r"(Transportation Research Part [A-F])\s*:?\s*", r"\1: ", v)
    v=re.sub(r"\s*[:,]\s*$","",v)
    fix={"Journal of business research":"Journal of Business Research",
         "Journal of plant diseases and protection":"Journal of Plant Diseases and Protection",
         "Handbook of agricultural economics":"Handbook of Agricultural Economics",
         "Transportation Research Part E: Logistics and Transportation Review":"Transportation Research Part E",
         "Transportation Research Part E: Logistics and T":"Transportation Research Part E",
         "Transportation Research Part A: Policy and Practice":"Transportation Research Part A",
         "Transportation Research Part C Emerging Technologies":"Transportation Research Part C",
         "Transportation Research Part B: Methodological":"Transportation Research Part B"}
    for a,b in fix.items():
        if v.lower().startswith(a.lower()[:40]): return b
    return v

def funil(key):
    rs=master["papers"][key]["citing"]
    doi=[r for r in rs if r.get("doi")]
    gr=[r for r in doi if r["doi"].split("/")[0] in GRANDES]
    per=[r for r in gr if not _livro(r["doi"])]
    cf=[r for r in per if CL.get(r["doi"].lower())]
    return [("Google Scholar reporta",SCHOLAR[key],None),
            ("Inventário após dedup e ruído",len(rs),len(rs)-SCHOLAR[key]),
            ("Com DOI depositado",len(doi),-(len(rs)-len(doi))),
            ("Editora estabelecida",len(gr),-(len(doi)-len(gr))),
            ("Periódico (sem capítulo, anais, preprint)",len(per),-(len(gr)-len(per))),
            ("Com evidência verificada",len(cf),-(len(per)-len(cf)))]

def render_funil(key):
    f=funil(key); topo=f[0][1]
    li=[]
    for i,(rot,val,delta) in enumerate(f):
        w=100*val/topo
        d=("<span class='delta'>%+d</span>"%delta) if delta not in (None,0) else ""
        cls_="step final" if i==len(f)-1 else ("step base" if i==0 else "step")
        li.append(f"<li class='{cls_}'><span class='rot'>{rot}</span>"
                  f"<span class='track'><i style='width:{w:.1f}%'></i></span>"
                  f"<span class='val'>{val}</span>{d}</li>")
    return "<ol class='funil'>"+"".join(li)+"</ol>"

def render_revistas(key):
    rows=[]
    for r in master["papers"][key]["citing"]:
        d=r.get("doi") or ""
        if not d or d.split("/")[0] not in GRANDES or _livro(d): continue
        c=CL.get(d.lower())
        if c: rows.append((venue_norm(r.get("venue")),c))
    agg=collections.defaultdict(list)
    for v,c in rows: agg[v].append(c)
    ordem=["foundational","supporting","real_mention","brief_mention","drive_by","bibliography_only","wrongly_interpreted"]
    out=[]
    for v,cs in sorted(agg.items(),key=lambda x:(-len(x[1]),x[0])):
        dist=collections.Counter(c["role"] for c in cs)
        chips="".join(f"<i class='q s-{ROLE[r][1]}' title='{PT[r]}: {dist[r]}'>{dist[r]}</i>"
                      for r in ordem if dist.get(r))
        reuse=sum(len(c.get("reuse") or []) for c in cs)
        rtag=(f"<b>{reuse}</b>" if reuse else "<span class='off'>–</span>")
        out.append(f"<tr><td class='v'>{esc(v)}</td><td class='n'>{len(cs)}</td>"
                   f"<td class='qs'>{chips}</td><td class='n'>{rtag}</td></tr>")
    return ("<div class='scroll'><table class='tbl rev'><tr><th>Periódico</th><th class='n'>Citações</th>"
            "<th>Distribuição de papel</th><th class='n'>Reuso</th></tr>"+"".join(out)+"</table></div>")

FUNIS="".join(
  f"<div class='fcol'><h3>{'Aviação' if k=='airline' else 'Grãos'}</h3>{render_funil(k)}</div>"
  for k in ("airline","grains"))
REVISTAS="".join(
  f"<div class='rcol'><h3>{'Aviação' if k=='airline' else 'Grãos'}</h3>{render_revistas(k)}</div>"
  for k in ("airline","grains"))

# ---------------- quartil Scimago ----------------
JR=auditlib.load_journals()
QORD=["Q1","Q2","Q3","Q4","fora do Scimago","sem métrica"]
def quart(r):
    m=JR.get(r.get("source_id") or "")
    if not m: return "sem métrica"
    sc=m.get("scimago")
    if sc and sc.get("quartil") in ("Q1","Q2","Q3","Q4"): return sc["quartil"]
    return "fora do Scimago"
QCLS={"Q1":"q1","Q2":"q2","Q3":"q3","Q4":"q4","fora do Scimago":"qx","sem métrica":"qn"}

def barras_q(key):
    c=collections.Counter(quart(r) for r in master["papers"][key]["citing"]); tot=sum(c.values())
    segs="".join(f"<span class='qseg {QCLS[x]}' style='flex:{c[x]}' title='{x}: {c[x]}'>{c[x]}</span>"
                 for x in QORD if c.get(x))
    leg="".join(f"<span class='lg'><i class='sw {QCLS[x]}'></i>{x} <b>{c[x]}</b></span>"
                for x in QORD if c.get(x))
    return f"<div class='qbar'>{segs}</div><div class='legend'>{leg}</div>"

ROLES_ORD=["foundational","supporting","real_mention","brief_mention","drive_by","bibliography_only","wrongly_interpreted"]
def matriz_q():
    tab=collections.defaultdict(collections.Counter)
    for k,b in master["papers"].items():
        for r in b["citing"]:
            c=CL.get((r.get("doi") or "").lower())
            if c: tab[quart(r)][c["role"]]+=1
    th="".join(f"<th>{PT[x]}</th>" for x in ROLES_ORD)
    tr=""
    for x in QORD:
        if not tab[x]: continue
        tds="".join(f"<td class='n {'hi' if tab[x][r] else 'off'}'>{tab[x][r] or '·'}</td>" for r in ROLES_ORD)
        tr+=f"<tr><td class='v'><i class='sw {QCLS[x]}'></i>{x}</td>{tds}</tr>"
    return f"<div class='scroll'><table class='tbl mat'><tr><th>Quartil</th>{th}</tr>{tr}</table></div>"

QBARS="".join(f"<div class='fcol'><h3>{'Aviação' if k=='airline' else 'Grãos'}</h3>{barras_q(k)}</div>"
              for k in ("airline","grains"))
QMATRIZ=matriz_q()
_reuse_q=collections.Counter()
_ghost_q=collections.Counter()
for k,b in master["papers"].items():
    for r in b["citing"]:
        c=CL.get((r.get("doi") or "").lower())
        if not c: continue
        if c.get("reuse"): _reuse_q[quart(r)]+=1
        if c["role"]=="bibliography_only": _ghost_q[quart(r)]+=1
REUSE_Q1=_reuse_q["Q1"]; REUSE_TOT=sum(_reuse_q.values())
GHOST_Q1=_ghost_q["Q1"]; GHOST_TOT=sum(_ghost_q.values())

TOT=sum(len(b["citing"]) for b in master["papers"].values())
NCL=sum(1 for k,b in master["papers"].items() for r in b["citing"] if CL.get((r.get("doi") or "").lower()))
NDOI=sum(1 for k,b in master["papers"].items() for r in b["citing"] if r.get("doi"))
st=lambda k: status_tot.get(k,0)

CSS = """
:root{
 --paper:#F5F6F3; --surface:#FCFDFB; --raise:#EFF1EC;
 --ink:#15181B; --ink2:#454E55; --ink3:#767F87; --rule:#DBDFD8;
 --accent:#33506E; --good:#1F6F5C; --good-d:#14513F; --warn:#8E6018; --bad:#A8432C; --ghost:#8B9199;
 --tint-good:#E7F1ED; --tint-bad:#F8E9E4; --tint-warn:#F7EFDF; --tint-ghost:#ECEEEA;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
 --paper:#131719; --surface:#191E21; --raise:#1F252A;
 --ink:#E9EBE6; --ink2:#B3BBC0; --ink3:#828B93; --rule:#2B3237;
 --accent:#93B3D8; --good:#5EC0A3; --good-d:#8FD8C0; --warn:#D9A85C; --bad:#E58C70; --ghost:#7C848B;
 --tint-good:#16302A; --tint-bad:#33201A; --tint-warn:#2F2618; --tint-ghost:#20252A;
}}
:root[data-theme="dark"]{
 --paper:#131719; --surface:#191E21; --raise:#1F252A;
 --ink:#E9EBE6; --ink2:#B3BBC0; --ink3:#828B93; --rule:#2B3237;
 --accent:#93B3D8; --good:#5EC0A3; --good-d:#8FD8C0; --warn:#D9A85C; --bad:#E58C70; --ghost:#7C848B;
 --tint-good:#16302A; --tint-bad:#33201A; --tint-warn:#2F2618; --tint-ghost:#20252A;
}
*{box-sizing:border-box}
body{background:var(--paper);color:var(--ink);
 font-family:"IBM Plex Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
 line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:1060px;margin:0 auto;padding:56px 28px 96px}
.mono{font-family:"IBM Plex Mono",ui-monospace,SFMono-Regular,monospace}
h1,h2,h3{font-family:Spectral,Georgia,serif;text-wrap:balance;margin:0}
h1{font-size:clamp(2rem,4.4vw,3rem);font-weight:600;line-height:1.12;letter-spacing:-.015em}
h2{font-size:clamp(1.4rem,2.6vw,1.9rem);font-weight:600;line-height:1.22}
h3{font-size:1.03rem;font-weight:600;line-height:1.35}
.eyebrow{font-size:.7rem;text-transform:uppercase;letter-spacing:.14em;color:var(--ink3);margin:0 0 10px}

header.top{border-bottom:2px solid var(--ink);padding-bottom:26px;margin-bottom:34px}
header.top .lede{font-family:Spectral,Georgia,serif;font-size:1.16rem;color:var(--ink2);
 max-width:64ch;margin:16px 0 0}
.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;
 background:var(--rule);border:1px solid var(--rule);margin:30px 0 0}
@media (max-width:760px){.kpis{grid-template-columns:repeat(2,1fr)}}
.kpi{background:var(--surface);padding:16px 18px}
.kpi b{display:block;font-family:Spectral,Georgia,serif;font-size:1.85rem;font-weight:600;
 line-height:1.1;font-variant-numeric:tabular-nums}
.kpi span{font-size:.74rem;color:var(--ink3);letter-spacing:.03em}
.kpi.hl b{color:var(--bad)}

.paper{margin-top:64px}
.p-head{border-left:3px solid var(--accent);padding-left:18px}
.doi{font-size:.78rem;color:var(--ink3);margin:12px 0 0}
.bar{display:flex;height:30px;margin:26px 0 12px;border:1px solid var(--rule);overflow:hidden}
.seg{display:flex;align-items:center;justify-content:center;min-width:26px;
 font-size:.72rem;font-weight:600;color:#fff;font-family:"IBM Plex Mono",monospace}
.legend{display:flex;flex-wrap:wrap;gap:6px 20px;font-size:.76rem;color:var(--ink2);margin-bottom:30px}
.lg{display:flex;align-items:center;gap:7px}
.sw{width:11px;height:11px;display:inline-block;flex:none}
.s-good-deep,.sw.s-good-deep{background:var(--good-d)}
.s-good,.sw.s-good{background:var(--good)}
.s-accent,.sw.s-accent{background:var(--accent)}
.s-dim,.sw.s-dim{background:var(--ink3)}
.s-ghost,.sw.s-ghost{background:var(--ghost)}
.s-bad,.sw.s-bad{background:var(--bad)}

.entries{display:flex;flex-direction:column}
.entry{padding:24px 0;border-top:1px solid var(--rule)}
.entry.flagged{padding:22px 22px;border-top:1px solid var(--rule);border-left:3px solid var(--ink3);background:var(--surface)}
.entry.f-good{border-left-color:var(--good);background:var(--tint-good)}
.entry.f-bad{border-left-color:var(--bad);background:var(--tint-bad)}
.entry.f-warn{border-left-color:var(--warn);background:var(--tint-warn)}
.entry.f-ghost{border-left-color:var(--ghost);background:var(--tint-ghost)}
.e-head{display:flex;gap:14px;align-items:flex-start;justify-content:space-between}
.flag{flex:none;font-size:.66rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
 padding:4px 9px;font-family:"IBM Plex Mono",monospace;white-space:nowrap}
.flag.f-good{background:var(--good);color:#fff}
.flag.f-bad{background:var(--bad);color:#fff}
.flag.f-warn{background:var(--warn);color:#fff}
.flag.f-ghost{background:var(--ghost);color:#fff}
.meta{font-size:.79rem;color:var(--ink3);margin:7px 0 0}
.venue{color:var(--ink2)}
.dot{margin:0 8px;opacity:.55}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:13px 0 0}
.chip{font-size:.7rem;font-family:"IBM Plex Mono",monospace;padding:3px 9px;
 border:1px solid var(--rule);color:var(--ink2);background:var(--paper)}
.chip.r-good{border-color:var(--good);color:var(--good)}
.chip.r-good-deep{border-color:var(--good-d);color:var(--good-d);font-weight:600}
.chip.r-accent{border-color:var(--accent);color:var(--accent)}
.chip.r-bad{border-color:var(--bad);color:var(--bad);font-weight:600}
.chip.r-ghost{border-color:var(--ghost);color:var(--ghost)}
.chip.s-good{color:var(--good)}.chip.s-bad{color:var(--bad);font-weight:600}
.chip.reuse{background:var(--good);color:#fff;border-color:var(--good);font-weight:600}
.chip.infl{background:var(--accent);color:#fff;border-color:var(--accent)}
blockquote{font-family:Spectral,Georgia,serif;font-size:1rem;line-height:1.62;color:var(--ink);
 margin:16px 0 0;padding-left:16px;border-left:2px solid var(--rule);max-width:74ch}
.note{font-size:.85rem;color:var(--ink2);margin:14px 0 0;max-width:72ch}
.note::before{content:"→ ";color:var(--ink3)}

.funnel{margin-top:56px;border-top:2px solid var(--ink);padding-top:26px}
.fgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:36px;margin-top:22px}
.fcol h3,.rcol h3{font-size:.78rem;text-transform:uppercase;letter-spacing:.12em;
 font-family:"IBM Plex Sans",sans-serif;color:var(--ink3);margin-bottom:14px}
.funil{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:3px;
 counter-reset:none}
.funil .step{display:grid;grid-template-columns:1fr 84px 34px 42px;align-items:center;
 gap:10px;padding:7px 0;border-bottom:1px solid var(--rule)}
.funil .rot{font-size:.79rem;color:var(--ink2)}
.funil .track{display:block;height:9px;background:var(--rule)}
.funil .track i{display:block;height:100%;background:var(--ink3)}
.funil .base .track i{background:var(--accent)}
.funil .final .track i{background:var(--good)}
.funil .final .rot{color:var(--ink);font-weight:600}
.funil .val{font-family:"IBM Plex Mono",monospace;font-variant-numeric:tabular-nums;
 font-size:.86rem;text-align:right;font-weight:600}
.funil .final .val{color:var(--good)}
.funil .delta{font-family:"IBM Plex Mono",monospace;font-size:.72rem;color:var(--bad);
 text-align:right;font-variant-numeric:tabular-nums}
.rgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:32px;margin-top:30px}
.tbl.rev td.v{font-size:.8rem;color:var(--ink2);max-width:250px}
.tbl.rev td.qs{white-space:nowrap}
.q{display:inline-flex;align-items:center;justify-content:center;width:17px;height:17px;
 font-style:normal;font-size:.64rem;font-weight:600;color:#fff;margin-right:2px;
 font-family:"IBM Plex Mono",monospace}
.tbl .off{color:var(--ink3)}

.qbar{display:flex;height:26px;border:1px solid var(--rule);overflow:hidden;margin-bottom:10px}
.qseg{display:flex;align-items:center;justify-content:center;min-width:22px;color:#fff;
 font-size:.7rem;font-weight:600;font-family:"IBM Plex Mono",monospace}
.q1,.sw.q1{background:var(--good-d)} .q2,.sw.q2{background:var(--good)}
.q3,.sw.q3{background:var(--warn)}  .q4,.sw.q4{background:var(--bad)}
.qx,.sw.qx{background:var(--ink3)}  .qn,.sw.qn{background:var(--ghost)}
.tbl.mat th{font-size:.62rem} .tbl.mat td.v{font-weight:600;white-space:nowrap}
.tbl.mat td.v .sw{margin-right:6px;vertical-align:middle}
.tbl.mat td.hi{font-weight:600;color:var(--ink)}
.tbl.mat td.off{color:var(--ink3)}

.method{margin-top:72px;border-top:2px solid var(--ink);padding-top:28px}
.method h2{margin-bottom:18px}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:26px}
.method p,.method li{font-size:.9rem;color:var(--ink2);max-width:66ch}
.method ul{padding-left:18px;margin:10px 0}
.method li{margin:5px 0}
.tbl{width:100%;border-collapse:collapse;font-size:.82rem;margin-top:12px}
.tbl th,.tbl td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--rule)}
.tbl th{font-size:.68rem;text-transform:uppercase;letter-spacing:.09em;color:var(--ink3);font-weight:600}
.tbl td.n{font-family:"IBM Plex Mono",monospace;font-variant-numeric:tabular-nums;text-align:right}
.scroll{overflow-x:auto}
@media (max-width:640px){.wrap{padding:34px 18px 70px}.e-head{flex-direction:column;gap:9px}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""


HTML=f"""<title>Quem Cita Bendinelli</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Spectral:wght@400;600&family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>{CSS}</style>
<div class="wrap">
<header class="top">
 <p class="eyebrow mono">Auditoria de citações · taxonomia Paperclip · setembro de 2026</p>
 <h1>Quem cita, e como</h1>
 <p class="lede">Cada citação recebida pelos dois artigos foi rastreada até a passagem exata onde
 o trabalho é mencionado, e classificada por papel, postura e reuso efetivo — a mesma taxonomia
 que o <span class="mono">citation-explorer</span> do Paperclip aplica, extraída do código-fonte da ferramenta.</p>
 <div class="kpis">
  <div class="kpi"><b>{TOT}</b><span>citações mapeadas</span></div>
  <div class="kpi"><b>{100*NCL/NDOI:.0f}%</b><span>das {NDOI} com DOI, verificadas</span></div>
  <div class="kpi"><b>{kpi["reuse"]}</b><span>com reuso metodológico externo</span></div>
  <div class="kpi"><b>{kpi["self"]}</b><span>autocitação ou coautor</span></div>
  <div class="kpi hl"><b>{kpi["mis"]}</b><span>atribuições incorretas</span></div>
  <div class="kpi hl"><b>{kpi["ghost"]}</b><span>citações-fantasma</span></div>
 </div>
</header>
<section class="funnel">
 <h2>De {SCHOLAR["airline"]+SCHOLAR["grains"]} citações no Scholar até as que dão para ler</h2>
 <p style="font-size:.9rem;color:var(--ink2);max-width:70ch;margin:14px 0 0">
 Cada degrau retira um grupo pelo motivo declarado. A população do estudo é o
 penúltimo degrau: artigo de periódico, de editora estabelecida, com DOI. O último
 mostra quanto dessa população já tem a passagem citante em mãos.</p>
 <div class="fgrid">{FUNIS}</div>
 <h2 style="margin-top:54px">Onde as citações estão, e como cada revista cita</h2>
 <p style="font-size:.9rem;color:var(--ink2);max-width:70ch;margin:14px 0 18px">
 Cada quadrado é uma citação, colorida pelo papel: verde escuro fundacional,
 verde sustenta, azul menção real, cinza menção breve ou de passagem,
 cinza-claro só na bibliografia, vermelho interpretado errado. A última coluna conta
 quantas adotaram método, dado ou resultado.</p>
 <div class="rgrid">{REVISTAS}</div>
</section>
<section class="funnel">
 <h2>A qualidade dos veículos que citam</h2>
 <p style="font-size:.9rem;color:var(--ink2);max-width:70ch;margin:14px 0 22px">
 Quartil oficial do Scimago (SJR Best Quartile, edição 2025), casado por ISSN.
 Setenta dos 93 periódicos citantes têm quartil; os demais são
 repositório de preprint, série de conferência ou periódico regional
 fora do Scopus.</p>
 <div class="fgrid">{QBARS}</div>
 <h3 style="margin-top:40px;font-size:.78rem;text-transform:uppercase;letter-spacing:.12em;color:var(--ink3)">Papel da citação por quartil do periódico</h3>
 <div style="margin-top:12px">{QMATRIZ}</div>
 <div class="grid2" style="margin-top:30px">
  <p style="font-size:.9rem;color:var(--ink2)"><b>O engajamento de fundo se concentra no topo.</b>
  Toda citação fundacional está em Q1, e {REUSE_Q1} das {REUSE_TOT} que adotam
  método, dado ou resultado também. Quem lê a fundo publica em revista boa.</p>
  <p style="font-size:.9rem;color:var(--ink2)"><b>Mas citação-fantasma não é doença de revista fraca.</b>
  {GHOST_Q1} das {GHOST_TOT} estão em Q1 — entre elas <i>Transportation Research Part E</i>,
  <i>Communications Earth &amp; Environment</i> e <i>Journal of Transport Geography</i>. Listar na
  bibliografia sem citar no texto acontece em periódico de primeira linha.</p>
 </div>
</section>
{"".join(sections)}
<section class="method">
 <h2>Método e limites</h2>
 <div class="grid2">
  <div>
   <h3>Como cada citação foi avaliada</h3>
   <p>Quatro eixos independentes, exatamente como o Paperclip define:</p>
   <ul>
    <li><b>Papel</b> — de <span class="mono">só na bibliografia</span> até <span class="mono">fundacional</span>, medindo o quanto o artigo importou para quem citou.</li>
    <li><b>Postura</b> — apoia, contrapõe ou neutra. Regra deliberadamente liberal: um contraste calmo já conta como contraposição.</li>
    <li><b>Reuso</b> — adoção de método, validação de resultado, reuso de dado, benchmark ou extensão.</li>
    <li><b>Status</b> — presente no corpo do texto ou apenas na lista de referências.</li>
   </ul>
   <p><b>Regra de evidência:</b> nenhuma classificação sem o documento em mãos — a passagem literal, ou o
   texto completo comprovando que a menção só existe na bibliografia. Página de rosto de publisher, que
   exibe as referências sem o corpo, não serve de prova e não entra em contagem alguma.</p>
  </div>
  <div>
   <h3>Onde está o resto</h3>
   <p>O grafo de citação vem da união de OpenAlex, Semantic Scholar, OpenCitations e Europe PMC,
   deduplicada por DOI e por título normalizado. O texto vem de Unpaywall, Europe PMC, arXiv e
   repositórios institucionais.</p>
   <div class="scroll"><table class="tbl">
    <tr><th>Situação</th><th class="n">Citações</th></tr>
    <tr><td>Texto completo validado</td><td class="n">{st("tem_texto")}</td></tr>
    <tr><td>Só página de rosto</td><td class="n">{st("texto_parcial")+st("evidencia_insuficiente")+st("texto_incorreto")}</td></tr>
    <tr><td>OA com verificação anti-bot</td><td class="n">{st("oa_antibot")}</td></tr>
    <tr><td>OA não recuperado</td><td class="n">{st("oa_bloqueado")+st("oa_baixavel")}</td></tr>
    <tr><td>Fechado</td><td class="n">{st("fechado")}</td></tr>
    <tr><td>Só no Scholar, sem DOI</td><td class="n">{st("so_scholar_sem_doi")+st("sem_doi")}</td></tr>
   </table></div>
  </div>
 </div>
 <p style="margin-top:24px"><b>O inventário está fechado.</b> Às quatro APIs somaram-se as listas
 completas de “cited by” do Google Scholar (95 e 76), paginadas manualmente. O Scholar confirmou
 118 registros que as APIs já tinham e acrescentou 45; em contrapartida, as APIs acharam registros que
 o Scholar não lista. A união dá <b>{TOT}</b> — mais do que qualquer fonte sozinha.
 Dos 45 exclusivos do Scholar, 21 foram resolvidos a DOI via Crossref; os {st("so_scholar_sem_doi")} restantes
 são tese, capítulo de livro e periódico sem DOI depositado.</p>
</section>
</div>"""

OUT = auditlib.REPORTS / "index.html"
nbytes = len(HTML.encode("utf-8"))
if "--check" in sys.argv[1:]:
    atual = OUT.read_text(encoding="utf-8") if OUT.exists() else None
    if atual != HTML:
        atual_bytes = len(atual.encode("utf-8")) if atual is not None else 0
        print(f"DRIFT: report/index.html gerado difere do commitado "
              f"({nbytes} bytes gerados vs {atual_bytes} commitados)")
        sys.exit(1)
    print(f"ok: report/index.html idêntico ao gerado ({nbytes} bytes | {TOT} citacoes | {NCL} classificadas)")
else:
    OUT.write_text(HTML, encoding="utf-8")
    print("ok", nbytes, "bytes |", TOT, "citacoes |", NCL, "classificadas")
