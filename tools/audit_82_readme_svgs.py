#!/usr/bin/env python3
"""Capa VITA e diagramas didáticos do README, com versões para celular.

Cada diagrama explica uma ideia. Detalhes de implementação ficam em tools/README.md.
Somente capa e funil exibem medidas; todas vêm de dados.json, gerado por audit_70.
--check regenera em memória e compara as saídas sem escrever.
"""

import argparse
import json
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = SCRIPT_ROOT / "docs/assets"
VITA = json.loads((Path(__file__).parent / "vita_tokens.json").read_text())
P = VITA["palette"]
BG, CARD, INK, GRAY, BORDER = (
    P["composition"],
    P["canvas"],
    P["ink"],
    P["muted"],
    P["line"],
)
SANS = "Inter, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"


def esc(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def T(x, y, s, size=24, weight=400, fill=INK, anchor="start", spacing=None):
    tracking = f' letter-spacing="{spacing}"' if spacing else ""
    return f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{tracking}>{esc(s)}</text>'


def rect(x, y, w, h, fill, stroke=None, rx=20):
    edge = f' stroke="{stroke}" stroke-width="1.5"' if stroke else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{edge}/>'


def lines(x, y, texts, size=24, fill=GRAY, weight=400, leading=34):
    return "\n".join(
        T(x, y + i * leading, s, size=size, fill=fill, weight=weight)
        for i, s in enumerate(texts)
    )


def start(title, description, w, h):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{esc(title)}</title><desc id="desc">{esc(description)}</desc>',
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="none" stroke="#606060" stroke-width="1.5"/></marker></defs>',
        rect(0, 0, w, h, BG, rx=28),
    ]


def arrow(x1, y1, x2, y2):
    return f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{GRAY}" stroke-width="2" marker-end="url(#arrow)"/>'


def heading(out, kicker, title, mobile=False):
    out.append(
        T(40 if mobile else 56, 56, kicker, size=17, weight=500, fill=GRAY, spacing="2")
    )
    out.append(
        lines(
            40 if mobile else 56,
            111,
            title,
            size=36 if mobile else 44,
            fill=INK,
            weight=500,
            leading=44 if mobile else 54,
        )
    )


def finish(out):
    return "\n".join([*out, "</svg>"])


def build_capa_svg(dados):
    """Capa editorial VITA: hierarquia neutra e números apenas de dados.json."""
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="740" viewBox="0 0 1600 740" role="img" aria-labelledby="title desc">',
        '<title id="title">Quem citou, e como — auditoria de citações</title>',
        '<desc id="desc">Leitura da qualidade das citações, com contagens do snapshot atual, em uma composição neutra do design VITA.</desc>',
        rect(0, 0, 1600, 740, BG, rx=28),
        T(64, 74, "SAPIANS / PESQUISA", size=21, weight=500, spacing="2.5"),
        T(1536, 74, dados["meta"]["gerado_em"], size=19, fill=GRAY, anchor="end"),
        T(64, 212, "Quem citou,", size=106, weight=500, spacing="-4"),
        T(64, 324, "e como.", size=106, weight=500, spacing="-4"),
        T(
            68,
            397,
            "Uma leitura da qualidade das citações recebidas.",
            size=29,
            fill=GRAY,
        ),
        T(
            68,
            439,
            "Passagens verificáveis. Critérios explícitos. Resultados reproduzíveis.",
            size=25,
            fill=GRAY,
        ),
    ]
    # Geometria editorial: não codifica estatística nem imita um gráfico de dados.
    for i, (label, fill) in enumerate(
        (("CITAÇÃO", "#E5E5E5"), ("EVIDÊNCIA", "#B8B8B8"), ("LEITURA", INK))
    ):
        x = 1140 + i * 125
        out.extend(
            [
                rect(x, 162, 98, 190, fill, rx=18),
                T(x + 49, 385, label, size=13, fill=GRAY, anchor="middle", spacing="1"),
            ]
        )
    metrics = (
        (dados["inventario"]["total"], "registros mapeados"),
        (dados["meta"]["n_classificados"], "leituras com passagem"),
        (dados["populacao"]["total"], "citações na população"),
    )
    for i, (value, label) in enumerate(metrics):
        x = 64 + i * 500
        out.extend(
            [
                rect(x, 520, 472, 146, CARD, rx=20),
                T(x + 26, 589, str(value), size=53, weight=500),
                T(x + 26, 632, label, size=22, fill=GRAY),
            ]
        )
    out.append(
        T(
            68,
            709,
            "Fonte: dados.json · audit_70 · valores e denominadores detalhados no relatório",
            size=15,
            fill=GRAY,
        )
    )
    out.append("</svg>")
    return "\n".join(out)


def build_capa_mobile_svg(dados):
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="900" viewBox="0 0 640 900" role="img" aria-labelledby="title desc">',
        '<title id="title">Quem citou, e como</title>',
        '<desc id="desc">Resumo do inventário e das leituras com passagem no snapshot atual.</desc>',
        rect(0, 0, 640, 900, BG, rx=26),
        T(40, 62, "SAPIANS / PESQUISA", size=20, weight=500, spacing="2"),
        T(40, 184, "Quem citou,", size=84, weight=500, spacing="-3"),
        T(40, 276, "e como.", size=84, weight=500, spacing="-3"),
        T(42, 340, "Uma leitura da qualidade", size=28, fill=GRAY),
        T(42, 378, "das citações recebidas.", size=28, fill=GRAY),
    ]
    for i, (value, label) in enumerate(
        (
            (dados["inventario"]["total"], "registros mapeados"),
            (dados["meta"]["n_classificados"], "leituras com passagem"),
            (dados["populacao"]["total"], "citações na população"),
        )
    ):
        y = 436 + i * 128
        out.extend(
            [
                rect(40, y, 560, 108, CARD, rx=18),
                T(64, y + 69, str(value), size=50, weight=500),
                T(196, y + 65, label, size=24, fill=GRAY),
            ]
        )
    out.append(
        T(
            42,
            862,
            f"Snapshot {dados['meta']['gerado_em']} · audit_70",
            size=19,
            fill=GRAY,
        )
    )
    out.append("</svg>")
    return "\n".join(out)


def build_pipeline_svg(mobile=False):
    w, h = (640, 1120) if mobile else (1440, 640)
    out = start(
        "Da citação ao resultado verificável",
        "Reunir registros, conferir evidência, ler a passagem e gerar resultados. Texto indisponível permanece pendente.",
        w,
        h,
    )
    heading(
        out,
        "COMO A ANÁLISE ACONTECE",
        ["Da citação ao", "resultado verificável"]
        if mobile
        else ["Da citação ao resultado verificável"],
        mobile,
    )
    steps = [
        ("Reunir registros", ["Cruzar bases e listas.", "Deduplicar as obras."]),
        (
            "Conferir a evidência",
            ["Confirmar o documento", "e conferir o corpo."],
        ),
        ("Ler a passagem", ["Confrontar a passagem", "com o artigo original."]),
        ("Gerar resultados", ["Derivar os números", "e gerar as figuras."]),
    ]
    for i, (title, detail) in enumerate(steps):
        x, y, cw, ch = (
            (40, 230 + i * 168, 560, 140) if mobile else (56 + i * 340, 215, 308, 220)
        )
        out += [
            rect(x, y, cw, ch, CARD),
            T(x + 22, y + 45, title, size=25, weight=500),
            lines(x + 22, y + 87, detail, size=22, leading=32),
        ]
        if i < len(steps) - 1:
            out.append(
                arrow(x + cw / 2, y + ch + 4, x + cw / 2, y + ch + 22)
                if mobile
                else arrow(x + cw + 6, y + ch / 2, x + cw + 23, y + ch / 2)
            )
    y = 950 if mobile else 490
    out += [
        rect(
            40 if mobile else 56,
            y,
            560 if mobile else 1328,
            112 if mobile else 92,
            CARD,
            stroke=BORDER,
        ),
        lines(
            62 if mobile else 80,
            y + 37,
            ["Sem texto suficiente?", "Registrar pendência e buscar evidência."]
            if mobile
            else [
                "Texto indisponível permanece na fila de pendências; a qualidade da citação fica sem julgamento."
            ],
            size=23,
            leading=34,
        ),
    ]
    return finish(out)


def build_funil_svg(dados, mobile=False):
    w, h = (640, 1180) if mobile else (1440, 910)
    out = start(
        "Do inventário à leitura",
        "O inventário reúne fontes diferentes. Os cortes aninhados começam no inventário, não na lista do Scholar. A população é DOI, editora estabelecida e artigo de periódico.",
        w,
        h,
    )
    heading(
        out,
        "O ALCANCE DE CADA CORTE",
        ["O que foi mapeado", "e o que pôde ser lido"]
        if mobile
        else ["O que foi mapeado e o que pôde ser lido"],
        mobile,
    )
    if mobile:
        out.append(
            lines(
                40,
                211,
                [
                    "Origem: APIs + listas locais do Scholar.",
                    "Os cortes começam no inventário.",
                ],
                size=22,
                leading=31,
            )
        )
        top, row_h, label_x, xcols, bar_w = 343, 130, 40, (40, 342), 258
        out += [
            T(40, 304, "AVIAÇÃO", size=18, fill=GRAY, spacing="1"),
            T(342, 304, "GRÃOS", size=18, fill=GRAY, spacing="1"),
        ]
    else:
        out.append(
            T(
                56,
                164,
                "Origem: união das APIs com as listas locais do Scholar. Os cortes começam no inventário reunido.",
                size=23,
                fill=GRAY,
            )
        )
        top, row_h, label_x, xcols, bar_w = 297, 95, 80, (630, 1010), 290
        out += [
            T(630, 233, "AVIAÇÃO", size=19, fill=GRAY, spacing="1"),
            T(1010, 233, "GRÃOS", size=19, fill=GRAY, spacing="1"),
        ]
    labels = [
        "Inventário reunido",
        "Com DOI",
        "Editora estabelecida",
        "Artigo de periódico",
        "Com classificação",
    ]
    for i, label in enumerate(labels):
        y = top + i * row_h
        if not mobile:
            out.append(
                rect(56, y - 39, 1328, 78, CARD, stroke=INK if i == 3 else None, rx=14)
            )
        if mobile and i == 3:
            label += " · população"
        out.append(T(label_x, y, label, size=25, weight=500))
        if i == 3 and not mobile:
            out.append(T(400, y, "população", size=21, fill=GRAY))
        for x, key in zip(xcols, ("airline", "grains")):
            steps = dados["funil"][key]["steps"]
            value, base = steps[i + 1]["valor"], steps[1]["valor"]
            bar_y = y + 22 if mobile else y - 12
            tx = x + bar_w if mobile else x + bar_w + 48
            out += [
                rect(x, bar_y, bar_w, 13, P["selected"], rx=5),
                rect(
                    x,
                    bar_y,
                    bar_w * value / base,
                    13,
                    INK if i >= 3 else P["control"],
                    rx=5,
                ),
                T(
                    tx,
                    bar_y + 46 if mobile else y + 4,
                    str(value),
                    size=28,
                    weight=500,
                    anchor="end",
                ),
            ]
    note_y = 1043 if mobile else 810
    out.append(
        lines(
            40 if mobile else 56,
            note_y,
            [
                "População: DOI + editora estabelecida",
                "+ artigo de periódico.",
                "Leitura é o subconjunto com evidência.",
                "Barras: fração de cada inventário.",
            ]
            if mobile
            else [
                "População: DOI + editora estabelecida + artigo de periódico. Leitura é o subconjunto com evidência.",
                "Barras: fração do inventário de cada artigo.",
            ],
            size=22,
            leading=32,
        )
    )
    return finish(out)


QUESTIONS = [
    ("Presença", "Onde aparece?", "No corpo, nas referências ou ausente."),
    ("Profundidade", "Quanto foi usado?", "Da menção ao apoio do argumento."),
    ("Postura", "Qual é a posição?", "Apoia, contrapõe ou só menciona."),
    ("Exatidão", "O original diz isso?", "Confronto com o artigo-fonte."),
    ("Reuso", "O que foi adotado?", "Método, dado ou resultado verificável."),
]


def build_taxonomia_svg(mobile=False):
    w, h = (640, 1170) if mobile else (1440, 850)
    out = start(
        "Uma citação, perguntas separadas",
        "Presença, profundidade, postura, exatidão e reuso são julgados independentemente. Apoio não garante exatidão.",
        w,
        h,
    )
    heading(
        out,
        "COMO CADA CITAÇÃO É LIDA",
        ["Uma citação,", "perguntas separadas"]
        if mobile
        else ["Uma citação, perguntas separadas"],
        mobile,
    )
    for i, (label, question, detail) in enumerate(QUESTIONS):
        y = (224 + i * 158) if mobile else (202 + i * 105)
        out.append(
            rect(
                40 if mobile else 56,
                y,
                560 if mobile else 1328,
                140 if mobile else 87,
                CARD,
            )
        )
        if mobile:
            out += [
                T(62, y + 32, label, size=20, weight=500, fill=GRAY),
                T(62, y + 72, question, size=29, weight=500),
                T(62, y + 111, detail, size=23, fill=GRAY),
            ]
        else:
            out += [
                T(80, y + 52, label, size=25, weight=500),
                T(360, y + 52, question, size=29, weight=500),
                T(800, y + 52, detail, size=23, fill=GRAY),
            ]
    out.append(
        lines(
            40 if mobile else 56,
            1074 if mobile else 784,
            ["Cada eixo tem sua própria resposta.", "O veredito combina as evidências."]
            if mobile
            else [
                "Postura de apoio e exatidão são julgadas separadamente. O veredito combina as evidências."
            ],
            size=23,
            leading=34,
        )
    )
    return finish(out)


def build_portoes_svg(mobile=False):
    w, h = (640, 1230) if mobile else (1440, 900)
    out = start(
        "Quando a evidência permite classificar",
        "Texto correto, corpo disponível e presença verificada são conferidos antes do julgamento. Falta de corpo é pendência. Ausência confirmada manualmente é aresta falsa.",
        w,
        h,
    )
    heading(
        out,
        "OS PORTÕES DA EVIDÊNCIA",
        ["Quando é possível", "classificar uma citação"]
        if mobile
        else ["Quando é possível classificar uma citação"],
        mobile,
    )
    gates = [
        ("Texto correto", ["Confere com o título", "do documento citante."]),
        ("Corpo disponível", ["Página de rosto", "não comprova o corpo."]),
        ("Presença verificada", ["Busca no corpo", "e nas referências."]),
    ]
    for i, (label, detail) in enumerate(gates):
        x, y, cw, ch = (
            (40, 225 + i * 158, 560, 134) if mobile else (56 + i * 452, 208, 424, 178)
        )
        out += [
            rect(x, y, cw, ch, CARD),
            T(x + 22, y + 42, label, size=28, weight=500),
            lines(x + 22, y + 82, detail, size=23, leading=32),
        ]
        if i < 2:
            out.append(
                arrow(x + cw / 2, y + ch + 2, x + cw / 2, y + ch + 19)
                if mobile
                else arrow(x + cw + 5, y + ch / 2, x + cw + 21, y + ch / 2)
            )
    outcomes = [
        ("Evidência recuperada", "Classificar e preservar a passagem."),
        ("Corpo indisponível", "Registrar pendência; obter o texto."),
        ("Ausência confirmada", "Veredito manual: aresta falsa."),
    ]
    for i, (label, detail) in enumerate(outcomes):
        y = (730 + i * 112) if mobile else (452 + i * 106)
        out += [
            rect(
                40 if mobile else 56,
                y,
                560 if mobile else 1328,
                94 if mobile else 88,
                CARD,
                stroke=BORDER,
            ),
            T(
                62 if mobile else 80,
                y + 35 if mobile else y + 53,
                label,
                size=25,
                weight=500,
            ),
            T(
                62 if mobile else 590,
                y + 72 if mobile else y + 53,
                detail,
                size=22,
                fill=GRAY,
            ),
        ]
    out.append(
        lines(
            40 if mobile else 56,
            1125 if mobile else 828,
            [
                "Só nas referências? O corpo completo",
                "é necessário para confirmar fantasma.",
            ]
            if mobile
            else [
                "Somente nas referências é achado de fantasma apenas com corpo completo comprovado."
            ],
            size=22,
            leading=32,
        )
    )
    return finish(out)


def render_all(dados):
    outputs = {
        "00-capa.svg": build_capa_svg(dados),
        "00-capa-mobile.svg": build_capa_mobile_svg(dados),
    }
    builders = {
        "01-pipeline": build_pipeline_svg,
        "02-funil": lambda mobile: build_funil_svg(dados, mobile),
        "03-taxonomia": build_taxonomia_svg,
        "04-portoes": build_portoes_svg,
    }
    for name, fn in builders.items():
        outputs[f"{name}.svg"] = fn(False)
        outputs[f"{name}-mobile.svg"] = fn(True)
    return outputs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=SCRIPT_ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    dados = json.loads((args.root / "reports/01-impacto/dados.json").read_text())
    outputs = render_all(dados)
    if args.check:
        drift = [
            name
            for name, content in outputs.items()
            if not (OUT_DIR / name).exists()
            or (OUT_DIR / name).read_text() != content + "\n"
        ]
        if drift:
            print("DRIFT: " + ", ".join(drift))
            return 1
        print(f"ok --check: {len(outputs)} SVGs idênticos ao gerado")
        return 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        (OUT_DIR / name).write_text(content + "\n")
    print(f"ok: {len(outputs)} SVGs gerados em {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
