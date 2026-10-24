#!/usr/bin/env python3
"""Tema das figuras de citation-audit, alinhado ao design global VITA.

Cores canônicas em tools/vita_tokens.json; Inter e JetBrains Mono são
alternativas OFL para a publicação aberta. Optimistic VF não é redistribuída.
As funções de formatação e dimensões preservam o contrato dos geradores.
"""

from __future__ import annotations

import json
import math
import pathlib

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

try:
    import pandas as pd  # só para _ausente()/tabela(); a fase 81 não usa
except ImportError:  # pragma: no cover
    pd = None
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap, to_hex
from matplotlib.ticker import FuncFormatter, ScalarFormatter

AQUI = pathlib.Path(__file__).resolve().parent
ESTILO = AQUI / "sapians.mplstyle"
FONTES_DIR = AQUI / "fonts"
FONTES = [
    "Inter-Regular.ttf",
    "Inter-Medium.ttf",
    "Inter-SemiBold.ttf",
    "Inter-Bold.ttf",
    "JetBrainsMono-Regular.ttf",
    "JetBrainsMono-Bold.ttf",
]

# ---------------------------------------------------------------------------
# Tokens neutros do design global VITA, fotografados em vita_tokens.json.
# Os nomes antigos são mantidos para compatibilidade com as figuras;
# não representam mais cores cromáticas. Rótulos e marcadores carregam categoria.
# ---------------------------------------------------------------------------
VITA = json.loads((AQUI / "vita_tokens.json").read_text(encoding="utf-8"))
P = VITA["palette"]
PAPEL = P["canvas"]
ESCURO = P["ink"]
CARTAO = P["composition"]
TERRACOTA = P["ink"]  # destaque de dado é neutro; terracota só em ações reais
AZUL = "#454545"
AMBAR = P["control"]
SAGE = "#909090"
CINZA = P["muted"]
CINZA_CLARO = "#B8B8B8"
LINHA = P["line"]
GRADE = P["composition"]
CODIGO = P["subtle"]
CATEGORICA = [ESCURO, CINZA, AMBAR, CINZA_CLARO, P["selected"]]
BINARIA = [CINZA, ESCURO]
SEQ_AZUL = VITA["data_series"]
SEQ_TERRACOTA = SEQ_AZUL
DIVERGENTE = [ESCURO, CINZA_CLARO, PAPEL, CINZA_CLARO, ESCURO]
CMAP_INTENSIDADE = LinearSegmentedColormap.from_list("vita_intensidade", SEQ_AZUL)
CMAP_DIVERGENTE = LinearSegmentedColormap.from_list("vita_divergente", DIVERGENTE)


def rampa(n: int, lo: float = 0.35, cmap=CMAP_INTENSIDADE) -> list[str]:
    """`n` passos hex da rampa, do claro (`lo`) ao escuro (1,0).

    `lo` corta a ponta clara: abaixo de ~0,3 a cor some no papel branco.
    Ordem crescente = intensidade crescente; inverta a lista quando o
    primeiro item for o mais intenso (veja `CORES_ANO`).
    """
    if n < 1:
        raise ValueError("rampa precisa de n >= 1")
    if n == 1:
        return [to_hex(cmap(1.0))]
    return [to_hex(cmap(t)) for t in np.linspace(lo, 1.0, n)]


# Os cinco anos da coorte, do mais escuro ao mais claro. 2020 é o mais
# escuro porque é o regime mais letal: a rampa de intensidade carrega a
# gravidade, e a ordem cronológica cai junto — o aluno lê "vai clareando"
# como "vai ficando menos letal" sem precisar de legenda.
CORES_ANO = dict(zip(range(2020, 2025), reversed(rampa(5))))

# ---------------------------------------------------------------------------
# LINHAS E MARCADORES — tracejado também é vocabulário.
#
# Tracejado faz três trabalhos diferentes no curso e já foi desenhado do
# mesmo jeito nos três, o que fez uma sala ler uma janela de eixo como se
# fosse uma vizinhança. Um traço para cada, o mais escuro para o objeto do
# próprio modelo.
# ---------------------------------------------------------------------------
# (literais e não dict(...): o ruff do repo recusa dict() com chaves fixas)
L_FRONTEIRA = {"color": ESCURO, "linestyle": (0, (4, 3)), "linewidth": 1.2}  # p=0,5
L_KERNEL = {"color": CINZA, "linestyle": (0, (3, 3)), "linewidth": 1.0}  # construto
L_REF = {"color": CINZA_CLARO, "linestyle": (0, (2, 3)), "linewidth": 0.9}  # andaime

# Forma = origem do ponto; cor = o que aquele ponto é.
MARCADOR_REAL = "o"  # círculo: paciente real da base (cor = desfecho observado)
MARCADOR_SINTETICO = "s"  # quadrado: vizinho sintético (cor = predição do modelo)
MARCADOR_PACIENTE = "X"  # ✕: o paciente sendo explicado, sempre em ESCURO

# ---------------------------------------------------------------------------
# TAMANHOS — três, e só três, para que figuras irmãs tenham o mesmo aspecto.
# ---------------------------------------------------------------------------
SLOT = (9.6, 5.4)  # o padrão: um gráfico, 16:9, cabe no slide e na página
FAIXA = (12.0, 4.0)  # faixa larga e baixa: barras horizontais, φ ordenado, séries
PAINEL = (12.0, 8.0)  # painel: small multiples 2x2 / 2x3
DPI = 150  # o DPI do arquivo salvo (savefig.dpi do estilo)
BANDA_TITULO = 0.14  # fração do canvas reservada acima dos eixos numa figura
# titulada — igual em todas, para o vão ler igual
FIGDIR = pathlib.Path("figures_generated")  # relativo ao cwd, como os cadernos

_aplicado = False


def aplicar(*, fontes: bool = True, estilo: bool = True) -> pathlib.Path:
    """Registra as fontes empacotadas, aplica o estilo, garante `figures_generated/`.

    Idempotente: chamar de novo não repete o trabalho. Devolve `FIGDIR`.

    As fontes vêm de `tools/fonts/` por caminho absoluto e NÃO do sistema:
    é o que faz o PNG sair igual no Mac do autor, no runner Linux do CI e
    no Colab. Se um arquivo sumir, isto levanta `FileNotFoundError` —
    falhar alto, porque a alternativa é o matplotlib cair no DejaVu Sans
    sem dizer nada e a figura mudar em todo glifo.
    """
    global _aplicado
    if not _aplicado:
        if fontes:
            faltam = [n for n in FONTES if not (FONTES_DIR / n).is_file()]
            if faltam:
                raise FileNotFoundError(
                    "fontes empacotadas ausentes em "
                    f"{FONTES_DIR}: {', '.join(faltam)} — "
                    "veja tools/fonts/README.md"
                )
            for nome in FONTES:
                font_manager.fontManager.addfont(str(FONTES_DIR / nome))
        if estilo:
            if not ESTILO.is_file():
                raise FileNotFoundError(f"estilo ausente: {ESTILO}")
            plt.style.use(str(ESTILO))
        _aplicado = True
    FIGDIR.mkdir(exist_ok=True)
    return FIGDIR


def titulo(fig, achado: str, kicker: str | None = None, *, x: float = 0.012) -> None:
    """O título diz o ACHADO, não o que o gráfico é.

    "Sobrevida cai 18 p.p. entre a 2ª e a 3ª dose" e não "Predição vs
    doses". O kicker (`§4 · doses`) é a etiqueta de onde a figura vive; o
    achado é a frase que o aluno leva embora.

    `fig.text` e não `ax.set_title`: `set_title` alinha ao eixo, então
    figuras irmãs com rótulos de tamanhos diferentes começam o título em
    x diferentes e a sequência inteira parece torta.
    """
    if kicker:
        fig.text(
            x,
            0.985,
            kicker.upper(),
            ha="left",
            va="top",
            fontsize=8.5,
            fontweight="bold",
            color=TERRACOTA,
        )
        fig.text(
            x,
            0.945,
            achado,
            ha="left",
            va="top",
            fontsize=13,
            fontweight="bold",
            color=ESCURO,
        )
    else:
        fig.text(
            x,
            0.985,
            achado,
            ha="left",
            va="top",
            fontsize=13,
            fontweight="bold",
            color=ESCURO,
        )
    fig._sp_titulado = True


def _tick_pt(v, _pos=None) -> str:
    """Rótulo de eixo em português: inteiro com milhar, decimal com vírgula.

    O número de casas é o menor que reproduz o valor do tick (até 4) — um
    eixo de 0 a 1 em passos de 0,2 mostra "0,2", não "0,2000".
    """
    if abs(v - round(v)) < 1e-9 and abs(v) < 1e15:
        return pt_int(round(v))
    for casas in (1, 2, 3, 4):
        if abs(round(v, casas) - v) < 1e-9:
            return pt(v, casas)
    return pt(v, 4)


def eixos_pt(fig) -> None:
    """Põe os ticks numéricos de todos os eixos da figura em português.

    Só substitui o formatador padrão (`ScalarFormatter`): eixos de
    categorias, datas, percentuais ou log já têm formatador próprio e
    ficam como estão. `axes.formatter.use_locale` faria o mesmo, mas
    dependeria do locale da máquina — e o PNG tem de sair igual em
    qualquer uma.
    """
    for ax in fig.get_axes():
        for eixo in (ax.xaxis, ax.yaxis):
            if type(eixo.get_major_formatter()) is ScalarFormatter:
                eixo.set_major_formatter(FuncFormatter(_tick_pt))


def salvar(
    fig, nome: str, *, rect=None, dpi: int = DPI, ticks_pt: bool = True
) -> pathlib.Path:
    """Salva em `figures_generated/<nome>.png` e devolve o caminho.

    `ticks_pt` passa os ticks numéricos para o português antes de salvar
    (`eixos_pt`); desligue só num eixo que já tem formatador próprio.

    Sem `bbox_inches="tight"`: ele deixa o aspecto do arquivo divergir do
    `figsize`, que é como cinco figuras do mesmo tamanho nominal foram
    parar em cinco alturas diferentes no mesmo slot. O `tight_layout`
    mantém os rótulos dentro do canvas; o `rect` é o que impede o título
    de sentar em cima do gráfico.

    `metadata={"Software": None}` remove o chunk de texto que o matplotlib
    escreveria com a própria versão: sem ele o PNG muda a cada bump da
    biblioteca e o diff mente sobre o que mudou.
    """
    if ticks_pt:
        eixos_pt(fig)
    topo = 1.0 - BANDA_TITULO if getattr(fig, "_sp_titulado", False) else 0.98
    fig.tight_layout(rect=rect or (0.0, 0.0, 1.0, topo))
    FIGDIR.mkdir(exist_ok=True)
    destino = FIGDIR / f"{nome}.png"
    fig.savefig(destino, dpi=dpi, facecolor=PAPEL, metadata={"Software": None})
    print(f"figura: {destino}")
    return destino


def sem_grade(*axes) -> None:
    """Desliga a grade nos eixos dados — dispersões e mapas não a querem."""
    for ax in axes:
        ax.grid(False)


# ---------------------------------------------------------------------------
# NÚMEROS EM PORTUGUÊS — milhar com ponto, decimal com vírgula.
#
# O sinal negativo é o hífen-menos ASCII, nunca U+2212: a prosa e as
# saídas são conferidas por regex (tools/check_numbers.py) e um menos
# tipográfico quebraria a conferência sem melhorar nada.
# ---------------------------------------------------------------------------
_SOBRESCRITO = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")


def _ausente(x) -> bool:
    """True para None, NaN e o `pd.NA` das colunas nullable — tudo vira 'NA'."""
    if x is None:
        return True
    if pd is None:  # sem pandas (fase 81): só None e NaN contam como ausente
        try:
            return math.isnan(float(x))
        except (TypeError, ValueError):
            return False
    try:
        return bool(pd.isna(x))
    except (TypeError, ValueError):
        return False


def pt(x, casas: int = 2, *, sinal: bool = False) -> str:
    """'1.234,57'. NaN vira 'NA'; com `sinal=True`, '+0,92' / '-0,36'."""
    if _ausente(x):
        return "NA"
    v = float(x)
    if np.isinf(v):
        return "∞" if v > 0 else "-∞"
    v = round(v, casas)
    corpo = f"{abs(v):,.{casas}f}".translate(str.maketrans({",": ".", ".": ","}))
    if v < 0:
        return f"-{corpo}"
    return f"+{corpo}" if sinal else corpo


def pt_int(n) -> str:
    """'1.234.567'. Aceita int, inteiro do numpy e float inteiro; NaN vira 'NA'."""
    if _ausente(n):
        return "NA"
    v = float(n)
    if np.isinf(v):
        return "∞" if v > 0 else "-∞"
    if v != int(v):
        raise ValueError(f"pt_int recebeu um não-inteiro: {n!r} — use pt()")
    return f"{int(v):,d}".replace(",", ".")


def pct(x, casas: int = 1, *, fator: float = 100, sinal: bool = False) -> str:
    """'37,3%' a partir de 0,373. Use `fator=1` quando x já vier em pontos %."""
    if _ausente(x):
        return "NA"
    v = float(x)
    return f"{pt(v * fator, casas, sinal=sinal)}%"


def pt_sig(x, sig: int = 2) -> str:
    """'1,05×10⁻⁵' — para valores que só se leem em notação científica."""
    if _ausente(x):
        return "NA"
    v = float(x)
    if np.isinf(v):
        return "∞" if v > 0 else "-∞"
    if v == 0:
        return pt(0.0, sig)
    expoente = int(np.floor(np.log10(abs(v))))
    mantissa = v / (10.0**expoente)
    # arredondar a mantissa pode empurrá-la para 10,00: renormaliza.
    if abs(round(mantissa, sig)) >= 10:
        mantissa /= 10.0
        expoente += 1
    return f"{pt(mantissa, sig)}×10{str(expoente).translate(_SOBRESCRITO)}"


def tabela(
    df: pd.DataFrame, casas=None, *, index: bool = False, cru: tuple[str, ...] = ()
) -> str:
    """`df.to_string` com todo float em `pt` e todo inteiro em `pt_int`.

    `cru` lista as colunas que ficam como estão — anos, `gold_id`,
    `NU_NOTIFIC`, semanas: identificadores e códigos não levam separador
    de milhar ("2.019" é um erro, não um número em português).

    `casas` é um int para o quadro inteiro ou um dict coluna→int; o
    default para float é 4 (a precisão em que os módulos comparam
    coeficientes). Ausente sai como 'NA'. Formata numa CÓPIA em vez de
    passar `formatters=` ao `to_string`: o pandas resolve o ausente antes
    do formatador, e uma coluna `Int64` com `pd.NA` sairia como '<NA>'.
    Não altera `df`.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("tabela() recebe um DataFrame")

    def _casas(col) -> int:
        if isinstance(casas, dict):
            return casas.get(col, 4)
        return 4 if casas is None else int(casas)

    saida = df.copy()
    for col in saida.columns:
        coluna = saida[col]
        if col in cru or pd.api.types.is_bool_dtype(coluna):
            continue
        if pd.api.types.is_integer_dtype(coluna):
            saida[col] = [pt_int(v) for v in coluna]
        elif pd.api.types.is_float_dtype(coluna):
            d = _casas(col)
            saida[col] = [pt(v, d) for v in coluna]
    return saida.to_string(index=index, na_rep="NA")


__all__ = [
    "AMBAR",
    "AZUL",
    "BANDA_TITULO",
    "BINARIA",
    "CARTAO",
    "CATEGORICA",
    "CINZA",
    "CINZA_CLARO",
    "CMAP_DIVERGENTE",
    "CMAP_INTENSIDADE",
    "CODIGO",
    "CORES_ANO",
    "DIVERGENTE",
    "DPI",
    "ESCURO",
    "FAIXA",
    "FIGDIR",
    "FONTES",
    "FONTES_DIR",
    "GRADE",
    "LINHA",
    "L_FRONTEIRA",
    "L_KERNEL",
    "L_REF",
    "MARCADOR_PACIENTE",
    "MARCADOR_REAL",
    "MARCADOR_SINTETICO",
    "PAINEL",
    "PAPEL",
    "SAGE",
    "SEQ_AZUL",
    "SEQ_TERRACOTA",
    "SLOT",
    "TERRACOTA",
    "aplicar",
    "eixos_pt",
    "pct",
    "pt",
    "pt_int",
    "pt_sig",
    "rampa",
    "salvar",
    "sem_grade",
    "tabela",
    "titulo",
]


if __name__ == "__main__":
    import os
    import tempfile

    matplotlib.use("Agg")
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        destino = aplicar()
        assert destino.is_dir(), destino

        primeira = plt.rcParams["font.sans-serif"][0]
        assert primeira == "Inter", f"font.sans-serif[0] = {primeira!r}, não 'Inter'"
        achado = pathlib.Path(font_manager.findfont("Inter")).resolve()
        assert achado.parent == FONTES_DIR, (
            f"findfont('Inter') resolveu para {achado} — fora de {FONTES_DIR}; "
            "o matplotlib caiu no fallback do sistema"
        )
        mono = pathlib.Path(font_manager.findfont("JetBrains Mono")).resolve()
        assert mono.parent == FONTES_DIR, f"findfont('JetBrains Mono') → {mono}"

        fig, ax = plt.subplots(figsize=SLOT)
        ax.plot([0, 1, 2], [0.1, 0.5, 0.4], color=AZUL, marker=MARCADOR_REAL)
        ax.axhline(0.5, **L_FRONTEIRA)
        ax.set_xlabel("dose")
        ax.set_ylabel("p(óbito)")
        titulo(fig, "A fumaça sobe e desce", "smoke · sapians.py")
        png = salvar(fig, "smoke")
        assert png.is_file() and png.stat().st_size > 0
        plt.close(fig)

    print(f"matplotlib {matplotlib.__version__} · estilo {ESTILO.name}")
    print(f"fontes    : {len(FONTES)} arquivos em {FONTES_DIR}")
    print(f"categórica: {CATEGORICA}")
    print(f"binária   : {BINARIA}")
    print(f"seq azul  : {SEQ_AZUL}")
    print(f"seq terra : {SEQ_TERRACOTA}")
    print(f"divergente: {DIVERGENTE}")
    print(f"anos      : {CORES_ANO}")
    print(
        "números   : "
        f"{pt(1234.567)} · {pt(-0.36, 2, sinal=True)} · {pt(0.92, 2, sinal=True)} · "
        f"{pt_int(1282970)} · {pct(0.373)} · {pt_sig(1.05e-05)}"
    )
    print("smoke: ok")
