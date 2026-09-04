"""Etapa 80: gera reports/01-impacto/index.html.

Todo agregado numérico vem de reports/01-impacto/dados.json — a fonte única
gerada por tools/audit_70_numbers.py a partir de data/*.json. Este script não
recomputa funil, cobertura, quartis, distribuições nem listas agregadas; ele
só lê os blocos já prontos de dados.json e formata. O único texto que ainda
vem direto de data/master.json e data/classify.json é o texto por registro
de cada citação (título, DOI, veículo, trechos citantes, nota) usado nos
cartões de citação por artigo — isso não é número agregado.

Uso:
  python3 tools/audit_80_report_html.py           grava reports/01-impacto/index.html
  python3 tools/audit_80_report_html.py --check    renderiza em memória e compara
                                                    byte a byte com o arquivo commitado
  python3 tools/audit_80_report_html.py --root P   raiz do repositório (padrão: inferida
                                                    de __file__, como auditlib.ROOT) --
                                                    controla de onde data/master.json,
                                                    data/classify.json e
                                                    reports/01-impacto/dados.json são
                                                    lidos, e onde reports/01-impacto/
                                                    index.html é gravado
"""

import argparse
import html
import json
import re
import sys
from pathlib import Path

import auditlib

# --------------------------------------------------------------------------
# CLI / caminhos
# --------------------------------------------------------------------------


def parse_args(argv):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--root",
        type=Path,
        default=auditlib.ROOT,
        help="raiz do repositório (padrão: inferida de __file__)",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="renderiza em memória e compara byte a byte com o arquivo commitado; "
        "nunca grava; sai 1 se houver diferença",
    )
    return ap.parse_args(argv)


ARGS = parse_args(sys.argv[1:])
ROOT = ARGS.root.resolve()
OUT_DIR = ROOT / "reports" / "01-impacto"
DADOS_PATH = OUT_DIR / "dados.json"
OUT = OUT_DIR / "index.html"

with open(DADOS_PATH, encoding="utf-8") as _f:
    DADOS = json.load(_f)


def _load_versioned(path, key):
    """Mesma regra de auditlib._load_versioned/tools/audit_70_numbers.load_versioned,
    reimplementada aqui (em vez de auditlib.load_master()/load_classify()) só
    para que --root também governe de onde master.json/classify.json são
    lidos -- auditlib.ROOT é fixo pela localização de auditlib.py."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict) and "meta" in raw and key in raw:
        return raw
    return {"meta": {"schema": 1}, key: raw}


master = _load_versioned(ROOT / "data" / "master.json", "papers")
CL = _load_versioned(ROOT / "data" / "classify.json", "entries")["entries"]

PAPERS = ("airline", "grains")
PAPER_PT = {"airline": "Aviação", "grains": "Grãos"}


# --------------------------------------------------------------------------
# Vocabulário de exibição -- une os rótulos v1 (auditlib.role_flag_v1, usado
# só no texto por registro dos cartões) e as chaves v2-nativas de dados.json
# (papel_quartil, periodicos.papeis) num único dicionário: são o mesmo
# vocabulário de 7 papéis, só com 2 nomes diferentes para os mesmos 2
# valores (bibliography_only=reference_list_only,
# wrongly_interpreted=misrepresented) -- ver auditlib.role_flag_v1 e
# tools/audit_70_numbers.ROLE_V2_ORDER/axis_role.
# --------------------------------------------------------------------------
ROLE = {
    "bibliography_only": ("só na bibliografia", "ghost", 0),
    "reference_list_only": ("só na bibliografia", "ghost", 0),
    "drive_by": ("de passagem", "dim", 1),
    "brief_mention": ("menção breve", "dim", 2),
    "real_mention": ("menção real", "accent", 3),
    "supporting": ("sustenta", "good", 4),
    "foundational": ("fundacional", "good-deep", 5),
    "wrongly_interpreted": ("interpretado errado", "bad", -1),
    "misrepresented": ("interpretado errado", "bad", -1),
}
PT = {k: v[0] for k, v in ROLE.items()}
ROLE_V2_ORDER = [
    "foundational",
    "supporting",
    "real_mention",
    "brief_mention",
    "drive_by",
    "reference_list_only",
    "misrepresented",
]
STANCE = {
    "supporting": ("apoia", "s-good"),
    "contradictory": ("contrapõe", "s-bad"),
    "none": ("neutra", "s-dim"),
}
REUSE = {
    "method_adoption": "adota método",
    "result_validated": "valida resultado",
    "dataset_reuse": "reusa dado",
    "benchmarking": "benchmark",
    "work_extended": "estende",
}
FLAG = {
    "best": ("Melhor citação", "good"),
    "good": ("Uso substantivo", "good"),
    "critical": ("Crítica ao artigo", "bad"),
    "misattribution": ("Atribuição incorreta", "bad"),
    "ghost": ("Citação-fantasma", "ghost"),
    "weak": ("Atribuição frágil", "warn"),
    "duplicate": ("Publicação duplicada", "warn"),
    "autocitacao": ("Autocitação", "ghost"),
    "coautor": ("Citação de coautor", "warn"),
}
PRESENCE_PT = {
    "in_text": "no corpo do texto",
    "reference_list_only": "só na bibliografia",
    "not_cited": "não citado",
}
ACCURACY_PT = {
    "accurate": "fiel",
    "imprecise": "impreciso",
    "misrepresented": "deturpado",
}
RELATION_PT = {"independent": "–", "coauthor": "coautor", "self": "autocitação"}
HIGHLIGHT_PT = {"none": "–", "good": "boa", "best": "melhor"}
QORD = ["Q1", "Q2", "Q3", "Q4", "fora_do_scimago", "sem_metrica"]
QLABEL = {
    "Q1": "Q1",
    "Q2": "Q2",
    "Q3": "Q3",
    "Q4": "Q4",
    "fora_do_scimago": "fora do Scimago",
    "sem_metrica": "sem métrica",
}
QCLS = {
    "Q1": "q1",
    "Q2": "q2",
    "Q3": "q3",
    "Q4": "q4",
    "fora_do_scimago": "qx",
    "sem_metrica": "qn",
}
AXIS_PT = {
    "accuracy": "fidelidade",
    "accuracy_misrepresented": "deturpação (sim/não)",
    "accuracy_not_accurate": "imprecisão ou pior (sim/não)",
    "claim_ids": "afirmação citada",
    "depth": "profundidade",
    "depth_substantive": "uso substantivo (sim/não)",
    "distortion": "subcódigo de distorção",
    "presence": "presença",
    "reuse": "reuso",
    "stance": "postura",
}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def esc(s):
    return html.escape(s or "")


def center(p, n=430):
    m = re.search(r"Bendinelli|@@", p)
    if not m:
        return (p[:n] + "…") if len(p) > n else p
    a = max(0, m.start() - n // 2)
    b = min(len(p), m.start() + n // 2)
    return (
        ("…" if a > 0 else "")
        + p[a:b].strip().replace("@@", "")
        + ("…" if b < len(p) else "")
    )


def leaf_val(obj):
    """Valor numérico cru de uma folha de dados.json (para ordenar/computar):
    tanto o inteiro/float puro quanto o envelope {valor,txt}/{valor,pct,ratio}
    -- ver tools/audit_70_numbers.py (int_leaf/dec_leaf/pct_leaf)."""
    if isinstance(obj, dict):
        return obj.get("valor")
    return obj


def leaf_txt(obj):
    """Texto de exibição de uma folha de dados.json -- usa txt/pct quando
    existem (regra do enunciado), senão o próprio escalar."""
    if isinstance(obj, dict):
        if "pct" in obj and "ratio" in obj:
            return f"{obj['pct']} ({obj['ratio']})"
        if "txt" in obj:
            return obj["txt"]
        v = obj.get("valor")
        return "-" if v is None else str(v)
    if obj is None:
        return "-"
    return str(obj)


def is_pendente(v):
    return isinstance(v, dict) and v.get("pendente") is True


def pending_note(v, titulo=None):
    """Bloco {'pendente': True, 'motivo': ...} de dados.json vira aviso
    visível na seção, nunca um erro (regra do enunciado)."""
    motivo = esc(v.get("motivo", ""))
    prefix = f"{esc(titulo)}: " if titulo else ""
    return f'<p class="pending">{prefix}<b>pendente</b> — {motivo}</p>'


def pct0(x):
    return "-" if x is None else f"{round(x * 100)}%"


def pt_dec(x, casas=3):
    if x is None:
        return "-"
    return f"{x:.{casas}f}".replace(".", ",")


# --------------------------------------------------------------------------
# Cartões de citação por artigo -- texto por registro (título, DOI, veículo,
# trechos, nota) vem de data/master.json + data/classify.json; a barra de
# distribuição por papel vem de dados.json (papel_quartil), não é recontada
# aqui.
# --------------------------------------------------------------------------

sections = []
for key in PAPERS:
    blk = master["papers"][key]
    art = DADOS["artigos"][key]
    title, venue, yr, doi = art["titulo"], art["veiculo"], art["ano"], art["doi"]
    total = leaf_val(art["n_citantes"])
    n_classificados = DADOS["eixos"][key]["presence"]["in_text"]["D"]

    rows = [(r, CL.get((r.get("doi") or "").lower())) for r in blk["citing"]]
    rows = [(r, c) for r, c in rows if c]
    rows.sort(
        key=lambda rc: (
            -ROLE[auditlib.role_flag_v1(rc[1])[0]][2],
            rc[0].get("venue") or "",
        )
    )
    ents = []
    for r, c in rows:
        role, flag = auditlib.role_flag_v1(c)  # projeção v2 -> (role, flag) v1
        sl, sc = STANCE[c["stance"]]
        chips = f'<span class="chip r-{ROLE[role][1]}">{PT[role]}</span><span class="chip {sc}">{sl}</span>'
        for t in c.get("reuse", []):
            chips += f'<span class="chip reuse">{REUSE[t]}</span>'
        if r.get("is_influential"):
            chips += '<span class="chip infl">influential · S2</span>'
        fl = FLAG.get(flag or "")
        qs = [center(p) for p in (c.get("passages") or [])][:2]
        quotes = "".join(f"<blockquote>{esc(q)}</blockquote>" for q in qs)
        note = f'<p class="note">{esc(c.get("note"))}</p>' if c.get("note") else ""
        fcls = f" flagged f-{fl[1]}" if fl else ""
        ftag = f'<span class="flag f-{fl[1]}">{fl[0]}</span>' if fl else ""
        ents.append(f"""<article class="entry{fcls}">
 <header class="e-head"><h3>{esc(r.get("title"))}</h3>{ftag}</header>
 <p class="meta"><span class="venue">{esc(r.get("venue") or "sem veículo indexado")}</span><span class="dot">·</span>{r.get("year") or ""}<span class="dot">·</span><span class="mono">{esc(r.get("oa_status") or "?")}</span></p>
 <div class="chips">{chips}</div>
 {quotes}{note}
</article>""")

    # distribuição por papel: soma de papel_quartil[paper].matriz sobre todos
    # os baldes de quartil -- mesmo universo (todo classificado com DOI) do
    # laço de cartões acima, já agregado em dados.json.
    matriz = DADOS["papel_quartil"][key]["matriz"]
    dist = {r: sum(matriz.get(q, {}).get(r, 0) for q in matriz) for r in ROLE_V2_ORDER}
    bars = "".join(
        f'<span class="seg s-{ROLE[r][1]}" style="flex:{dist[r]}" title="{PT[r]}: {dist[r]}"><b>{dist[r]}</b></span>'
        for r in ROLE_V2_ORDER
        if dist.get(r)
    )
    leg = "".join(
        f'<span class="lg"><i class="sw s-{ROLE[r][1]}"></i>{PT[r]} <b>{dist[r]}</b></span>'
        for r in ROLE_V2_ORDER
        if dist.get(r)
    )
    sections.append(f'''<section class="paper" id="{key}">
 <div class="p-head"><p class="eyebrow mono">{esc(venue)} · {yr}</p><h2>{esc(title)}</h2>
 <p class="doi mono">{doi} — {total} citações na união de quatro fontes, <b>{n_classificados} com evidência verificada</b></p></div>
 <div class="bar">{bars}</div><div class="legend">{leg}</div>
 <div class="entries">{"".join(ents)}</div></section>''')


# --------------------------------------------------------------------------
# Funil, revistas, linha do tempo -- tudo de dados.json (funil, periodicos,
# linha_do_tempo)
# --------------------------------------------------------------------------


def render_funil(paper):
    steps = DADOS["funil"][paper]["steps"]
    vals = [leaf_val(s["valor"]) for s in steps]
    topo = vals[0] or 1
    li = []
    for i, s in enumerate(steps):
        val = vals[i]
        delta = s["delta"]
        w = 100 * val / topo
        d = f"<span class='delta'>{delta:+d}</span>" if delta not in (None, 0) else ""
        cls_ = (
            "step final" if i == len(steps) - 1 else ("step base" if i == 0 else "step")
        )
        li.append(
            f"<li class='{cls_}'><span class='rot'>{esc(s['rotulo'])}</span>"
            f"<span class='track'><i style='width:{w:.1f}%'></i></span>"
            f"<span class='val'>{val}</span>{d}</li>"
        )
    return "<ol class='funil'>" + "".join(li) + "</ol>"


def render_revistas(paper):
    rows = DADOS["periodicos"]["por_artigo"][paper]
    out = []
    for row in rows:
        papeis = row["papeis"]
        chips = "".join(
            f"<i class='q s-{ROLE[r][1]}' title='{PT[r]}: {papeis[r]}'>{papeis[r]}</i>"
            for r in ROLE_V2_ORDER
            if papeis.get(r)
        )
        reuso_n = row["reuso_n"]
        rtag = f"<b>{reuso_n}</b>" if reuso_n else "<span class='off'>–</span>"
        out.append(
            f"<tr><td class='v'>{esc(row['nome_norm'])}</td><td class='n'>{row['n']}</td>"
            f"<td class='qs'>{chips}</td><td class='n'>{rtag}</td></tr>"
        )
    return (
        "<div class='scroll'><table class='tbl rev'><tr><th>Periódico</th><th class='n'>Citações</th>"
        "<th>Distribuição de papel</th><th class='n'>Reuso</th></tr>"
        + "".join(out)
        + "</table></div>"
    )


def render_linha_do_tempo(paper):
    dados_ano = DADOS["linha_do_tempo"][paper]
    if not dados_ano:
        return "<p class='off' style='font-size:.85rem'>Sem citação classificada com ano registrado.</p>"
    rows = "".join(
        f"<tr><td class='v'>{esc(ano)}</td><td class='n'>{c['fundo']}</td><td class='n'>{c['conteudo']}</td>"
        f"<td class='n'>{c['passagem']}</td><td class='n'>{c['fantasma']}</td></tr>"
        for ano, c in dados_ano.items()
    )
    return (
        "<div class='scroll'><table class='tbl'><tr><th>Ano</th><th class='n'>Fundo</th>"
        "<th class='n'>Conteúdo</th><th class='n'>Passagem</th><th class='n'>Fantasma</th></tr>"
        + rows
        + "</table></div>"
    )


FUNIS = "".join(
    f"<div class='fcol'><h3>{PAPER_PT[k]}</h3>{render_funil(k)}</div>" for k in PAPERS
)
REVISTAS = "".join(
    f"<div class='rcol'><h3>{PAPER_PT[k]}</h3>{render_revistas(k)}</div>"
    for k in PAPERS
)
LINHA_TEMPO = "".join(
    f"<div class='fcol'><h3>{PAPER_PT[k]}</h3>{render_linha_do_tempo(k)}</div>"
    for k in PAPERS
)

POPULACAO_TOTAL = DADOS["populacao"]["total"]
SCHOLAR_TOTAL = sum(leaf_val(DADOS["funil"][p]["steps"][0]["valor"]) for p in PAPERS)


# --------------------------------------------------------------------------
# Quartil Scimago -- barras (quartil.todas_citacoes), matriz papel×quartil
# (papel_quartil.pooled.matriz), cobertura de evidência por quartil
# (cobertura_quartil) e editoras (editoras); tudo de dados.json.
# --------------------------------------------------------------------------


def barras_q(paper):
    c = DADOS["quartil"]["todas_citacoes"][paper]
    segs = "".join(
        f"<span class='qseg {QCLS[x]}' style='flex:{c[x]}' title='{QLABEL[x]}: {c[x]}'>{c[x]}</span>"
        for x in QORD
        if c.get(x)
    )
    leg = "".join(
        f"<span class='lg'><i class='sw {QCLS[x]}'></i>{QLABEL[x]} <b>{c[x]}</b></span>"
        for x in QORD
        if c.get(x)
    )
    return f"<div class='qbar'>{segs}</div><div class='legend'>{leg}</div>"


def matriz_q():
    matriz = DADOS["papel_quartil"]["pooled"]["matriz"]
    th = "".join(f"<th>{PT[r]}</th>" for r in ROLE_V2_ORDER)
    tr = ""
    for x in QORD:
        linha = matriz.get(x)
        if not linha:
            continue
        tds = "".join(
            f"<td class='n {'hi' if linha.get(r) else 'off'}'>{linha.get(r) or '·'}</td>"
            for r in ROLE_V2_ORDER
        )
        tr += (
            f"<tr><td class='v'><i class='sw {QCLS[x]}'></i>{QLABEL[x]}</td>{tds}</tr>"
        )
    return f"<div class='scroll'><table class='tbl mat'><tr><th>Quartil</th>{th}</tr>{tr}</table></div>"


def render_cobertura_quartil():
    cq = DADOS["cobertura_quartil"]
    rows = []
    for q in ("Q1", "Q2", "Q3", "Q4"):
        row = cq[q]
        rows.append(
            f"<tr><td class='v'>{q}</td><td class='n'>{row['total']}</td>"
            f"<td class='n'>{row['trecho']}</td><td class='n'>{row['fantasma']}</td>"
            f"<td class='n'>{row['aresta_falsa']}</td><td class='n'>{row['pendente']}</td>"
            f"<td class='n'>{row['pct_evidencia']['pct']}</td><td class='n'>{row['pct_trecho']['pct']}</td></tr>"
        )
    tot = cq["total"]
    rows.append(
        f"<tr><td class='v'><b>Total</b></td><td class='n'><b>{tot['total']}</b></td>"
        f"<td class='n'><b>{tot['trecho']}</b></td><td class='n'><b>{tot['fantasma']}</b></td>"
        f"<td class='n'><b>{tot['aresta_falsa']}</b></td><td class='n'><b>{tot['pendente']}</b></td>"
        f"<td class='n'><b>{tot['pct_evidencia']['pct']}</b></td><td class='n'><b>{tot['pct_trecho']['pct']}</b></td></tr>"
    )
    return (
        "<div class='scroll'><table class='tbl'><tr><th>Quartil</th><th class='n'>Total</th>"
        "<th class='n'>Trecho</th><th class='n'>Fantasma</th><th class='n'>Aresta falsa</th>"
        "<th class='n'>Pendente</th><th class='n'>% com evidência</th><th class='n'>% com trecho</th></tr>"
        + "".join(rows)
        + "</table></div>"
    )


def render_editoras():
    pooled = DADOS["editoras"]["pooled"]
    rows = "".join(
        f"<tr><td class='v'>{esc(nome)}</td><td class='n'>{n}</td></tr>"
        for nome, n in pooled.items()
    )
    return (
        "<div class='scroll'><table class='tbl'><tr><th>Editora</th><th class='n'>Citações com DOI</th></tr>"
        + rows
        + "</table></div>"
    )


QBARS = "".join(
    f"<div class='fcol'><h3>{PAPER_PT[k]}</h3>{barras_q(k)}</div>" for k in PAPERS
)
QMATRIZ = matriz_q()
COBERTURA_TBL = render_cobertura_quartil()
EDITORAS_TBL = render_editoras()

_pq_pooled = DADOS["papel_quartil"]["pooled"]
REUSE_Q1 = _pq_pooled["reuso_por_quartil"].get("Q1", 0)
REUSE_TOT = sum(_pq_pooled["reuso_por_quartil"].values())
GHOST_Q1 = _pq_pooled["fantasma_por_quartil"].get("Q1", 0)
GHOST_TOT = sum(_pq_pooled["fantasma_por_quartil"].values())
FOUND_Q1 = _pq_pooled["matriz"].get("Q1", {}).get("foundational", 0)
FOUND_TOT = sum(
    _pq_pooled["matriz"].get(q, {}).get("foundational", 0) for q in _pq_pooled["matriz"]
)

PERIODICOS_TOTAL = DADOS["periodicos"]["total"]
PERIODICOS_CASADOS = DADOS["periodicos"]["scimago_casados"]
SCIMAGO_EDITION = DADOS["constantes"]["scimago_edition"]


# --------------------------------------------------------------------------
# Seções novas: IRR, taxas-base, fantasmas auditados, afirmações, anexo --
# tudo de dados.json, tabela simples, bloco pendente vira aviso visível.
# --------------------------------------------------------------------------


def irr_scalar(pair):
    """Extrai (valor 0..1, rótulo da métrica) de um par de codificadores em
    irr.*.eixos.*.pares.* -- os eixos têm formatos bem diferentes entre si
    (ver docstring de tools/audit_70_numbers._summarize_irr_axis_pairs), daí
    a cadeia de tentativas em vez de um único caminho fixo."""
    if not isinstance(pair, dict):
        return None, None
    point = pair.get("point")
    if isinstance(point, dict) and point.get("raw_agreement") is not None:
        return point["raw_agreement"], "concordância bruta"
    if pair.get("raw_agreement") is not None:
        return pair["raw_agreement"], "concordância bruta"
    jac = pair.get("jaccard")
    if isinstance(jac, dict):
        jp = jac.get("point") or {}
        if jp.get("jaccard_mean") is not None:
            return jp["jaccard_mean"], "Jaccard médio"
    return None, None


def render_irr():
    irr = DADOS["irr"]
    parts = []

    adj = irr["adjudication"]
    if is_pendente(adj):
        parts.append(pending_note(adj, "adjudicação"))
    else:
        stats_rows = "".join(
            f"<tr><td class='v'>{esc(k)}</td><td class='n'>{v}</td></tr>"
            for k, v in sorted(adj["stats"].items())
        )
        parts.append(
            f"<h3 class='sub'>Adjudicação</h3>"
            f"<p style='font-size:.9rem;color:var(--ink2);max-width:70ch'>{adj['n_items']} itens julgados "
            f"(as 104 entradas vivas + 10 sondas duplicadas), {adj['n_contested']} contestados. Por "
            f"eixo:categoria, quantas decisões saíram unânimes, por maioria ou foram ao colegiado.</p>"
            f"<div class='scroll'><table class='tbl'><tr><th>Eixo:categoria</th><th class='n'>N</th></tr>"
            f"{stats_rows}</table></div>"
        )

    pre = irr["pre"]
    if is_pendente(pre):
        parts.append(pending_note(pre, "pré-adjudicação"))
    else:
        rows = []
        for axis in sorted(pre["eixos"]):
            axv = pre["eixos"][axis]
            alpha = axv.get("alpha")
            vals = []
            for p in (axv.get("pares") or {}).values():
                v, _ = irr_scalar(p)
                if v is not None:
                    vals.append(v)
            media = sum(vals) / len(vals) if vals else None
            alpha_txt = pt_dec(alpha) if alpha is not None else "-"
            rows.append(
                f"<tr><td class='v'>{esc(AXIS_PT.get(axis, axis))}</td>"
                f"<td class='n'>{alpha_txt}</td><td class='n'>{pct0(media)}</td></tr>"
            )
        parts.append(
            f"<h3 class='sub'>Antes da adjudicação (N={pre['n_items']}, 3 codificadores)</h3>"
            f"<div class='scroll'><table class='tbl'><tr><th>Eixo</th>"
            f"<th class='n'>α de Krippendorff</th>"
            f"<th class='n'>Concordância par a par (média)</th></tr>{''.join(rows)}</table></div>"
        )

    post = irr["post"]
    if is_pendente(post):
        parts.append(pending_note(post, "pós-adjudicação"))
    else:
        coders = sorted(post.keys())
        axes = sorted(
            {a for c in coders if not is_pendente(post[c]) for a in post[c]["eixos"]}
        )
        head = "".join(f"<th class='n'>{esc(c)}</th>" for c in coders)
        rows = []
        for axis in axes:
            tds = []
            for c in coders:
                cb = post[c]
                if is_pendente(cb):
                    tds.append("<td class='n off'>·</td>")
                    continue
                pares = (cb["eixos"].get(axis) or {}).get("pares") or {}
                v = None
                for p in pares.values():
                    v, _ = irr_scalar(p)
                    break
                tds.append(f"<td class='n'>{pct0(v)}</td>")
            rows.append(
                f"<tr><td class='v'>{esc(AXIS_PT.get(axis, axis))}</td>{''.join(tds)}</tr>"
            )
        parts.append(
            f"<h3 class='sub'>Depois da adjudicação, cada codificador contra o rótulo final</h3>"
            f"<div class='scroll'><table class='tbl'><tr><th>Eixo</th>{head}</tr>"
            f"{''.join(rows)}</table></div>"
        )

    B = leaf_txt(DADOS["constantes"]["B"])
    seed = leaf_txt(DADOS["constantes"]["seed"])
    cortes = DADOS["constantes"]["krippendorff_cutoffs"]
    intro = (
        "<p style='font-size:.9rem;color:var(--ink2);max-width:70ch;margin:14px 0 22px'>"
        "Três codificadores rotularam o mesmo pacote cego (identidade apagada) antes de "
        "qualquer adjudicação; divergência virou decisão por maioria ou foi ao colegiado. "
        f"Intervalos de 95% por bootstrap (B={B}, seed={seed}). Leitura de referência do α de "
        f"Krippendorff: abaixo de {pct0(cortes['tentativo'])} é insuficiente, entre "
        f"{pct0(cortes['tentativo'])} e {pct0(cortes['confiavel'])} é tentativo, "
        f"{pct0(cortes['confiavel'])} ou mais é confiável (Krippendorff 2011).</p>"
    )
    return f"""<section class="funnel">
 <h2>Confiabilidade entre codificadores</h2>
 {intro}
 {"".join(parts)}
</section>"""


def render_taxa_base():
    tb = DADOS["taxa_base"]
    if is_pendente(tb):
        return (
            '<section class="funnel"><h2>Como nossas taxas se comparam à literatura</h2>'
            f"{pending_note(tb)}</section>"
        )
    rows = []
    for r in tb["rows"]:
        pooled = r["results"].get("pooled")
        if pooled and pooled.get("rate") is not None:
            nosso = f"{round(pooled['rate'] * 100)}% ({pooled['numerator']}/{pooled['denominator']})"
        else:
            nosso = "-"
        status = r.get("verification_status") or "-"
        publicado = esc(r["published"]) if r.get("published") else "–"
        # denominator_label é curto (D_read/D_body/D_pop/D_text/D_ind) e distingue
        # as 3 linhas de "fantasma" (D_read/D_body/D_pop), que compartilham a
        # mesma description; denominator_note existe só nessas 3 e é nota de
        # bastidor do levantamento (audit_68_base_rates.py), não rótulo de leitor.
        rotulo = f"{r['denominator_label']} — {r['description']}"
        rows.append(
            f"<tr><td class='v'>{esc(rotulo)}</td><td class='n'>{nosso}</td>"
            f"<td>{publicado}</td><td>{esc(status)}</td></tr>"
        )
    return f"""<section class="funnel">
 <h2>Como nossas taxas se comparam à literatura</h2>
 <p style="font-size:.9rem;color:var(--ink2);max-width:70ch;margin:14px 0 18px">
 Cada linha compara uma taxa medida aqui (pooled, sobre as citações classificadas) contra um
 número publicado numa fonte externa. "Nosso valor" é a taxa bruta, com numerador e denominador
 entre parênteses; unidade e população de medição nem sempre coincidem exatamente com a fonte —
 ver a nota de comparabilidade de cada indicador em <span class="mono">reports/01-impacto/dados.json</span>.
 "Verificação" é o status do próprio levantamento (<span class="mono">audit_68_base_rates.py</span>),
 não uma auditoria independente da fonte publicada.</p>
 <div class="scroll"><table class="tbl"><tr><th>Indicador</th><th class="n">Nosso valor</th>
 <th>Publicado</th><th>Verificação</th></tr>{"".join(rows)}</table></div>
</section>"""


CAT_PT = {
    "genuine": "genuína — sem menção comprovada no corpo",
    "extraction_failure": "falha de extração — havia marcador, o pipeline perdeu",
    "body_unavailable": "corpo indisponível — depende da leitura documentada do codificador",
    "false_edge": "aresta falsa — o citante nem lista o artigo na bibliografia",
}


def render_fantasmas():
    fa = DADOS["fantasmas_auditados"]
    n_intext = DADOS["eixos"]["pooled"]["presence"]["in_text"]["n"]
    n_ghost = DADOS["eixos"]["pooled"]["presence"]["reference_list_only"]["n"]
    n_class = DADOS["meta"]["n_classificados"]
    parts = [
        (
            "<p style='font-size:.9rem;color:var(--ink2);max-width:70ch;margin:14px 0 18px'>"
            f"Das {n_class} citações classificadas, {n_intext} aparecem no corpo do texto e {n_ghost} só na "
            "lista de referências. Cada uma dessas citações-fantasma foi reexaminada individualmente contra "
            "o texto em disco, para separar fantasma genuíno de falha de extração ou corpo indisponível "
            "(<span class='mono'>audit_67_ghost_audit.py</span>).</p>"
        )
    ]
    if is_pendente(fa):
        parts.append(pending_note(fa))
    else:
        summary = fa["summary"]
        cat_rows = "".join(
            f"<tr><td class='v'>{esc(CAT_PT.get(k, k))}</td><td class='n'>{v}</td></tr>"
            for k, v in summary["counts_by_category"].items()
        )
        parts.append(
            "<h3 class='sub'>As citações-fantasma, por categoria</h3>"
            "<div class='scroll'><table class='tbl'><tr><th>Categoria</th><th class='n'>N</th></tr>"
            f"{cat_rows}</table></div>"
        )

        gr = summary["ghost_rate"]
        gr_rows = []
        for k in ("D_read", "D_pop", "D_body"):
            g = gr.get(k)
            if not g:
                continue
            rate = "-" if g["rate"] is None else f"{round(g['rate'] * 100)}%"
            gr_rows.append(
                f"<tr><td class='v'>{esc(g['denominator_label'])}</td>"
                f"<td class='n'>{g['numerator']}/{g['denominator']}</td><td class='n'>{rate}</td></tr>"
            )
        parts.append(
            "<h3 class='sub'>Taxa de fantasma genuíno, por denominador</h3>"
            "<div class='scroll'><table class='tbl'><tr><th>Denominador</th>"
            "<th class='n'>Genuínas / total</th><th class='n'>Taxa</th></tr>"
            f"{''.join(gr_rows)}</table></div>"
        )

        entries = sorted(fa["entries"].values(), key=lambda e: (e["paper"], e["id"]))
        erows = "".join(
            f"<tr><td class='v mono'>{esc(e['id'])}</td><td>{PAPER_PT.get(e['paper'], e['paper'])}</td>"
            f"<td class='v'>{esc(e.get('venue') or '?')}</td><td>{esc(e.get('quartil_scimago') or '–')}</td>"
            f"<td>{esc(CAT_PT.get(e['category'], e['category']))}</td></tr>"
            for e in entries
        )
        parts.append(
            "<h3 class='sub'>As 12 citações-fantasma, uma a uma</h3>"
            "<div class='scroll'><table class='tbl'><tr><th>ID</th><th>Artigo</th><th>Veículo</th>"
            f"<th>Quartil</th><th>Categoria</th></tr>{erows}</table></div>"
        )

    cd = DADOS["cd"]
    cd_rows = []
    cd_pend = []
    for paper in PAPERS:
        block = cd[paper]
        ra = block["refs_audit"]
        if is_pendente(ra):
            cd_pend.append(
                pending_note(ra, f"auditoria de referências ({PAPER_PT[paper]})")
            )
        else:
            cd_rows.append(
                f"<tr><td class='v'>{PAPER_PT[paper]}</td><td class='n'>{ra['n_openalex_raw']}</td>"
                f"<td class='n'>{ra['n_pdf']}</td><td class='n'>{ra['n_valid']}</td>"
                f"<td class='n'>{ra['n_false_references']}</td><td class='n'>{ra['n_unresolvable']}</td></tr>"
            )
        if is_pendente(block["cd_index"]):
            cd_pend.append(
                pending_note(
                    block["cd_index"],
                    f"índice de distância de citação ({PAPER_PT[paper]})",
                )
            )
    if cd_rows:
        parts.append(
            "<h3 class='sub'>Auditoria das referências dos dois artigos</h3>"
            "<p style='font-size:.9rem;color:var(--ink2);max-width:70ch'>Cada referência da bibliografia "
            "dos dois artigos, conferida contra o PDF: quantas o OpenAlex lista, quantas têm PDF, quantas "
            "são válidas, quantas são referência falsa (não existe no PDF real) e quantas não foi possível "
            "resolver.</p>"
            "<div class='scroll'><table class='tbl'><tr><th>Artigo</th><th class='n'>OpenAlex (bruto)</th>"
            "<th class='n'>Com PDF</th><th class='n'>Válidas</th><th class='n'>Falsas</th>"
            f"<th class='n'>Não resolvidas</th></tr>{''.join(cd_rows)}</table></div>"
        )
    parts.extend(cd_pend)

    cocit = DADOS["cocitacao"]
    if is_pendente(cocit):
        parts.append(pending_note(cocit, "co-citação"))

    return f'<section class="funnel">\n <h2>Fantasmas auditados, citação por citação</h2>\n {"".join(parts)}\n</section>'


def render_alegacoes():
    al = DADOS["alegacoes"]
    total = al["total"]
    tipo_rows = "".join(
        f"<tr><td class='v'>{esc(k)}</td><td class='n'>{v}</td></tr>"
        for k, v in sorted(al["por_type"].items())
    )
    status_rows = "".join(
        f"<tr><td class='v'>{esc(k)}</td><td class='n'>{v}</td></tr>"
        for k, v in sorted(al["por_status"].items())
    )
    claims = sorted(al["claims"].items())
    crows = "".join(
        f"<tr><td class='v mono'>{esc(cid)}</td><td>{PAPER_PT.get(c['paper'], c['paper'])}</td>"
        f"<td>{esc(c['type'])}</td><td>{esc(c['status'])}</td><td class='n'>{c['n_citations']}</td>"
        f"<td class='n'>{c['n_faithful']}</td><td class='n'>{c['n_imprecise']}</td>"
        f"<td class='n'>{c['n_misrepresented']}</td></tr>"
        for cid, c in claims
    )
    return f"""<section class="funnel">
 <h2>O que cada artigo afirma, e como foi citado</h2>
 <p style="font-size:.9rem;color:var(--ink2);max-width:70ch;margin:14px 0 18px">
 As {total} afirmações extraídas dos dois artigos (achado, método, dado, definição ou política) e
 quantas vezes cada uma foi citada — fielmente, com imprecisão ou deturpada. Uma afirmação com 0
 citações nunca foi retomada por quem cita o artigo.</p>
 <div class="rgrid">
  <div class='rcol'><h3>Por tipo</h3><table class='tbl'><tr><th>Tipo</th><th class='n'>N</th></tr>{tipo_rows}</table></div>
  <div class='rcol'><h3>Por status</h3><table class='tbl'><tr><th>Status</th><th class='n'>N</th></tr>{status_rows}</table></div>
 </div>
 <div class="scroll" style="margin-top:26px"><table class="tbl"><tr><th>ID</th><th>Artigo</th><th>Tipo</th>
 <th>Status</th><th class="n">Citações</th><th class="n">Fiel</th><th class="n">Impreciso</th>
 <th class="n">Deturpado</th></tr>{crows}</table></div>
</section>"""


def render_anexo():
    items = DADOS["inventario_classificados"]
    rows = []
    for it in items:
        reuse = ", ".join(REUSE.get(t, t) for t in (it.get("reuse") or [])) or "–"
        depth = it.get("depth")
        rows.append(
            f"<tr><td class='v mono'>{esc(it['id'])}</td><td>{PAPER_PT.get(it['paper'], it['paper'])}</td>"
            f"<td class='v'>{esc(it['veiculo_norm'])}</td><td class='n'>{it.get('ano') or '–'}</td>"
            f"<td>{esc(it.get('quartil') or '–')}</td>"
            f"<td>{esc(PRESENCE_PT.get(it['presence'], it['presence']))}</td>"
            f"<td>{esc(PT.get(depth, depth) if depth else '–')}</td>"
            f"<td>{esc(STANCE.get(it.get('stance'), (it.get('stance') or '–', ''))[0])}</td>"
            f"<td>{esc(ACCURACY_PT.get(it.get('accuracy'), it.get('accuracy') or '–'))}</td>"
            f"<td>{esc(reuse)}</td>"
            f"<td>{esc(RELATION_PT.get(it.get('relation'), it.get('relation')))}</td>"
            f"<td>{esc(HIGHLIGHT_PT.get(it.get('highlight'), it.get('highlight')))}</td></tr>"
        )
    return f"""<section class="funnel">
 <h2>Anexo — todas as citações classificadas</h2>
 <p style="font-size:.9rem;color:var(--ink2);max-width:70ch;margin:14px 0 18px">
 As {len(items)} citações com evidência, uma linha cada, para conferência linha a linha contra
 <span class="mono">data/classify.json</span>.</p>
 <div class="scroll"><table class="tbl"><tr><th>ID</th><th>Artigo</th><th>Veículo</th><th class="n">Ano</th>
 <th>Quartil</th><th>Presença</th><th>Profundidade</th><th>Postura</th><th>Fidelidade</th><th>Reuso</th>
 <th>Relação</th><th>Destaque</th></tr>{"".join(rows)}</table></div>
</section>"""


IRR_SECTION = render_irr()
TAXA_BASE_SECTION = render_taxa_base()
FANTASMAS_SECTION = render_fantasmas()
ALEGACOES_SECTION = render_alegacoes()
ANEXO_SECTION = render_anexo()


# --------------------------------------------------------------------------
# KPIs do topo e status do inventário (Método e limites) -- de dados.json
# (inventario, meta, eixos)
# --------------------------------------------------------------------------

INV = DADOS["inventario"]
TOT = leaf_val(INV["total"])
NDOI = leaf_val(INV["com_doi"]["total"])
NCL = DADOS["meta"]["n_classificados"]
PCT_CL = round(100 * NCL / NDOI) if NDOI else 0

_eixos_pooled = DADOS["eixos"]["pooled"]
N_SELF_COAUTOR = (
    _eixos_pooled["relation"]["self"]["n"] + _eixos_pooled["relation"]["coauthor"]["n"]
)
N_MIS = _eixos_pooled["accuracy"]["misrepresented"]["n"]
N_GHOST = _eixos_pooled["presence"]["reference_list_only"]["n"]
# KPI "reuso metodológico externo": só vínculo independente (folha dedicada do
# audit_70); a soma por tag incluiria autocitação e coautoria.
N_REUSE = _eixos_pooled["reuse_externo"]["n"]


def st(status):
    return INV["por_status"].get(status, 0)


_scholar = DADOS["meta"]["scholar"]
_scholar_casados = sum(_scholar[p]["casados"] for p in PAPERS)
_scholar_novos = sum(_scholar[p]["novos"] for p in PAPERS)
_scholar_so_sem_doi = st("so_scholar_sem_doi")
_scholar_resolvidos = _scholar_novos - _scholar_so_sem_doi


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
h3.sub{margin-top:34px;font-size:.78rem;text-transform:uppercase;letter-spacing:.12em;
 font-family:"IBM Plex Sans",sans-serif;color:var(--ink3)}
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

.pending{font-size:.82rem;color:var(--ink2);background:var(--tint-warn);
 border-left:3px solid var(--warn);padding:10px 14px;margin:14px 0}
.pending b{color:var(--warn);text-transform:uppercase;letter-spacing:.04em;font-size:.72rem}

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
.tbl td.v.mono{font-family:"IBM Plex Mono",monospace;font-size:.76rem}
.scroll{overflow-x:auto}
@media (max-width:640px){.wrap{padding:34px 18px 70px}.e-head{flex-direction:column;gap:9px}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""


HTML = f"""<title>Quem Cita Bendinelli</title>
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
  <div class="kpi"><b>{PCT_CL}%</b><span>das {NDOI} com DOI, verificadas</span></div>
  <div class="kpi"><b>{N_REUSE}</b><span>com reuso metodológico externo</span></div>
  <div class="kpi"><b>{N_SELF_COAUTOR}</b><span>autocitação ou coautor</span></div>
  <div class="kpi hl"><b>{N_MIS}</b><span>atribuições incorretas</span></div>
  <div class="kpi hl"><b>{N_GHOST}</b><span>citações-fantasma</span></div>
 </div>
</header>
<section class="funnel">
 <h2>De {SCHOLAR_TOTAL} citações no Scholar até as que dão para ler</h2>
 <p style="font-size:.9rem;color:var(--ink2);max-width:70ch;margin:14px 0 0">
 Cada degrau retira um grupo pelo motivo declarado. A população do estudo é o
 penúltimo degrau: artigo de periódico, de editora estabelecida, com DOI — {POPULACAO_TOTAL}
 citações ao todo. O último degrau mostra quanto dessa população já tem a passagem citante em mãos.</p>
 <div class="fgrid">{FUNIS}</div>
 <h2 style="margin-top:54px">Onde as citações estão, e como cada revista cita</h2>
 <p style="font-size:.9rem;color:var(--ink2);max-width:70ch;margin:14px 0 18px">
 Cada quadrado é uma citação, colorida pelo papel: verde escuro fundacional,
 verde sustenta, azul menção real, cinza menção breve ou de passagem,
 cinza-claro só na bibliografia, vermelho interpretado errado. A última coluna conta
 quantas adotaram método, dado ou resultado.</p>
 <div class="rgrid">{REVISTAS}</div>
 <h3 class="sub">E ao longo do tempo, desde a publicação de cada artigo</h3>
 <div class="fgrid">{LINHA_TEMPO}</div>
</section>
<section class="funnel">
 <h2>A qualidade dos veículos que citam</h2>
 <p style="font-size:.9rem;color:var(--ink2);max-width:70ch;margin:14px 0 22px">
 Quartil oficial do Scimago (SJR Best Quartile, edição {SCIMAGO_EDITION}), casado por ISSN.
 {PERIODICOS_CASADOS} dos {PERIODICOS_TOTAL} periódicos citantes com evidência têm quartil; os demais são
 repositório de preprint, série de conferência ou periódico regional
 fora do Scopus.</p>
 <div class="fgrid">{QBARS}</div>
 <h3 class="sub">Papel da citação por quartil do periódico</h3>
 <div style="margin-top:12px">{QMATRIZ}</div>
 <div class="grid2" style="margin-top:30px">
  <p style="font-size:.9rem;color:var(--ink2)"><b>O engajamento de fundo se concentra no topo.</b>
  {FOUND_Q1} das {FOUND_TOT} citações fundacionais estão em Q1, e {REUSE_Q1} das {REUSE_TOT} que adotam
  método, dado ou resultado também. Quem lê a fundo publica em revista boa.</p>
  <p style="font-size:.9rem;color:var(--ink2)"><b>Mas citação-fantasma não é doença de revista fraca.</b>
  {GHOST_Q1} das {GHOST_TOT} estão em Q1 — entre elas <i>Transportation Research Part E</i>,
  <i>Communications Earth &amp; Environment</i> e <i>Journal of Transport Geography</i>. Listar na
  bibliografia sem citar no texto acontece em periódico de primeira linha.</p>
 </div>
 <h3 class="sub">Cobertura de evidência por quartil (todas as citações com quartil oficial, classificadas ou não)</h3>
 <div style="margin-top:12px">{COBERTURA_TBL}</div>
 <h3 class="sub">Por editora, união dos dois artigos</h3>
 <div style="margin-top:12px">{EDITORAS_TBL}</div>
</section>
{"".join(sections)}
{IRR_SECTION}
{TAXA_BASE_SECTION}
{FANTASMAS_SECTION}
{ALEGACOES_SECTION}
{ANEXO_SECTION}
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
    <tr><td>Só página de rosto</td><td class="n">{st("texto_parcial") + st("evidencia_insuficiente") + st("texto_incorreto")}</td></tr>
    <tr><td>OA com verificação anti-bot</td><td class="n">{st("oa_antibot")}</td></tr>
    <tr><td>OA não recuperado</td><td class="n">{st("oa_bloqueado") + st("oa_baixavel")}</td></tr>
    <tr><td>Fechado</td><td class="n">{st("fechado")}</td></tr>
    <tr><td>Só no Scholar, sem DOI</td><td class="n">{st("so_scholar_sem_doi") + st("sem_doi")}</td></tr>
   </table></div>
  </div>
 </div>
 <p style="margin-top:24px"><b>O inventário está fechado.</b> Às quatro APIs somaram-se as listas
 completas de "cited by" do Google Scholar ({DADOS["meta"]["scholar"]["airline"]["listadas"]} e
 {DADOS["meta"]["scholar"]["grains"]["listadas"]}), paginadas manualmente. O Scholar confirmou
 {_scholar_casados} registros que as APIs já tinham e acrescentou {_scholar_novos}; em contrapartida, as
 APIs acharam registros que o Scholar não lista. A união dá <b>{TOT}</b> — mais do que qualquer fonte
 sozinha. Dos {_scholar_novos} exclusivos do Scholar, {_scholar_resolvidos} foram resolvidos a DOI via
 Crossref; os {_scholar_so_sem_doi} restantes são tese, capítulo de livro e periódico sem DOI depositado.</p>
</section>
</div>"""

nbytes = len(HTML.encode("utf-8"))
if ARGS.check:
    atual = OUT.read_text(encoding="utf-8") if OUT.exists() else None
    if atual != HTML:
        atual_bytes = len(atual.encode("utf-8")) if atual is not None else 0
        print(
            f"DRIFT: reports/01-impacto/index.html gerado difere do commitado "
            f"({nbytes} bytes gerados vs {atual_bytes} commitados)"
        )
        sys.exit(1)
    print(
        f"ok: reports/01-impacto/index.html idêntico ao gerado ({nbytes} bytes | {TOT} citacoes | {NCL} classificadas)"
    )
else:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(HTML, encoding="utf-8")
    print("ok", nbytes, "bytes |", TOT, "citacoes |", NCL, "classificadas")
