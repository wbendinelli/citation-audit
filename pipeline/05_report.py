import json, re, html, os
HERE=os.path.dirname(os.path.abspath(__file__))
inv=json.load(open(f"{HERE}/inventory.json")); cl=json.load(open(f"{HERE}/classify.json"))

ROLE={"bibliography_only":("só na bibliografia","ghost",0),
      "drive_by":("de passagem","dim",1),
      "brief_mention":("menção breve","dim",2),
      "real_mention":("menção real","accent",3),
      "supporting":("sustenta","good",4),
      "foundational":("fundacional","good-deep",5),
      "wrongly_interpreted":("interpretado errado","bad",-1)}
STANCE={"supporting":("apoia","s-good"),"contradictory":("contrapõe","s-bad"),"none":("neutra","s-dim")}
REUSE={"method_adoption":"adota método","result_validated":"valida resultado",
       "dataset_reuse":"reusa dado","benchmarking":"benchmark","work_extended":"estende"}
FLAG={"best":("Melhor citação","good"),"good":("Uso substantivo","good"),
      "critical":("Crítica ao artigo","bad"),"misattribution":("Atribuição incorreta","bad"),
      "ghost":("Citação-fantasma","ghost"),"weak":("Atribuição frágil","warn"),
      "duplicate":("Publicação duplicada","warn")}
PAPERS={"airline":("Airline delays, congestion internalization and non-price spillover effects of low cost carrier entry",
                   "Transportation Research Part A","2016","10.1016/j.tra.2016.01.001",53),
        "grains":("What are the main factors that determine post-harvest losses of grains?",
                  "Sustainable Production and Consumption","2019","10.1016/j.spc.2019.09.002",60)}

def center(p, n=430):
    m=re.search(r"Bendinelli",p)
    if not m: return (p[:n]+"…") if len(p)>n else p
    a=max(0,m.start()-n//2); b=min(len(p),m.start()+n//2)
    s=("…" if a>0 else "")+p[a:b].strip()+("…" if b<len(p) else "")
    return s

def pick(it):
    ps=[p for p in it.get("passages",[]) if "Bendinelli" in p] or it.get("passages",[])
    ps=sorted(ps,key=len)
    out,seen=[],set()
    for p in ps:
        c=center(p); k=re.sub(r"\W","",c.lower())[:60]
        if k in seen: continue
        seen.add(k); out.append(c)
        if len(out)==2: break
    return out

def esc(s): return html.escape(s or "")

sections=[]
for key in ("airline","grains"):
    title,venue,yr,doi,ncit=PAPERS[key]
    ents=[]
    items=sorted([x for x in inv[key]["citing"] if str(x["n"]) in cl[key]],
                 key=lambda x:(-ROLE[cl[key][str(x["n"])]["role"]][2], x["venue"] or ""))
    dist={}
    for it in items:
        c=cl[key][str(it["n"])]; dist[c["role"]]=dist.get(c["role"],0)+1
        rl,rc,_=ROLE[c["role"]]; sl,sc=STANCE[c["stance"]]
        fl=FLAG.get(c["flag"])
        chips=f'<span class="chip r-{rc}">{rl}</span><span class="chip {sc}">{sl}</span>'
        for t in c["reuse"]: chips+=f'<span class="chip reuse">{REUSE[t]}</span>'
        if it.get("s2_influential"): chips+='<span class="chip infl">influential · S2</span>'
        quotes="".join(f'<blockquote>{esc(q)}</blockquote>' for q in pick(it))
        note=f'<p class="note">{esc(c["note"])}</p>' if c["note"] else ""
        flagcls=f' flagged f-{fl[1]}' if fl else ""
        flagtag=f'<span class="flag f-{fl[1]}">{fl[0]}</span>' if fl else ""
        ents.append(f'''<article class="entry{flagcls}">
 <header class="e-head"><h3>{esc(it["title"])}</h3>{flagtag}</header>
 <p class="meta"><span class="venue">{esc(it["venue"] or "sem veículo indexado")}</span><span class="dot">·</span>{it["year"]}<span class="dot">·</span><span class="mono">{esc(it["oa_status"])}</span></p>
 <div class="chips">{chips}</div>
 {quotes}{note}
</article>''')
    order=["foundational","supporting","real_mention","brief_mention","drive_by","bibliography_only","wrongly_interpreted"]
    tot=sum(dist.values())
    bars="".join(f'<span class="seg s-{ROLE[r][1]}" style="flex:{dist[r]}" title="{ROLE[r][0]}: {dist[r]}"><b>{dist[r]}</b></span>'
                 for r in order if dist.get(r))
    legend="".join(f'<span class="lg"><i class="sw s-{ROLE[r][1]}"></i>{ROLE[r][0]} <b>{dist[r]}</b></span>'
                   for r in order if dist.get(r))
    sections.append(f'''<section class="paper" id="{key}">
 <div class="p-head">
  <p class="eyebrow mono">{esc(venue)} · {yr}</p>
  <h2>{esc(title)}</h2>
  <p class="doi mono">{doi} — {ncit} citações no OpenAlex, <b>{tot} com passagem recuperada</b></p>
 </div>
 <div class="bar">{bars}</div>
 <div class="legend">{legend}</div>
 <div class="entries">{"".join(ents)}</div>
</section>''')

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
.kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:1px;
 background:var(--rule);border:1px solid var(--rule);margin:30px 0 0}
@media (max-width:760px){.kpis{grid-template-columns:repeat(2,1fr)}.kpis .kpi:last-child{grid-column:1/-1}}
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
  <div class="kpi"><b>113</b><span>citações nos dois artigos</span></div>
  <div class="kpi"><b>31</b><span>com passagem recuperada</span></div>
  <div class="kpi"><b>3</b><span>com reuso metodológico real</span></div>
  <div class="kpi hl"><b>2</b><span>atribuições incorretas</span></div>
  <div class="kpi hl"><b>2</b><span>citações-fantasma</span></div>
 </div>
</header>
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
  </div>
  <div>
   <h3>De onde veio a evidência</h3>
   <p>Grafo de citações do OpenAlex; texto completo por Unpaywall, Europe PMC, arXiv e repositórios
   institucionais; trechos de citação do Semantic Scholar como fonte complementar. Nenhuma
   classificação foi feita sem a passagem literal em mãos.</p>
   <div class="scroll"><table class="tbl">
    <tr><th>Cobertura de passagem</th><th class="n">Aviação</th><th class="n">Grãos</th></tr>
    <tr><td>Citações totais</td><td class="n">53</td><td class="n">60</td></tr>
    <tr><td>Texto completo obtido</td><td class="n">11</td><td class="n">14</td></tr>
    <tr><td>Passagem classificável</td><td class="n">12</td><td class="n">19</td></tr>
    <tr><td>Teto do Paperclip</td><td class="n">4–8</td><td class="n">0</td></tr>
   </table></div>
  </div>
 </div>
 <p style="margin-top:24px"><b>O que ainda falta.</b> 82 das 113 citações estão atrás de paywall
 — Elsevier, Wiley e Springer bloqueiam download automatizado. Elas não foram classificadas e
 não entram em nenhuma contagem acima. A leitura correta destes números é
 “entre as citações que deu para ler”, não “entre todas”.</p>
</section>
</div>"""
open(f"{HERE}/report.html","w").write(HTML)
print("ok", len(HTML), "bytes")
