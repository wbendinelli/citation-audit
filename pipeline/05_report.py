import json, re, html, os, collections
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
M=json.load(open(f"{ROOT}/data/master.json"))
CL=json.load(open(f"{ROOT}/data/classify.json"))          # chaveado por DOI

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
TITLES={"airline":("Airline delays, congestion internalization and non-price spillover effects of low cost carrier entry","Transportation Research Part A","2016","10.1016/j.tra.2016.01.001"),
        "grains":("What are the main factors that determine post-harvest losses of grains?","Sustainable Production and Consumption","2019","10.1016/j.spc.2019.09.002")}

def esc(s): return html.escape(s or "")
def center(p,n=430):
    m=re.search(r"Bendinelli|@@",p)
    if not m: return (p[:n]+"\u2026") if len(p)>n else p
    a=max(0,m.start()-n//2); b=min(len(p),m.start()+n//2)
    return ("\u2026" if a>0 else "")+p[a:b].strip().replace("@@","")+("\u2026" if b<len(p) else "")

status_tot=collections.Counter()
sections=[]; kpi=collections.Counter()
for key in ("airline","grains"):
    blk=M[key]; title,venue,yr,doi=TITLES[key]
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
        if r.get("is_influential"): chips+='<span class="chip infl">influential \u00b7 S2</span>'
        fl=FLAG.get(c.get("flag") or "")
        qs=[center(p) for p in (c.get("passages") or [])][:2]
        quotes="".join(f"<blockquote>{esc(q)}</blockquote>" for q in qs)
        note=f'<p class="note">{esc(c.get("note"))}</p>' if c.get("note") else ""
        fcls=f" flagged f-{fl[1]}" if fl else ""
        ftag=f'<span class="flag f-{fl[1]}">{fl[0]}</span>' if fl else ""
        ents.append(f'''<article class="entry{fcls}">
 <header class="e-head"><h3>{esc(r.get("title"))}</h3>{ftag}</header>
 <p class="meta"><span class="venue">{esc(r.get("venue") or "sem veículo indexado")}</span><span class="dot">\u00b7</span>{r.get("year") or ""}<span class="dot">\u00b7</span><span class="mono">{esc(r.get("oa_status") or "?")}</span></p>
 <div class="chips">{chips}</div>
 {quotes}{note}
</article>''')
    order=["foundational","supporting","real_mention","brief_mention","drive_by","bibliography_only","wrongly_interpreted"]
    n=sum(dist.values())
    bars="".join(f'<span class="seg s-{ROLE[r][1]}" style="flex:{dist[r]}" title="{PT[r]}: {dist[r]}"><b>{dist[r]}</b></span>' for r in order if dist.get(r))
    leg="".join(f'<span class="lg"><i class="sw s-{ROLE[r][1]}"></i>{PT[r]} <b>{dist[r]}</b></span>' for r in order if dist.get(r))
    sections.append(f'''<section class="paper" id="{key}">
 <div class="p-head"><p class="eyebrow mono">{esc(venue)} \u00b7 {yr}</p><h2>{esc(title)}</h2>
 <p class="doi mono">{doi} \u2014 {total} cita\u00e7\u00f5es na uni\u00e3o de quatro fontes, <b>{n} com evid\u00eancia verificada</b></p></div>
 <div class="bar">{bars}</div><div class="legend">{leg}</div>
 <div class="entries">{"".join(ents)}</div></section>''')

# ---------------- funil e quebra por revista ----------------
import html as _h, unicodedata as _u
GRANDES={"10.1016":"Elsevier","10.1007":"Springer","10.1002":"Wiley","10.1111":"Wiley",
 "10.1155":"Wiley","10.1080":"Taylor & Francis","10.1108":"Emerald","10.3390":"MDPI",
 "10.1177":"SAGE","10.1017":"Cambridge","10.1093":"Oxford UP","10.1515":"De Gruyter",
 "10.1038":"Nature Portfolio","10.1371":"PLOS","10.1186":"BMC","10.1057":"Palgrave"}
SCHOLAR={"airline":95,"grains":76}
def _livro(d):
    suf=d.split("/",1)[1] if "/" in d else ""
    return suf.startswith("978") or "9781" in suf or "9780" in suf or d.startswith("10.1007/978")
def venue_norm(v):
    v=_h.unescape(v or "?").strip()
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
    rs=M[key]["citing"]
    doi=[r for r in rs if r.get("doi")]
    gr=[r for r in doi if r["doi"].split("/")[0] in GRANDES]
    per=[r for r in gr if not _livro(r["doi"])]
    cf=[r for r in per if CL.get(r["doi"].lower())]
    return [("Google Scholar reporta",SCHOLAR[key],None),
            ("Invent\u00e1rio ap\u00f3s dedup e ru\u00eddo",len(rs),len(rs)-SCHOLAR[key]),
            ("Com DOI depositado",len(doi),-(len(rs)-len(doi))),
            ("Editora estabelecida",len(gr),-(len(doi)-len(gr))),
            ("Peri\u00f3dico (sem cap\u00edtulo, anais, preprint)",len(per),-(len(gr)-len(per))),
            ("Com evid\u00eancia verificada",len(cf),-(len(per)-len(cf)))]

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
    for r in M[key]["citing"]:
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
        rtag=(f"<b>{reuse}</b>" if reuse else "<span class='off'>\u2013</span>")
        out.append(f"<tr><td class='v'>{esc(v)}</td><td class='n'>{len(cs)}</td>"
                   f"<td class='qs'>{chips}</td><td class='n'>{rtag}</td></tr>")
    return ("<div class='scroll'><table class='tbl rev'><tr><th>Peri\u00f3dico</th><th class='n'>Cita\u00e7\u00f5es</th>"
            "<th>Distribui\u00e7\u00e3o de papel</th><th class='n'>Reuso</th></tr>"+"".join(out)+"</table></div>")

FUNIS="".join(
  f"<div class='fcol'><h3>{'Aviação' if k=='airline' else 'Grãos'}</h3>{render_funil(k)}</div>"
  for k in ("airline","grains"))
REVISTAS="".join(
  f"<div class='rcol'><h3>{'Aviação' if k=='airline' else 'Grãos'}</h3>{render_revistas(k)}</div>"
  for k in ("airline","grains"))

TOT=sum(len(b["citing"]) for b in M.values())
NCL=sum(1 for k,b in M.items() for r in b["citing"] if CL.get((r.get("doi") or "").lower()))
NDOI=sum(1 for k,b in M.items() for r in b["citing"] if r.get("doi"))
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
 <p class="eyebrow mono">Auditoria de cita\u00e7\u00f5es \u00b7 taxonomia Paperclip \u00b7 setembro de 2026</p>
 <h1>Quem cita, e como</h1>
 <p class="lede">Cada cita\u00e7\u00e3o recebida pelos dois artigos foi rastreada at\u00e9 a passagem exata onde
 o trabalho \u00e9 mencionado, e classificada por papel, postura e reuso efetivo \u2014 a mesma taxonomia
 que o <span class="mono">citation-explorer</span> do Paperclip aplica, extra\u00edda do c\u00f3digo-fonte da ferramenta.</p>
 <div class="kpis">
  <div class="kpi"><b>{TOT}</b><span>cita\u00e7\u00f5es mapeadas</span></div>
  <div class="kpi"><b>{100*NCL/NDOI:.0f}%</b><span>das {NDOI} com DOI, verificadas</span></div>
  <div class="kpi"><b>{kpi["reuse"]}</b><span>com reuso metodol\u00f3gico externo</span></div>
  <div class="kpi"><b>{kpi["self"]}</b><span>autocita\u00e7\u00e3o ou coautor</span></div>
  <div class="kpi hl"><b>{kpi["mis"]}</b><span>atribui\u00e7\u00f5es incorretas</span></div>
  <div class="kpi hl"><b>{kpi["ghost"]}</b><span>cita\u00e7\u00f5es-fantasma</span></div>
 </div>
</header>
<section class="funnel">
 <h2>De 171 cita\u00e7\u00f5es no Scholar at\u00e9 as que d\u00e3o para ler</h2>
 <p style="font-size:.9rem;color:var(--ink2);max-width:70ch;margin:14px 0 0">
 Cada degrau retira um grupo pelo motivo declarado. A popula\u00e7\u00e3o do estudo \u00e9 o
 pen\u00faltimo degrau: artigo de peri\u00f3dico, de editora estabelecida, com DOI. O \u00faltimo
 mostra quanto dessa popula\u00e7\u00e3o j\u00e1 tem a passagem citante em m\u00e3os.</p>
 <div class="fgrid">{FUNIS}</div>
 <h2 style="margin-top:54px">Onde as cita\u00e7\u00f5es est\u00e3o, e como cada revista cita</h2>
 <p style="font-size:.9rem;color:var(--ink2);max-width:70ch;margin:14px 0 18px">
 Cada quadrado \u00e9 uma cita\u00e7\u00e3o, colorida pelo papel: verde escuro fundacional,
 verde sustenta, azul men\u00e7\u00e3o real, cinza men\u00e7\u00e3o breve ou de passagem,
 cinza-claro s\u00f3 na bibliografia, vermelho interpretado errado. A \u00faltima coluna conta
 quantas adotaram m\u00e9todo, dado ou resultado.</p>
 <div class="rgrid">{REVISTAS}</div>
</section>
{"".join(sections)}
<section class="method">
 <h2>M\u00e9todo e limites</h2>
 <div class="grid2">
  <div>
   <h3>Como cada cita\u00e7\u00e3o foi avaliada</h3>
   <p>Quatro eixos independentes, exatamente como o Paperclip define:</p>
   <ul>
    <li><b>Papel</b> \u2014 de <span class="mono">s\u00f3 na bibliografia</span> at\u00e9 <span class="mono">fundacional</span>, medindo o quanto o artigo importou para quem citou.</li>
    <li><b>Postura</b> \u2014 apoia, contrap\u00f5e ou neutra. Regra deliberadamente liberal: um contraste calmo j\u00e1 conta como contraposi\u00e7\u00e3o.</li>
    <li><b>Reuso</b> \u2014 ado\u00e7\u00e3o de m\u00e9todo, valida\u00e7\u00e3o de resultado, reuso de dado, benchmark ou extens\u00e3o.</li>
    <li><b>Status</b> \u2014 presente no corpo do texto ou apenas na lista de refer\u00eancias.</li>
   </ul>
   <p><b>Regra de evid\u00eancia:</b> nenhuma classifica\u00e7\u00e3o sem o documento em m\u00e3os \u2014 a passagem literal, ou o
   texto completo comprovando que a men\u00e7\u00e3o s\u00f3 existe na bibliografia. P\u00e1gina de rosto de publisher, que
   exibe as refer\u00eancias sem o corpo, n\u00e3o serve de prova e n\u00e3o entra em contagem alguma.</p>
  </div>
  <div>
   <h3>Onde est\u00e1 o resto</h3>
   <p>O grafo de cita\u00e7\u00e3o vem da uni\u00e3o de OpenAlex, Semantic Scholar, OpenCitations e Europe PMC,
   deduplicada por DOI e por t\u00edtulo normalizado. O texto vem de Unpaywall, Europe PMC, arXiv e
   reposit\u00f3rios institucionais.</p>
   <div class="scroll"><table class="tbl">
    <tr><th>Situa\u00e7\u00e3o</th><th class="n">Cita\u00e7\u00f5es</th></tr>
    <tr><td>Texto completo validado</td><td class="n">{st("tem_texto")}</td></tr>
    <tr><td>S\u00f3 p\u00e1gina de rosto</td><td class="n">{st("texto_parcial")+st("evidencia_insuficiente")+st("texto_incorreto")}</td></tr>
    <tr><td>OA com verifica\u00e7\u00e3o anti-bot</td><td class="n">{st("oa_antibot")}</td></tr>
    <tr><td>OA n\u00e3o recuperado</td><td class="n">{st("oa_bloqueado")+st("oa_baixavel")}</td></tr>
    <tr><td>Fechado</td><td class="n">{st("fechado")}</td></tr>
    <tr><td>S\u00f3 no Scholar, sem DOI</td><td class="n">{st("so_scholar_sem_doi")+st("sem_doi")}</td></tr>
   </table></div>
  </div>
 </div>
 <p style="margin-top:24px"><b>O invent\u00e1rio est\u00e1 fechado.</b> \u00c0s quatro APIs somaram-se as listas
 completas de \u201ccited by\u201d do Google Scholar (95 e 76), paginadas manualmente. O Scholar confirmou
 118 registros que as APIs j\u00e1 tinham e acrescentou 45; em contrapartida, as APIs acharam registros que
 o Scholar n\u00e3o lista. A uni\u00e3o d\u00e1 <b>{TOT}</b> \u2014 mais do que qualquer fonte sozinha.
 Dos 45 exclusivos do Scholar, 21 foram resolvidos a DOI via Crossref; os {st("so_scholar_sem_doi")} restantes
 s\u00e3o tese, cap\u00edtulo de livro e peri\u00f3dico sem DOI depositado.</p>
</section>
</div>"""
open(f"{ROOT}/report/index.html","w").write(HTML)
print("ok", len(HTML), "bytes |", TOT, "citacoes |", NCL, "classificadas")
