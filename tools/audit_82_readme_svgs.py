#!/usr/bin/env python3
"""Etapa 82: os quatro diagramas SVG didáticos do README.

Gera, à mão (string templating, sem biblioteca de desenho), quatro SVGs
conceituais que explicam a auditoria a quem abre o README pela primeira vez:

  docs/assets/01-pipeline.svg   -- as fases dos scripts tools/audit_NN_*.py
  docs/assets/02-funil.svg      -- o funil de população dos dois artigos
  docs/assets/03-taxonomia.svg  -- os eixos ortogonais da taxonomia v2
  docs/assets/04-portoes.svg    -- os três portões de integridade + aresta_falsa

Só o funil (02) tem número -- e todo número dele vem de
`reports/01-impacto/dados.json` (blocos `funil` e `populacao`), gerado por
`audit_70_numbers.py`. Os outros três são conceituais: descrevem a forma do
pipeline, da taxonomia e dos portões, não uma medição, então não têm
estatística nenhuma para citar (números estruturais como o código da fase --
"10", "20"... -- ou o nome de um arquivo não são "número quantitativo em
prosa" no sentido da regra do CLAUDE.md: são identificadores fixos do
repositório, não uma contagem derivada dos dados).

Uso:
  python3 tools/audit_82_readme_svgs.py                  grava os quatro SVGs
  python3 tools/audit_82_readme_svgs.py --check            renderiza em memória
                                                             e compara byte a
                                                             byte com os
                                                             arquivos commitados
                                                             (nunca grava; sai 1
                                                             se houver diferença)
  python3 tools/audit_82_readme_svgs.py --root PATH        raiz onde ler
                                                             reports/01-impacto/
                                                             dados.json (padrão:
                                                             inferida de __file__)

Os arquivos de saída vivem sempre em <pasta do próprio script>/../docs/assets/
-- independente de --root. Isso deixa ler dados de um lugar (ex.: um
repositório só de leitura) e gravar em outro (ex.: um diretório de stage) -- mesma
convenção de `tools/audit_70_numbers.py` (ver o cabeçalho de lá).
"""

import argparse
import sys
import textwrap
from pathlib import Path

# --------------------------------------------------------------------------
# Caminhos -- mesma convenção de tools/audit_70_numbers.py
# --------------------------------------------------------------------------

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = SCRIPT_ROOT / "docs" / "assets"
DADOS_REL = Path("reports") / "01-impacto" / "dados.json"

OUT_FILES = ("01-pipeline.svg", "02-funil.svg", "03-taxonomia.svg", "04-portoes.svg")

# --------------------------------------------------------------------------
# Paleta SAPIANS e tipografia (dialeto compartilhado com outros repositórios
# SAPIANS -- ver docs/assets/*.svg de sapians-xreset e sapians-engram)
# --------------------------------------------------------------------------

BG = "#FBF9F6"
INK = "#161311"
GRAY = "#6D675F"
BLUE = "#315B86"  # via principal / o que fica
TERRACOTTA = "#C96F3F"  # anomalia ou destaque único
AMBER = "#D9822B"  # atenção / literatura
SAGE = "#4E8752"  # o que passou / foi aproveitado
CARD = "#FFFFFF"
BORDER = "#E4DFD7"
GRAY_SOFT = "#EDE9E2"  # preenchimento neutro leve (barras "resto" do funil)

SANS = "Inter, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', SFMono-Regular, Menlo, monospace"

W, H = 1600, 980
MARGIN = 48
CONTENT_W = W - 2 * MARGIN

# fatores empíricos de largura média por caractere (fração do font-size),
# usados só para decidir quebra de linha -- não há motor de fonte disponível
# neste gerador, então a largura é estimada, não medida; a checagem visual
# final (Read sobre o SVG) é o que valida de fato.
SANS_CHAR = 0.53
MONO_CHAR = 0.60


# ==========================================================================
# Helpers de baixo nível
# ==========================================================================


def esc(s):
    """Escapa texto para uso seguro dentro de elemento ou atributo XML."""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def text_width(s, size, mono=False):
    factor = MONO_CHAR if mono else SANS_CHAR
    return len(s) * size * factor


def wrap_words(s, size, max_w, mono=False):
    """Quebra por palavra até caber em max_w no tamanho size. Nunca quebra
    uma palavra ao meio -- se uma palavra sozinha for larga demais, ela
    ocupa a linha inteira mesmo assim (ver fit_mono para nomes de arquivo)."""
    factor = MONO_CHAR if mono else SANS_CHAR
    max_chars = max(3, int(max_w / (size * factor)))
    return textwrap.wrap(s, width=max_chars, break_long_words=False) or [s]


def fit_mono(name, size, max_w):
    """Ajusta um nome de arquivo (mono, sem espaço) a max_w: se não couber
    numa linha, quebra depois do '_' mais próximo do meio -- resultado em
    até duas linhas. Usado só quando a largura do cartão não foi suficiente
    (rede de segurança; o layout normal já dimensiona a fonte para caber)."""
    if text_width(name, size, mono=True) <= max_w:
        return [name]
    idxs = [i for i, c in enumerate(name) if c == "_"]
    if not idxs:
        return [name]
    mid = len(name) / 2
    best = min(idxs, key=lambda i: abs(i - mid))
    return [name[: best + 1], name[best + 1 :]]


def T(
    x, y, s, size=22, weight=400, fill=INK, family=None, anchor="start", spacing=None
):
    fam = family or SANS
    ls = f' letter-spacing="{spacing}"' if spacing is not None else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{ls}>{esc(s)}</text>'
    )


def multi(
    x, y, lines, size=22, weight=400, fill=INK, family=None, anchor="start", lh=None
):
    lh = lh if lh is not None else size * 1.32
    return "\n".join(
        T(x, y + i * lh, line, size, weight, fill, family, anchor)
        for i, line in enumerate(lines)
    )


def rect(x, y, w, h, fill, stroke=None, rx=20, sw=1.5, extra=""):
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"{st} {extra}/>'.strip()


def card(x, y, w, h, fill=CARD, stroke=BORDER, rx=20, shadow=True):
    f = ' filter="url(#cardShadow)"' if shadow else ""
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"{f}/>'


def harrow(x1, y1, x2, y2, color=GRAY, sw=2.5, marker="arrow", dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<path d="M{x1:.1f} {y1:.1f} L{x2:.1f} {y2:.1f}" stroke="{color}" stroke-width="{sw}" fill="none" marker-end="url(#{marker})"{d}/>'


def vline_dashed(x, y1, y2, color=GRAY, sw=1.5):
    return f'<line x1="{x:.1f}" y1="{y1:.1f}" x2="{x:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{sw}" stroke-dasharray="4 5" opacity="0.6"/>'


def circle_dot(cx, cy, r, fill):
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{fill}"/>'


DEFS = f"""<defs>
  <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
    <path d="M0,0 L10,5 L0,10 Z" fill="{GRAY}"/>
  </marker>
  <marker id="arrowBlue" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
    <path d="M0,0 L10,5 L0,10 Z" fill="{BLUE}"/>
  </marker>
  <marker id="arrowAmber" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
    <path d="M0,0 L10,5 L0,10 Z" fill="{AMBER}"/>
  </marker>
  <marker id="arrowTerra" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
    <path d="M0,0 L10,5 L0,10 Z" fill="{TERRACOTTA}"/>
  </marker>
  <marker id="arrowSage" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
    <path d="M0,0 L10,5 L0,10 Z" fill="{SAGE}"/>
  </marker>
  <filter id="cardShadow" x="-10%" y="-10%" width="120%" height="130%">
    <feDropShadow dx="0" dy="3" stdDeviation="5" flood-color="{INK}" flood-opacity="0.10"/>
  </filter>
</defs>"""


def svg_open(title, desc):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="{SANS}" role="img" aria-labelledby="title desc">\n'
        f"<title>{esc(title)}</title>\n"
        f"<desc>{esc(desc)}</desc>\n"
        f"{DEFS}\n"
        f'<rect width="{W}" height="{H}" fill="{BG}"/>'
    )


SVG_CLOSE = "</svg>"


def header(kicker, title, subtitle=None, badge=None):
    parts = [
        T(MARGIN, 54, kicker, size=15, weight=700, fill=GRAY, spacing="1.6"),
        T(MARGIN, 96, title, size=34, weight=700, fill=INK),
    ]
    if subtitle:
        parts.append(T(MARGIN, 128, subtitle, size=20, weight=400, fill=GRAY))
    if badge:
        bw, bh = 372, 56
        bx, by = W - MARGIN - bw, 30
        parts.append(
            card(bx, by, bw, bh, fill=CARD, stroke=BORDER, rx=14, shadow=False)
        )
        parts.append(
            T(
                bx + 20,
                by + 22,
                badge[0],
                size=11.5,
                weight=700,
                fill=GRAY,
                spacing="1.2",
            )
        )
        parts.append(T(bx + 20, by + 42, badge[1], size=14, weight=600, fill=INK))
    return "\n".join(parts)


def footer_band(line, y, h=52, fill=BLUE, txt="#FBF9F6", size=19):
    return (
        rect(MARGIN, y, CONTENT_W, h, fill, rx=14)
        + "\n"
        + T(
            W / 2,
            y + h / 2 + 6.5,
            line,
            size=size,
            weight=700,
            fill=txt,
            anchor="middle",
        )
    )


def legend_row(items, x, y, size=15.5, dot=6.5):
    """items: lista de (cor, rótulo). Distribui da esquerda, cada item com
    largura proporcional ao seu próprio texto (não a uma grade fixa)."""
    out = []
    cx = x
    for color, label in items:
        out.append(circle_dot(cx + dot, y, dot, color))
        out.append(
            T(
                cx + dot * 2 + 10,
                y + size * 0.35,
                label,
                size=size,
                weight=600,
                fill=GRAY,
            )
        )
        cx += dot * 2 + 10 + text_width(label, size) + 34
    return "\n".join(out)


# ==========================================================================
# SVG 01 -- pipeline das fases tools/audit_NN_*.py
# ==========================================================================

# Cada entrada: (nome_arquivo, tag) -- tag None (script commitado e em uso),
# "reservado" (nome reservado no ROADMAP.md, arquivo ainda não escrito) ou
# "este script" (é o próprio audit_82_readme_svgs.py gerando este SVG).
PHASES = [
    {
        "code": "10",
        "nome": "COLHEITA",
        "gloss": "Monta e funde o grafo de citações",
        "scripts": [
            ("audit_10_harvest.py", None),
            ("audit_11_triage.py", None),
            ("audit_12_merge_scholar.py", None),
            ("audit_13_resolve_scholar.py", None),
        ],
        "nota": None,
    },
    {
        "code": "20",
        "nome": "TEXTO",
        "gloss": "Baixa e extrai o texto de cada citante",
        "scripts": [
            ("audit_20_download.py", None),
            ("audit_21_download_deep.py", None),
            ("audit_22_retry_all.py", None),
        ],
        "nota": "Unpaywall · download direto · leitura por SSO manual",
    },
    {
        "code": "30",
        "nome": "INTEGRIDADE",
        "gloss": "Três portões validam texto e passagem",
        "scripts": [
            ("audit_30_validate_texts.py", None),
            ("audit_31_passages.py", None),
            ("audit_32_gate_bibonly.py", None),
        ],
        "nota": None,
    },
    {
        "code": "40",
        "nome": "PERIÓDICOS",
        "gloss": "Metadados do veículo citante e o tier",
        "scripts": [
            ("audit_40_journals.py", None),
            ("audit_41_scimago.py", None),
        ],
        "nota": "tier = quartil Scimago oficial",
    },
]

PHASE_50 = {
    "code": "50",
    "nome": "PENDÊNCIAS",
    "gloss": "Deriva CSVs de trabalho do estado atual",
    "scripts": [("audit_50_pending.py", None)],
    "nota": None,
}

PHASE_60_SHIPPED = [
    ("audit_60_taxonomy_v2.py", None),
    ("audit_61_irr_pack.py", None),
    ("audit_62_irr_stats.py", None),
    ("audit_63_adjudicate.py", None),
    ("audit_67_ghost_audit.py", None),
    ("audit_68_base_rates.py", None),
]
PHASE_60_RESERVED = [
    ("audit_63_claim_map.py", "reservado"),
    ("audit_64_refs_audit.py", "reservado"),
    ("audit_65_cd_index.py", "reservado"),
    ("audit_66_cocitation.py", "reservado"),
]

PHASE_70 = {
    "code": "70",
    "nome": "NÚMEROS",
    "gloss": "Única fonte de todo número em prosa",
    "scripts": [("audit_70_numbers.py", None)],
    "nota": "dados.json · numeros.txt",
}

PHASE_80 = {
    "code": "80",
    "nome": "SAÍDAS",
    "gloss": "Relatório HTML, figuras, SVGs, Typst",
    "scripts": [
        ("audit_80_report_html.py", None),
        ("audit_81_figures.py", "reservado"),
        ("audit_82_readme_svgs.py", "este script"),
    ],
    "nota": "+ typst compile → relatorio-impacto.pdf",
}


def phase_title_block(x, y, w, code, nome, title_size=29):
    """Título do cartão: 'FASE NN · NOME'. Quando não cabe numa linha só
    (cartões estreitos com nome de fase longo), quebra em duas: 'FASE NN' /
    'NOME' -- devolve também quantas linhas usou, para quem chama empurrar o
    resto do conteúdo para baixo."""
    label = f"FASE {code} · {nome}"
    if text_width(label, title_size) <= w:
        return T(x, y, label, size=title_size, weight=700, fill=INK), 1
    line1 = T(x, y, f"FASE {code}", size=title_size, weight=700, fill=INK)
    line2 = T(x, y + title_size * 1.18, nome, size=title_size, weight=700, fill=INK)
    return line1 + "\n" + line2, 2


def script_chip_lines(x, y, w, scripts, size, lh, pad_left=16):
    """Uma linha mono por script, com tag opcional (reservado / este script)
    em texto pequeno colorido à direita, quando couber; senão, abaixo."""
    out = []
    cy = y
    for name, tag in scripts:
        lines = fit_mono(name, size, w - pad_left - 8)
        color = GRAY if tag == "reservado" else (BLUE if tag == "este script" else INK)
        dash = ' stroke-dasharray="3 3"' if tag == "reservado" else ""
        out.append(
            f'<rect x="{x:.1f}" y="{cy - size:.1f}" width="7" height="7" rx="2" '
            f'fill="none" stroke="{color}" stroke-width="1.6"{dash}/>'
        )
        for li, line in enumerate(lines):
            out.append(
                T(
                    x + pad_left,
                    cy + li * (size * 1.05),
                    line,
                    size=size,
                    weight=500,
                    fill=color,
                    family=MONO,
                )
            )
        cy += lh * len(lines)
        if tag:
            out.append(
                T(x + pad_left, cy - 2, f"({tag})", size=13.5, weight=600, fill=GRAY)
            )
            cy += 17
    return "\n".join(out), cy


def build_phase_card(x, y, w, h, code, nome, gloss, scripts, nota=None, mono_size=17.5):
    out = [card(x, y, w, h)]
    pad = 22
    title_svg, title_lines = phase_title_block(x + pad, y + 40, w - 2 * pad, code, nome)
    out.append(title_svg)
    title_extra = 34 if title_lines > 1 else 0
    gloss_lines = wrap_words(gloss, 20, w - 2 * pad)
    gy = y + 68 + title_extra
    out.append(multi(x + pad, gy, gloss_lines, size=20, weight=400, fill=GRAY, lh=25))
    gy += 25 * len(gloss_lines) + 12
    lines_svg, end_y = script_chip_lines(
        x + pad, gy + 18, w - 2 * pad, scripts, mono_size, mono_size * 1.55
    )
    out.append(lines_svg)
    if nota:
        note_lines = wrap_words(nota, 15, w - 2 * pad)
        ny = max(end_y + 6, y + h - 18 - 16 * (len(note_lines) - 1))
        out.append(
            multi(x + pad, ny, note_lines, size=14.5, weight=600, fill=GRAY, lh=18)
        )
    return "\n".join(out)


def build_phase_card_60(x, y, w, h):
    """Cartão largo da fase 60, com duas colunas: entregues (sólido) e
    reservados (contorno tracejado, nome ainda não escrito -- ver ROADMAP.md).
    """
    out = [card(x, y, w, h)]
    pad = 22
    title_svg, title_lines = phase_title_block(
        x + pad, y + 40, w - 2 * pad, "60", "ANÁLISES"
    )
    out.append(title_svg)
    gloss = "Taxonomia, confiabilidade, fantasmas, taxas-base"
    gloss_lines = wrap_words(gloss, 20, w - 2 * pad)
    gy = y + 68 + (34 if title_lines > 1 else 0)
    out.append(multi(x + pad, gy, gloss_lines, size=20, weight=400, fill=GRAY, lh=25))
    col_w = (w - 2 * pad - 28) / 2
    col1_x = x + pad
    col2_x = x + pad + col_w + 28
    top = gy + 25 * len(gloss_lines) + 30
    out.append(
        T(
            col1_x,
            top - 12,
            "ENTREGUES",
            size=12.5,
            weight=700,
            fill=SAGE,
            spacing="1.3",
        )
    )
    out.append(
        T(
            col2_x,
            top - 12,
            "RESERVADOS · ROADMAP.md",
            size=12.5,
            weight=700,
            fill=GRAY,
            spacing="1.1",
        )
    )
    s1, _ = script_chip_lines(col1_x, top + 16, col_w, PHASE_60_SHIPPED, 17.5, 24)
    s2, _ = script_chip_lines(col2_x, top + 16, col_w, PHASE_60_RESERVED, 17.5, 24)
    out.append(s1)
    out.append(s2)
    return "\n".join(out)


def build_pipeline_svg():
    title = "Pipeline de auditoria: das APIs ao README"
    desc = (
        "Oito fases de scripts tools/audit_NN_*.py, da colheita do grafo de "
        "citações às saídas finais. Cada nome de script mostrado existe de "
        "fato no repositório; os marcados 'reservado' têm nome reservado no "
        "ROADMAP.md mas o arquivo ainda não foi escrito."
    )
    out = [svg_open(title, desc)]
    out.append(
        header(
            "CITATION-AUDIT · PIPELINE",
            title,
            "Um script por fase, biblioteca compartilhada em auditlib.py — nomes reais de tools/README.md.",
        )
    )

    row1_y, row1_h = 180, 290
    gap = 20
    col_w = (CONTENT_W - 3 * gap) / 4
    xs = [MARGIN + i * (col_w + gap) for i in range(4)]
    for ph, x in zip(PHASES, xs):
        out.append(
            build_phase_card(
                x,
                row1_y,
                col_w,
                row1_h,
                ph["code"],
                ph["nome"],
                ph["gloss"],
                ph["scripts"],
                ph.get("nota"),
            )
        )
    for i in range(3):
        xa = xs[i] + col_w
        xb = xs[i + 1]
        ymid = row1_y + row1_h / 2
        out.append(harrow(xa + 4, ymid, xb - 4, ymid, color=BLUE, marker="arrowBlue"))

    row2_y, row2_h = row1_y + row1_h + 46, 310
    w50, w60, w70, w80 = 250, 604, 250, 340
    x50 = MARGIN
    x60 = x50 + w50 + gap
    x70 = x60 + w60 + gap
    x80 = x70 + w70 + gap

    out.append(
        build_phase_card(
            x50,
            row2_y,
            w50,
            row2_h,
            PHASE_50["code"],
            PHASE_50["nome"],
            PHASE_50["gloss"],
            PHASE_50["scripts"],
            PHASE_50.get("nota"),
        )
    )
    out.append(build_phase_card_60(x60, row2_y, w60, row2_h))
    out.append(
        build_phase_card(
            x70,
            row2_y,
            w70,
            row2_h,
            PHASE_70["code"],
            PHASE_70["nome"],
            PHASE_70["gloss"],
            PHASE_70["scripts"],
            PHASE_70.get("nota"),
        )
    )
    out.append(
        build_phase_card(
            x80,
            row2_y,
            w80,
            row2_h,
            PHASE_80["code"],
            PHASE_80["nome"],
            PHASE_80["gloss"],
            PHASE_80["scripts"],
            PHASE_80.get("nota"),
        )
    )

    for xa, xb in ((x50 + w50, x60), (x60 + w60, x70), (x70 + w70, x80)):
        ymid = row2_y + row2_h / 2
        out.append(harrow(xa + 4, ymid, xb - 4, ymid, color=BLUE, marker="arrowBlue"))

    # curva ligando o fim da fileira 1 (fase 40) ao início da fileira 2 (fase 50)
    x_end = xs[3] + col_w / 2
    y_end = row1_y + row1_h
    x_start = x50 + w50 / 2
    y_start = row2_y
    mid_y = (y_end + y_start) / 2
    out.append(
        f'<path d="M{x_end:.1f} {y_end:.1f} L{x_end:.1f} {mid_y:.1f} L{x_start:.1f} {mid_y:.1f} '
        f'L{x_start:.1f} {y_start - 2:.1f}" stroke="{GRAY}" stroke-width="2.5" fill="none" '
        f'marker-end="url(#arrow)" stroke-dasharray="1 0"/>'
    )
    out.append(
        T(
            (x_end + x_start) / 2,
            mid_y - 10,
            "continua",
            size=14,
            weight=600,
            fill=GRAY,
            anchor="middle",
        )
    )

    legend_y = row2_y + row2_h + 34
    out.append(
        legend_row(
            [
                (INK, "script commitado, em uso"),
                (
                    GRAY,
                    "reservado — nome existe no ROADMAP.md, arquivo ainda não escrito",
                ),
                (BLUE, "este script (audit_82), gerando os quatro SVGs agora"),
            ],
            MARGIN,
            legend_y,
        )
    )

    foot_y = legend_y + 30
    out.append(
        footer_band(
            "Todo número quantitativo em prosa é impresso por um script versionado commitado.",
            foot_y,
        )
    )
    out.append(SVG_CLOSE)
    return "\n".join(out)


# ==========================================================================
# SVG 02 -- funil de população dos dois artigos (único com números)
# ==========================================================================


def build_funil_svg(dados):
    funil = dados["funil"]
    pop = dados["populacao"]
    artigos = dados["artigos"]

    title = "Do que o Scholar reporta à evidência verificada"
    desc = (
        "Funil de seis passos para os dois artigos auditados. O passo "
        "'periódico' é a população do estudo; 'com evidência verificada' é "
        "o que entrou em data/classify.json. Valores lidos de "
        "reports/01-impacto/dados.json (blocos funil e populacao), gerados "
        "por audit_70_numbers.py -- nenhum dígito deste diagrama foi digitado "
        "à mão."
    )
    out = [svg_open(title, desc)]
    out.append(
        header(
            "CITATION-AUDIT · FUNIL DE POPULAÇÃO",
            title,
            "Mesmos seis passos para os dois artigos — a população do estudo é o passo “periódico”.",
        )
    )

    panel_w = (CONTENT_W - 40) / 2
    panels = [
        ("airline", MARGIN),
        ("grains", MARGIN + panel_w + 40),
    ]

    panel_top = 158
    row_h = 77
    bar_h = 24
    track_frac = 0.80  # fração da largura do painel que representa o passo 0 (100%)

    # rastreia o ponto mais baixo realmente usado por qualquer coluna, para
    # posicionar o card de população depois sem supor de antemão quantas
    # linhas o título de cada artigo vai quebrar (título maior = mais alto).
    content_bottom = panel_top

    for key, px in panels:
        art = artigos[key]
        steps = funil[key]["steps"]
        linhas = funil["linhas"]
        base_val = steps[0]["valor"]
        track_w = panel_w * track_frac
        scale = track_w / base_val

        out.append(
            T(
                px,
                panel_top,
                key.upper(),
                size=13.5,
                weight=700,
                fill=GRAY,
                spacing="1.6",
            )
        )
        titulo_lines = wrap_words(art["titulo"], 18.5, panel_w)[:2]
        out.append(
            multi(
                px, panel_top + 23, titulo_lines, size=18.5, weight=700, fill=INK, lh=22
            )
        )
        veic_y = panel_top + 23 + 22 * len(titulo_lines) + 15
        out.append(
            T(
                px,
                veic_y,
                f"{art['veiculo']} · {art['ano']}",
                size=14.5,
                weight=500,
                fill=GRAY,
            )
        )

        bars_top = veic_y + 24
        # linha-guia tracejada no marco de 100% (largura do passo 0)
        out.append(
            vline_dashed(px + track_w, bars_top - 8, bars_top + row_h * len(steps) - 20)
        )
        out.append(
            T(
                px + track_w,
                bars_top - 15,
                "100% do passo 0",
                size=12,
                weight=600,
                fill=GRAY,
                anchor="middle",
            )
        )

        for i, step in enumerate(steps):
            y = bars_top + i * row_h
            rotulo = step["rotulo"]
            valor_txt = linhas[i][f"{key}_txt"]
            if i == 4:
                color = BLUE
            elif i == 5:
                color = SAGE
            else:
                color = GRAY
            out.append(T(px, y, rotulo, size=17.5, weight=600, fill=INK))
            out.append(
                T(
                    px + panel_w,
                    y,
                    valor_txt,
                    size=17.5,
                    weight=700,
                    fill=color,
                    anchor="end",
                )
            )

            bar_y = y + 9
            bar_px = max(6, step["valor"] * scale)
            out.append(
                rect(
                    px,
                    bar_y,
                    min(bar_px, panel_w),
                    bar_h,
                    GRAY_SOFT if color == GRAY else color,
                    rx=6,
                )
            )
            if bar_px > panel_w:
                out.append(
                    T(
                        px + panel_w - 6,
                        bar_y + bar_h + 14,
                        "ultrapassa — valor exato à esquerda",
                        size=11.5,
                        weight=600,
                        fill=GRAY,
                        anchor="end",
                    )
                )
            if color == GRAY:
                out.append(
                    rect(
                        px,
                        bar_y,
                        min(bar_px, panel_w),
                        bar_h,
                        "none",
                        stroke=GRAY,
                        rx=6,
                        sw=1.2,
                    )
                )

        bottom_here = bars_top + row_h * len(steps)
        if key == "grains":
            note_y = bottom_here + 6
            out.append(
                T(
                    px,
                    note_y,
                    "O inventário (passo 2) supera o Scholar: a união de fontes acha mais — não é erro.",
                    size=14,
                    weight=500,
                    fill=GRAY,
                )
            )
            bottom_here = note_y + 10
        content_bottom = max(content_bottom, bottom_here)

    callout_y = content_bottom + 28
    callout_h = 70
    out.append(
        card(MARGIN, callout_y, CONTENT_W, callout_h, fill=CARD, stroke=BLUE, rx=16)
    )
    out.append(
        T(
            MARGIN + 26,
            callout_y + 32,
            "População do estudo (METHOD.md §9): DOI + editora estabelecida + artigo de periódico",
            size=19,
            weight=700,
            fill=INK,
        )
    )
    out.append(
        T(
            MARGIN + 26,
            callout_y + 58,
            f"{pop['total']} citações — {pop['airline']} do artigo de aviação + {pop['grains']} do de grãos (populacao.total/airline/grains, dados.json)",
            size=16.5,
            weight=500,
            fill=GRAY,
        )
    )

    legend_y = callout_y + callout_h + 34
    out.append(
        legend_row(
            [
                (GRAY, "passos intermediários"),
                (BLUE, "periódico — a população do estudo"),
                (SAGE, "com evidência verificada"),
            ],
            MARGIN,
            legend_y,
        )
    )

    foot_y = legend_y + 30
    out.append(
        footer_band(
            "Todo número deste funil vem de reports/01-impacto/dados.json — nenhum dígito digitado à mão.",
            foot_y,
        )
    )
    out.append(SVG_CLOSE)
    return "\n".join(out)


# ==========================================================================
# SVG 03 -- taxonomia v2, eixos ortogonais (METHOD.md §16)
# ==========================================================================


def build_taxonomia_svg():
    title = "Seis dimensões da leitura de uma citação"
    desc = (
        "Os eixos ortogonais da taxonomia v2 (METHOD.md §16): presence, "
        "depth, stance, accuracy com os subcódigos de distorção de "
        "Greenberg, reuse e o campo auxiliar relation. Cada eixo é "
        "codificado à parte; o veredito de uma citação é a tupla dos "
        "valores, combinada por regra -- não uma média numa escala única."
    )
    out = [svg_open(title, desc)]
    out.append(
        header(
            "CITATION-AUDIT · TAXONOMIA V2",
            title,
            "METHOD.md §16 — cada eixo é lido separado; o veredito final combina os seis por regra, não por média.",
        )
    )

    pad = 22
    x0 = MARGIN

    # -------- Linha 1: PRESENCE (tira estreita) --------
    row1_y, row1_h = 176, 108
    out.append(card(x0, row1_y, CONTENT_W, row1_h))
    out.append(
        T(x0 + pad, row1_y + 32, "EIXO 1 · PRESENCE", size=20, weight=700, fill=INK)
    )
    out.append(
        T(
            x0 + pad,
            row1_y + 56,
            "onde o artigo aparece no citante",
            size=15.5,
            weight=500,
            fill=GRAY,
        )
    )
    presence = [
        ("in_text", "no corpo do texto", SAGE, CARD, True),
        ("reference_list_only", "só na lista de referências", AMBER, CARD, False),
        ("not_cited", "não aparece em lugar nenhum", GRAY, CARD, False),
    ]
    pchip_w, pchip_h, pgap = 372, 70, 18
    px = x0 + CONTENT_W - pad - (pchip_w * 3 + pgap * 2)
    py = row1_y + (row1_h - pchip_h) / 2
    in_text_cx = None
    for i, (code, gloss, accent, bgc, _) in enumerate(presence):
        cx = px + i * (pchip_w + pgap)
        out.append(rect(cx, py, pchip_w, pchip_h, bgc, stroke=accent, rx=12, sw=2))
        out.append(
            T(cx + 16, py + 27, code, size=18, weight=700, fill=accent, family=MONO)
        )
        out.append(T(cx + 16, py + 50, gloss, size=14.5, weight=500, fill=GRAY))
        if code == "in_text":
            in_text_cx = cx + pchip_w / 2

    # -------- Linha 2: DEPTH (escada ordinal) --------
    row2_y, row2_h = row1_y + row1_h + 26, 168
    out.append(card(x0, row2_y, CONTENT_W, row2_h))
    out.append(
        T(x0 + pad, row2_y + 32, "EIXO 2 · DEPTH", size=20, weight=700, fill=INK)
    )
    out.append(
        T(
            x0 + pad,
            row2_y + 56,
            "quanto o artigo importou para quem citou — escala ordinal, só quando presence = in_text",
            size=15.5,
            weight=500,
            fill=GRAY,
        )
    )
    depth_vals = [
        "drive_by",
        "brief_mention",
        "real_mention",
        "supporting",
        "foundational",
    ]
    n = len(depth_vals)
    dgap = 16
    dchip_w = (CONTENT_W - 2 * pad - (n - 1) * dgap) / n
    dtop = row2_y + 76
    dmax_h = 66
    # conector do chip in_text até o início da escada
    if in_text_cx:
        out.append(
            harrow(
                in_text_cx,
                row1_y + row1_h + 4,
                x0 + pad + dchip_w / 2,
                row2_y - 4,
                color=SAGE,
                marker="arrowSage",
            )
        )
    blue_ramp = ["#c3d4e2", "#9fb8d0", "#6f93b8", "#45719c", BLUE]
    for i, code in enumerate(depth_vals):
        cx = x0 + pad + i * (dchip_w + dgap)
        ch = dmax_h * (0.62 + 0.38 * i / (n - 1))
        cy = dtop + (dmax_h - ch)
        fill_c = blue_ramp[i]
        txt_c = "#FFFFFF" if i >= 2 else INK
        out.append(rect(cx, cy, dchip_w, ch, fill_c, rx=10))
        lbl_lines = fit_mono(code, 16.5, dchip_w - 16)
        ly = cy + ch - 14 - 18 * (len(lbl_lines) - 1)
        for li, line in enumerate(lbl_lines):
            out.append(
                T(
                    cx + dchip_w / 2,
                    ly + li * 18,
                    line,
                    size=16.5,
                    weight=700,
                    fill=txt_c,
                    family=MONO,
                    anchor="middle",
                )
            )
        if i < n - 1:
            out.append(
                harrow(
                    cx + dchip_w + 2,
                    dtop + dmax_h + 6,
                    cx + dchip_w + dgap - 2,
                    dtop + dmax_h + 6,
                    color=GRAY,
                    sw=2,
                )
            )
    out.append(
        T(
            x0 + pad,
            dtop + dmax_h + 34,
            "drive_by → foundational: quanto mais escuro, mais fundo o uso.",
            size=14,
            weight=500,
            fill=GRAY,
        )
    )

    # -------- Linha 3: STANCE + ACCURACY + DISTORTION --------
    row3_y, row3_h = row2_y + row2_h + 26, 224
    seg_gap = 20
    seg_w = (CONTENT_W - 2 * seg_gap) / 3
    sx1 = x0
    sx2 = x0 + seg_w + seg_gap
    sx3 = x0 + 2 * (seg_w + seg_gap)

    # STANCE
    out.append(card(sx1, row3_y, seg_w, row3_h))
    out.append(
        T(sx1 + pad, row3_y + 32, "EIXO 3 · STANCE", size=19, weight=700, fill=INK)
    )
    out.append(
        T(
            sx1 + pad,
            row3_y + 54,
            "postura do citante",
            size=14.5,
            weight=500,
            fill=GRAY,
        )
    )
    stance_vals = [
        ("none", "sem postura declarada"),
        ("supporting", "a favor do citado"),
        ("contradictory", "contesta o citado"),
    ]
    sy = row3_y + 78
    for code, gloss in stance_vals:
        out.append(rect(sx1 + pad, sy, 8, 8, "none", stroke=BLUE, rx=2, sw=1.6))
        out.append(
            T(
                sx1 + pad + 18,
                sy + 8,
                code,
                size=16.5,
                weight=700,
                fill=INK,
                family=MONO,
            )
        )
        out.append(T(sx1 + pad + 18, sy + 27, gloss, size=13.5, weight=500, fill=GRAY))
        sy += 44

    # ACCURACY
    out.append(card(sx2, row3_y, seg_w, row3_h))
    out.append(
        T(sx2 + pad, row3_y + 32, "EIXO 4 · ACCURACY", size=19, weight=700, fill=INK)
    )
    out.append(
        T(
            sx2 + pad,
            row3_y + 54,
            "o citante diz o que o artigo diz?",
            size=14.5,
            weight=500,
            fill=GRAY,
        )
    )
    acc_vals = [
        ("accurate", "corresponde ao artigo", SAGE),
        ("imprecise", "leitura frouxa, ampliada", AMBER),
        ("misrepresented", "o artigo não diz isso", TERRACOTTA),
    ]
    ay = row3_y + 78
    for code, gloss, color in acc_vals:
        out.append(rect(sx2 + pad, ay, 8, 8, color, rx=2))
        out.append(
            T(
                sx2 + pad + 18,
                ay + 8,
                code,
                size=16.5,
                weight=700,
                fill=color,
                family=MONO,
            )
        )
        out.append(T(sx2 + pad + 18, ay + 27, gloss, size=13.5, weight=500, fill=GRAY))
        ay += 44

    # DISTORTION (sub-código, ativo quando accuracy != accurate)
    out.append(card(sx3, row3_y, seg_w, row3_h, stroke=TERRACOTTA))
    out.append(
        T(sx3 + pad, row3_y + 32, "DISTORTION", size=19, weight=700, fill=TERRACOTTA)
    )
    out.append(
        T(
            sx3 + pad,
            row3_y + 54,
            "mecanismo do erro (Greenberg 2009), quando accuracy ≠ accurate",
            size=13,
            weight=500,
            fill=GRAY,
        )
    )
    dist_vals = ["dead_end", "diversion", "transmutation", "relayed_attribution"]
    dw = (seg_w - 2 * pad - 12) / 2
    dh = 46
    dxy0 = (sx3 + pad, row3_y + 74)
    for i, code in enumerate(dist_vals):
        col, rowi = i % 2, i // 2
        dx = dxy0[0] + col * (dw + 12)
        dyv = dxy0[1] + rowi * (dh + 12)
        out.append(rect(dx, dyv, dw, dh, "none", stroke=TERRACOTTA, rx=9, sw=1.4))
        lines = fit_mono(code, 13.5, dw - 14)
        ty = dyv + dh / 2 - 7 * (len(lines) - 1) + 5
        for li, line in enumerate(lines):
            out.append(
                T(
                    dx + dw / 2,
                    ty + li * 15,
                    line,
                    size=13.5,
                    weight=700,
                    fill=TERRACOTTA,
                    family=MONO,
                    anchor="middle",
                )
            )
    # conectores de accuracy (imprecise/misrepresented) até distortion
    out.append(
        harrow(
            sx2 + seg_w - 4,
            row3_y + 78 + 44 * 1 + 2,
            sx3 + 6,
            row3_y + 78 + 34,
            color=AMBER,
            sw=1.8,
            marker="arrowAmber",
            dash="3 3",
        )
    )
    out.append(
        harrow(
            sx2 + seg_w - 4,
            row3_y + 78 + 44 * 2 + 2,
            sx3 + 6,
            row3_y + 78 + 34 + dh + 12,
            color=TERRACOTTA,
            sw=1.8,
            marker="arrowTerra",
            dash="3 3",
        )
    )

    # -------- Linha 4: REUSE + RELATION --------
    row4_y, row4_h = row3_y + row3_h + 26, 150
    ru_w = CONTENT_W * 0.60 - 10
    rl_w = CONTENT_W * 0.40 - 10
    rux = x0
    rlx = x0 + ru_w + 20

    out.append(card(rux, row4_y, ru_w, row4_h))
    out.append(
        T(rux + pad, row4_y + 32, "EIXO 5 · REUSE", size=19, weight=700, fill=INK)
    )
    out.append(
        T(
            rux + pad,
            row4_y + 54,
            "reuso efetivo — multi-rótulo, um citante pode ter mais de um",
            size=14,
            weight=500,
            fill=GRAY,
        )
    )
    reuse_vals = [
        "method_adoption",
        "result_validated",
        "dataset_reuse",
        "benchmarking",
        "work_extended",
    ]
    n2 = len(reuse_vals)
    rgap = 14
    rchip_w = (ru_w - 2 * pad - (n2 - 1) * rgap) / n2
    ry = row4_y + 72
    for i, code in enumerate(reuse_vals):
        cx = rux + pad + i * (rchip_w + rgap)
        out.append(rect(cx, ry, rchip_w, 56, SAGE, rx=10))
        lines = fit_mono(code, 13.5, rchip_w - 14)
        ty = ry + 56 / 2 - 7 * (len(lines) - 1) + 5
        for li, line in enumerate(lines):
            out.append(
                T(
                    cx + rchip_w / 2,
                    ty + li * 15,
                    line,
                    size=13.5,
                    weight=700,
                    fill="#FFFFFF",
                    family=MONO,
                    anchor="middle",
                )
            )

    out.append(card(rlx, row4_y, rl_w, row4_h))
    out.append(T(rlx + pad, row4_y + 32, "RELATION", size=19, weight=700, fill=INK))
    out.append(
        T(
            rlx + pad,
            row4_y + 54,
            "campo auxiliar — vínculo de autoria, não eixo de função",
            size=14,
            weight=500,
            fill=GRAY,
        )
    )
    rel_vals = ["independent", "coauthor", "self"]
    rw3 = (rl_w - 2 * pad - 2 * 14) / 3
    for i, code in enumerate(rel_vals):
        cx = rlx + pad + i * (rw3 + 14)
        out.append(rect(cx, row4_y + 72, rw3, 56, "none", stroke=GRAY, rx=10, sw=1.4))
        out.append(
            T(
                cx + rw3 / 2,
                row4_y + 72 + 34,
                code,
                size=14.5,
                weight=700,
                fill=INK,
                family=MONO,
                anchor="middle",
            )
        )

    foot_y = row4_y + row4_h + 18
    out.append(
        footer_band(
            "Seis valores, seis eixos independentes — o veredito de uma citação é a tupla, combinada por regra, nunca uma média.",
            foot_y,
        )
    )
    out.append(SVG_CLOSE)
    return "\n".join(out)


# ==========================================================================
# SVG 04 -- portões de integridade (METHOD.md §4)
# ==========================================================================


def gate_node(x, y, w, h, num, pergunta):
    out = [card(x, y, w, h, stroke=BLUE)]
    out.append(circle_dot(x + 30, y + 30, 16, BLUE))
    out.append(
        T(x + 30, y + 36, num, size=17, weight=700, fill="#FFFFFF", anchor="middle")
    )
    out.append(T(x + 58, y + 36, f"PORTÃO {num}", size=18.5, weight=700, fill=BLUE))
    lines = wrap_words(pergunta, 16.5, w - 44)
    out.append(multi(x + 22, y + 66, lines, size=16.5, weight=500, fill=INK, lh=22))
    return "\n".join(out)


def outcome_chip(
    x, y, w, h, status, gloss, color, solid=False, max_gloss_lines=2, status_size=18
):
    """Cartão de estado de saída. solid=True (aresta_falsa) pinta o cartão
    inteiro na cor -- é o único veredito manual; os demais (solid=False) são
    contorno colorido sobre fundo branco -- saída automática recalculável."""
    if solid:
        out = [rect(x, y, w, h, color, rx=14)]
        txt_color, gloss_color = "#FFFFFF", "#f7e6dc"
    else:
        out = [rect(x, y, w, h, CARD, stroke=color, rx=14, sw=2)]
        txt_color, gloss_color = color, GRAY
    lines = fit_mono(status, status_size, w - 28)
    ty = y + 30
    for li, line in enumerate(lines):
        out.append(
            T(
                x + w / 2,
                ty + li * 20,
                line,
                size=status_size,
                weight=700,
                fill=txt_color,
                family=MONO,
                anchor="middle",
            )
        )
    gy = ty + 20 * len(lines) + 8
    glines = wrap_words(gloss, 13.5, w - 24)[:max_gloss_lines]
    out.append(
        multi(
            x + w / 2,
            gy,
            glines,
            size=13.5,
            weight=500,
            fill=gloss_color,
            lh=17,
            anchor="middle",
        )
    )
    return "\n".join(out)


def build_portoes_svg():
    title = "Três portões automáticos, mais um veredito manual terminal"
    desc = (
        "Fluxo dos portões de integridade (METHOD.md §4): texto baixado, "
        "portão 1 (título bate), portão 2 (corpo completo), portão 3 "
        "(só-bibliografia exige corpo), e os estados de saída tem_texto, "
        "texto_parcial, texto_incorreto, evidencia_insuficiente e o "
        "veredito manual terminal aresta_falsa, que nenhum portão "
        "sobrescreve."
    )
    out = [svg_open(title, desc)]
    out.append(
        header(
            "CITATION-AUDIT · PORTÕES DE INTEGRIDADE",
            title,
            "METHOD.md §4 — cada portão nasceu de um erro real encontrado nos dados.",
        )
    )

    spine_y = 210
    node_h = 128
    start_w, gate_w, end_w = 176, 336, 220
    gap = 26
    total = start_w + 3 * gate_w + end_w + 4 * gap
    x0 = MARGIN + (CONTENT_W - total) / 2

    xs = [x0]
    xs.append(xs[-1] + start_w + gap)
    xs.append(xs[-1] + gate_w + gap)
    xs.append(xs[-1] + gate_w + gap)
    xs.append(xs[-1] + gate_w + gap)
    x_start, x_g1, x_g2, x_g3, x_end = xs

    # nó inicial
    out.append(card(x_start, spine_y, start_w, node_h, fill=CARD, stroke=GRAY))
    out.append(
        T(
            x_start + start_w / 2,
            spine_y + 50,
            "texto",
            size=19,
            weight=700,
            fill=INK,
            anchor="middle",
        )
    )
    out.append(
        T(
            x_start + start_w / 2,
            spine_y + 76,
            "baixado",
            size=19,
            weight=700,
            fill=INK,
            anchor="middle",
        )
    )
    out.append(
        T(
            x_start + start_w / 2,
            spine_y + 100,
            "text/*.txt",
            size=13.5,
            weight=500,
            fill=GRAY,
            family=MONO,
            anchor="middle",
        )
    )

    out.append(
        gate_node(
            x_g1,
            spine_y,
            gate_w,
            node_h,
            "1",
            "o texto contém o próprio título do registro?",
        )
    )
    out.append(
        gate_node(
            x_g2,
            spine_y,
            gate_w,
            node_h,
            "2",
            "não é só página de rosto/abstract — corpo completo?",
        )
    )
    out.append(
        gate_node(
            x_g3,
            spine_y,
            gate_w,
            node_h,
            "3",
            "“só na bibliografia”: o corpo foi comprovado?",
        )
    )

    # nó final (sucesso nos três portões)
    out.append(rect(x_end, spine_y, end_w, node_h, SAGE, rx=20))
    out.append(
        T(
            x_end + end_w / 2,
            spine_y + 46,
            "tem_texto",
            size=19,
            weight=700,
            fill="#FFFFFF",
            family=MONO,
            anchor="middle",
        )
    )
    out.append(
        multi(
            x_end + end_w / 2,
            spine_y + 70,
            wrap_words("passou nos três portões", 14, end_w - 24),
            size=14,
            weight=600,
            fill="#eaf3ec",
            lh=18,
            anchor="middle",
        )
    )

    ymid = spine_y + node_h / 2
    for xa, xb in (
        (x_start + start_w, x_g1),
        (x_g1 + gate_w, x_g2),
        (x_g2 + gate_w, x_g3),
        (x_g3 + gate_w, x_end),
    ):
        out.append(
            harrow(xa + 4, ymid, xb - 4, ymid, color=BLUE, sw=2.6, marker="arrowBlue")
        )

    # ramos de falha (âmbar) descendo de cada portão -- e, na mesma fileira,
    # aresta_falsa (terracota, cartão sólido): não tem seta vindo da espinha
    # porque não deriva de portão nenhum -- é veredito manual, paralelo ao
    # fluxo automático (ver nota abaixo). Alinhado sob o nó tem_texto: os dois
    # são os "extremos" -- corpo comprovado vs. comprovadamente não citado.
    out_y = spine_y + node_h + 150
    out_h = 118
    out_w = gate_w - 20
    fails = [
        (x_g1 + 10, "texto_incorreto", "arquivo é de outro artigo — desvincula"),
        (x_g2 + 10, "texto_parcial", "página de rosto — não conta como lido"),
        (
            x_g3 + 10,
            "evidencia_insuficiente",
            "rosto de publisher, sem corpo comprovado",
        ),
    ]
    for gx, status, gloss in fails:
        cx = gx + gate_w / 2 - out_w / 2 - 10
        out.append(
            harrow(
                gx + gate_w / 2,
                spine_y + node_h + 4,
                gx + gate_w / 2,
                out_y - 4,
                color=AMBER,
                sw=2.3,
                marker="arrowAmber",
            )
        )
        out.append(outcome_chip(cx, out_y, out_w + 20, out_h, status, gloss, AMBER))

    af_w, af_h = end_w, 150
    af_x, af_y = x_end, out_y
    out.append(
        outcome_chip(
            af_x,
            af_y,
            af_w,
            af_h,
            "aresta_falsa",
            "PDF obtido e verificado — o citante não cita em lugar nenhum",
            TERRACOTTA,
            solid=True,
            max_gloss_lines=3,
            status_size=16.5,
        )
    )
    out.append(
        T(
            af_x + af_w / 2,
            af_y + af_h + 20,
            "manual — não deriva dos portões acima",
            size=12.5,
            weight=700,
            fill=TERRACOTTA,
            anchor="middle",
        )
    )

    note_y = max(out_y + out_h, af_y + af_h + 32) + 48
    out.append(
        multi(
            MARGIN,
            note_y,
            wrap_words(
                "Os portões recalculam status a cada nova coleta — exceto quando já é veredito terminal. Uma rodada antiga sobrescrevia aresta_falsa de volta para tem_texto; os portões agora pulam todo status terminal.",
                17,
                CONTENT_W,
            ),
            size=17,
            weight=500,
            fill=GRAY,
            lh=23,
        )
    )

    legend_y = note_y + 96
    out.append(
        legend_row(
            [
                (BLUE, "portão automático"),
                (AMBER, "saída incompleta — recalculada a cada coleta"),
                (SAGE, "corpo comprovado, passou nos três portões"),
                (TERRACOTTA, "veredito manual terminal"),
            ],
            MARGIN,
            legend_y,
        )
    )

    foot_y = legend_y + 40
    out.append(
        footer_band(
            "aresta_falsa é o único veredito que nenhum portão automático recalcula.",
            foot_y,
        )
    )
    out.append(SVG_CLOSE)
    return "\n".join(out)


# ==========================================================================
# Orquestração
# ==========================================================================


def render_all(dados):
    return {
        "01-pipeline.svg": build_pipeline_svg(),
        "02-funil.svg": build_funil_svg(dados),
        "03-taxonomia.svg": build_taxonomia_svg(),
        "04-portoes.svg": build_portoes_svg(),
    }


def load_dados(root):
    p = root / DADOS_REL
    import json

    return json.loads(p.read_text(encoding="utf-8"))


def parse_args(argv):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--root",
        type=Path,
        default=SCRIPT_ROOT,
        help="raiz onde ler reports/01-impacto/dados.json (padrão: inferida de __file__)",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="renderiza em memória e compara byte a byte com os arquivos commitados; nunca grava; sai 1 se houver diferença",
    )
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    root = args.root.resolve()
    dados = load_dados(root)
    rendered = render_all(dados)

    print(f"-- audit_82_readme_svgs: raiz de dados = {root}")
    print(f"-- {len(rendered)} SVGs renderizados: {', '.join(rendered)}")

    if args.check:
        drift = []
        for name, content in rendered.items():
            p = OUT_DIR / name
            atual = p.read_text(encoding="utf-8") if p.exists() else None
            if atual != content:
                atual_len = len(atual.encode("utf-8")) if atual is not None else 0
                drift.append(
                    f"{name}: {len(content.encode('utf-8'))} bytes gerados vs {atual_len} commitados"
                )
        if drift:
            for d in drift:
                print(f"DRIFT: {d}")
            return 1
        print("ok --check: os quatro SVGs idênticos ao gerado")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, content in rendered.items():
        (OUT_DIR / name).write_text(content, encoding="utf-8")
    print(f"ok: {len(rendered)} SVGs gravados em {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
