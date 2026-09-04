#!/usr/bin/env python3
"""Etapa 81: as figuras de medida do relatório de impacto de citações.

Lê UMA fonte, `<root>/reports/01-impacto/dados.json` (gravado por
`tools/audit_70_numbers.py` -- nunca `data/*.json`, nunca recomputa nada:
todo intervalo de confiança, toda contagem, já vem pronto do JSON) e grava
14 PNGs determinísticos em `reports/01-impacto/figuras/`. Regra do
repositório (CLAUDE.md): todo número em prosa vem de um script versionado;
este é o script que desenha os números de `dados.json`.

Uso:
  python3 tools/audit_81_figures.py                grava as 14 figuras
  python3 tools/audit_81_figures.py --check          regenera em memória +
                                                       diretório temporário e
                                                       compara byte a byte com
                                                       reports/01-impacto/figuras/
                                                       já gravado (nunca
                                                       escreve; sai 1 se
                                                       houver diferença ou
                                                       violação de regra da
                                                       casa); ver `SAIDAS`
  python3 tools/audit_81_figures.py --root PATH      raiz onde ler
                                                       reports/01-impacto/
                                                       dados.json (padrão:
                                                       inferida de __file__,
                                                       como audit_70_numbers.py)
  python3 tools/audit_81_figures.py --only fig05_profundidade.png
                                                      gera/confere só esta
                                                       figura

Caminhos -- mesmo desenho de `tools/audit_70_numbers.py`: os arquivos de
saída vivem sempre em `<pasta do próprio script>/../reports/01-impacto/
figuras/`, independente de `--root`. Isso deixa ler dados de um repositório
só-leitura (`--root` aponta pra lá) e gravar num diretório de stage -- exatamente o
caso de uso da fase de testes deste script. Quando ele for copiado para
`tools/` do repositório real, `--root` default e a saída passam a resolver
para o mesmo lugar sozinhos.

`tools/sapians.py` é importado por caminho: primeiro tenta ao lado deste
script (repo real, onde `sapians.py` mora em `tools/` junto dele); se não
achar (rodando do diretório de stage, onde só este arquivo foi copiado), cai para
`<root>/tools` -- `--root` aponta pro repositório real, que tem o módulo de
verdade. Nenhum outro import do repositório (`auditlib.py` etc.):
vocabulário fechado (ordens de categoria) é duplicado aqui, mesma razão que
`audit_70_numbers.py` dá para duplicar em vez de importar -- este script
roda sozinho contra qualquer `--root`.

Regras de desenho (aplicadas nas 14 funções abaixo, conferidas por
`--check`): sem título dentro da imagem (a legenda do relatório carrega o
achado -- um `ax.set_title` neutro só com o nome do artigo, pra distinguir
painéis sem cor, não conta como título); sem eixo twin; barras sempre do
zero; sem grade vertical; no máximo 5 cores distintas por figura; os dois
artigos (`airline`, `grains`) são separados por PAINEL, nunca por cor. Cor
carrega UM significado no relatório inteiro: rampa de azul = escada
ordinal (profundidade em fig05/fig09; quartil em fig03 -- é a mesma
TÉCNICA -- claro fraco, escuro forte -- aplicada a duas escadas diferentes,
nunca a mesma cor concreta com dois significados); terracota = anomalia ou
destaque único (`misrepresented`, `aresta_falsa`, e por extensão do mesmo
princípio `contradictory` em fig06 -- a única categoria adversa dentro de
um eixo por outro lado normal); âmbar = valor da LITERATURA (taxa
publicada); sage não é usado neste lote de figuras (reservado para reuso/
adoção de método -- nenhuma das 14 é sobre isso); cinza = o resto.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import tempfile
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # antes de qualquer import de pyplot -- inclusive o
# que `sapians.py` faz no próprio topo do módulo (ver _carregar_sapians).

import matplotlib.collections as mcollections
import matplotlib.colors as mcolors
import matplotlib.container as mcontainer
import matplotlib.pyplot as plt
import numpy as np

# --------------------------------------------------------------------------
# Caminhos -- ver docstring do módulo.
# --------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT_ROOT = SCRIPT_DIR.parent
OUT_DIR = SCRIPT_ROOT / "reports" / "01-impacto" / "figuras"

sys.path.insert(0, str(SCRIPT_DIR))
try:
    import sapians as SP  # type: ignore[import-not-found]
except ImportError:
    SP = None  # resolvido por _carregar_sapians() quando --root for conhecido


def _carregar_sapians(root: Path):
    """Garante `SP` importado e aplicado (fontes + `sapians.mplstyle`).

    Primeiro tenta o import que já rodou no topo do módulo (repo real);
    se falhou (rodando do diretório de stage), insere `<root>/tools` em
    `sys.path` e tenta de novo -- `root` só é conhecido depois do
    argparse, por isso este passo não pode viver no topo do arquivo.
    """
    global SP
    if SP is None:
        try:
            import sapians as _sp
        except ImportError:
            sys.path.insert(0, str(root / "tools"))
            import sapians as _sp
        SP = _sp
    SP.aplicar()
    # SP.aplicar() cria FIGDIR ("figures_generated/", relativo ao cwd) --
    # convenção dos cadernos do curso, que salvam ali via SP.salvar(). Este
    # script tem seu próprio contrato de saída (OUT_DIR, fixo, com o
    # próprio writer determinístico) e nunca usa SP.salvar()/SP.FIGDIR; se
    # a pasta ficou vazia, remove -- não faz sentido deixar um diretório
    # órfão de notebook dentro de tools/ do repositório real.
    try:
        if SP.FIGDIR.is_dir() and not any(SP.FIGDIR.iterdir()):
            SP.FIGDIR.rmdir()
    except OSError:
        pass
    return SP


# --------------------------------------------------------------------------
# Vocabulário fechado (duplicado de auditlib/audit_70 de propósito -- ver
# docstring do módulo) e rótulos em português usados nos eixos das figuras.
# --------------------------------------------------------------------------
PAPERS = ("airline", "grains")
PAPER_LABEL = {
    "airline": "airline · atrasos aéreos / entrada de low-cost",
    "grains": "grains · perdas pós-colheita de grãos",
}

DEPTH_ORDER = [
    "drive_by",
    "brief_mention",
    "real_mention",
    "supporting",
    "foundational",
]
DEPTH_LABEL = {
    "drive_by": "de passagem",
    "brief_mention": "menção breve",
    "real_mention": "menção real",
    "supporting": "sustenta",
    "foundational": "fundacional",
}
ACCURACY_ORDER = ["accurate", "imprecise", "misrepresented"]
ACCURACY_LABEL = {
    "accurate": "precisa",
    "imprecise": "imprecisa",
    "misrepresented": "interpretada errado",
}
STANCE_ORDER = ["supporting", "none", "contradictory"]
STANCE_LABEL = {"supporting": "apoia", "none": "neutra", "contradictory": "contrapõe"}
DISTORTION_ORDER = ["dead_end", "diversion", "transmutation", "relayed_attribution"]
DISTORTION_LABEL = {
    "dead_end": "beco sem saída (dead_end)",
    "diversion": "desvio (diversion)",
    "transmutation": "transmutação (transmutation)",
    "relayed_attribution": "atribuição repassada (relayed_attribution)",
}
ROLE_V2_ORDER = [
    "foundational",
    "supporting",
    "real_mention",
    "brief_mention",
    "drive_by",
    "reference_list_only",
    "misrepresented",
]
ROLE_V2_LABEL = {
    "foundational": "fundacional",
    "supporting": "sustenta",
    "real_mention": "menção real",
    "brief_mention": "menção breve",
    "drive_by": "de passagem",
    "reference_list_only": "só bibliografia",
    "misrepresented": "interpretada errado",
}
QUARTIL_ORDER = ["Q1", "Q2", "Q3", "Q4"]
QUARTIL_ORDER_COMPLETO = ["Q1", "Q2", "Q3", "Q4", "fora_do_scimago", "sem_metrica"]
TIMELINE_LABEL = {
    "fundo": "fundo (sustenta/fundacional)",
    "conteudo": "conteúdo (menção real)",
    "passagem": "de passagem (breve/drive-by)",
    "fantasma": "fantasma (só bibliografia)",
}
SEG_LABEL_COBERTURA = {
    "trecho": "trecho localizado",
    "fantasma": "fantasma (só bibliografia)",
    "aresta_falsa": "aresta falsa",
    "pendente": "pendente",
}
TIPO_CLAIM_LABEL = {
    "data": "dado",
    "definition": "definição",
    "finding": "achado",
    "method": "método",
    "policy": "política",
}
EIXO_IRR_LABEL = {
    "presence": "presença",
    "depth": "profundidade",
    "accuracy": "acurácia",
    "stance": "postura",
}
INDICATOR_LABEL = {
    "ghost_D_read": "fantasma / base D_read",
    "ghost_D_body": "fantasma / base D_body",
    "ghost_D_pop": "fantasma / base D_pop",
    "misrepresented_major": "erro maior (misrepresented)",
    "misrepresented_plus_imprecise_total": "erro maior + leve (misrepresented+imprecise)",
    "contradictory": "postura contraditória",
    "perfunctory": "perfunctória (drive_by + brief_mention)",
    "important": "importante (supporting + foundational)",
    "background_like": "tipo-fundo (background-like)",
    "method_reuse": "reuso metodológico",
    "self_or_coauthor": "autocitação / coautoria",
    "duplicate_publication": "publicação duplicada",
}

# eixo -> estatística escolhida para fig11 (ver docstring de fig11_irr).
EIXOS_IRR = [
    ("presence", "kappa", "κ"),
    ("depth", "alpha_ordinal", "α ordinal"),
    ("accuracy", "kappa", "κ"),
    ("stance", "kappa", "κ"),
]

_RE_PUBLICADO_PCT = re.compile(r"(\d+(?:[.,]\d+)?)(?:\s*-\s*(\d+(?:[.,]\d+)?))?\s*%")


# --------------------------------------------------------------------------
# Registro SAIDAS -- nome_arquivo -> função(D) -> Figure. `main()` percorre
# este dicionário; `--only` restringe a uma chave; `--check` regenera cada
# uma em memória/diretório temporário e compara bytes com o já gravado.
# Populado por decorador conforme cada fig0N_* é definida abaixo, na ordem
# do relatório (1..14) -- é essa ordem de inserção que `main()` preserva.
# --------------------------------------------------------------------------
SAIDAS: dict = {}


def _saida(nome):
    def _decorador(func):
        SAIDAS[nome] = func
        return func

    return _decorador


# ==========================================================================
# Helpers pequenos, reusados entre figuras (nada de repetir entre elas).
# ==========================================================================


def _escada_azul(fracas_para_fortes):
    """dict {categoria: cor} numa rampa de azul, clara=fraca, escura=forte.

    Mesma técnica em fig03 (quartil), fig05 (profundidade) e fig09 (classe
    de tempo) -- três escadas ordinais DIFERENTES, nunca a mesma cor
    concreta carregando dois significados (cada figura tem sua própria
    rampa, calculada aqui a partir do próprio conjunto de categorias).
    """
    tons = SP.rampa(len(fracas_para_fortes))
    return dict(zip(fracas_para_fortes, tons))


def _texto_contraste(cor_hex, *, continuo=False):
    """PAPEL (texto claro) ou ESCURO (texto escuro) pra contrastar com
    `cor_hex`. A paleta fixa das barras empilhadas (fig02/fig06) usa uma
    tabela cega -- terracota fica bem no meio da luminância perceptual e
    uma fórmula genérica erraria o lado; `continuo=True` (células do
    heatmap de fig08, cores fora da paleta fixa) cai pra luminância, que é
    a escolha certa quando o valor não é um dos 5 tons fixos do relatório.
    """
    fixa = {
        SP.AZUL: SP.PAPEL,
        SP.CINZA: SP.PAPEL,
        SP.TERRACOTA: SP.PAPEL,
        SP.CINZA_CLARO: SP.ESCURO,
        SP.AMBAR: SP.ESCURO,
    }
    if not continuo and cor_hex in fixa:
        return fixa[cor_hex]
    r, g, b = mcolors.to_rgb(cor_hex)
    luminancia = 0.299 * r + 0.587 * g + 0.114 * b
    return SP.ESCURO if luminancia >= 0.5 else SP.PAPEL


def _rotulo_painel(ax, texto):
    """Rótulo neutro do painel (qual artigo) -- não é o "título" que a
    regra da casa proíbe (esse é o achado, e mora na legenda do relatório,
    não na imagem); é a única forma de distinguir os dois artigos sem cor,
    como a tarefa exige.
    """
    ax.set_title(texto, loc="left", fontsize=9)


def _valores_publicados(texto):
    """Extrai toda porcentagem citada em `texto` (campo `published` de
    `taxa_base.rows`) -- valor único ("41%") ou faixa ("13.1-20.4%", os
    dois extremos). Usado por fig12_taxa_base; nunca inventa um número que
    não esteja escrito ali (`None` ou prosa sem "%" -> lista vazia).
    """
    if not texto:
        return []
    valores = []
    for m in _RE_PUBLICADO_PCT.finditer(texto):
        for grupo in m.groups():
            if grupo is not None:
                valores.append(float(grupo.replace(",", ".")))
    return valores


def _desenhar_pendente_no_eixo(ax, rotulo, motivo):
    """Preenche UM eixo com o aviso "pendente: <motivo>" centrado, fundo
    branco (a régua de fig13_cd/fig14_cocitacao -- ver docstring das
    duas). Fatorado à parte de `_figura_pendente` porque fig13_cd passou
    a poder ter só UM dos dois painéis pendente (o outro artigo já
    chegou) -- a mesma pintura de painel serve pros dois casos: figura
    inteira pendente (fig14, todo `_figura_pendente`) ou só um painel
    dentro de uma figura que também desenha dado de verdade (fig13).
    """
    ax.set_axis_off()
    linhas_txt = textwrap.wrap(f"pendente: {motivo}", 44)
    ax.text(
        0.5,
        0.5,
        "\n".join(linhas_txt),
        ha="center",
        va="center",
        fontsize=8.5,
        color=SP.CINZA,
        transform=ax.transAxes,
    )
    if rotulo:
        ax.text(
            0.5,
            0.92,
            rotulo,
            ha="center",
            va="top",
            fontsize=9.5,
            fontweight="bold",
            color=SP.ESCURO,
            transform=ax.transAxes,
        )


def _figura_pendente(paineis, figsize):
    """Figura-aviso mínima onde TODOS os painéis estão pendentes -- um
    painel por item de `paineis` (rótulo, motivo). Usada por
    fig14_cocitacao (o bloco inteiro pendente, sem quebra por artigo).
    """
    fig, eixos = plt.subplots(1, len(paineis), figsize=figsize, squeeze=False)
    for ax, (rotulo, motivo) in zip(eixos[0], paineis):
        _desenhar_pendente_no_eixo(ax, rotulo, motivo)
    return fig


# ==========================================================================
# As 14 figuras.
# ==========================================================================


@_saida("fig01_funil.png")
def fig01_funil(D):
    """Funil por artigo: Scholar -> inventário -> com DOI -> editora
    estabelecida -> periódico -> evidência verificada. Bloco `funil`
    (`audit_70 §funil`), dois painéis empilhados (um por artigo).

    O passo "periódico" é a população do estudo (METHOD.md §9): é o único
    marcado em azul; os outros cinco ficam em cinza-neutro. `funil.linhas`
    já traz o valor + delta pré-formatado em português ("93 (-2)") -- é
    esse texto que vai em cada barra, não um número recalculado aqui.
    """
    fig, eixos = plt.subplots(2, 1, figsize=SP.PAINEL)
    linhas = D["funil"]["linhas"]
    for ax, paper in zip(eixos, PAPERS):
        steps = D["funil"][paper]["steps"]
        assert steps[4]["rotulo"].startswith("Periódico"), (
            "ordem do funil mudou em dados.json"
        )
        x = np.arange(len(steps))
        valores = [s["valor"] for s in steps]
        cores = [SP.AZUL if i == 4 else SP.CINZA for i in range(len(steps))]
        ax.bar(x, valores, color=cores, width=0.66)
        chave_txt = "airline_txt" if paper == "airline" else "grains_txt"
        for xi, s, linha in zip(x, steps, linhas):
            ax.text(
                xi,
                s["valor"],
                linha[chave_txt],
                ha="center",
                va="bottom",
                fontsize=7.6,
                color=SP.ESCURO,
            )
        ax.set_xticks(x)
        ax.set_xticklabels(
            [s["rotulo"] for s in steps], rotation=18, ha="right", fontsize=7.2
        )
        ax.set_ylim(0, max(valores) * 1.2)
        ax.set_ylabel("citantes (n)")
        _rotulo_painel(ax, PAPER_LABEL[paper])
    return fig


@_saida("fig02_cobertura_quartil.png")
def fig02_cobertura_quartil(D):
    """Os 98 citantes com DOI+quartil (população 87 + 11 fora dela, ainda
    com quartil -- METHOD.md), por Q1..Q4 e total: barras horizontais
    empilhadas em trecho localizado / fantasma / aresta falsa / pendente.
    Bloco `cobertura_quartil`, nível pooled (`audit_70 §cobertura`).
    """
    cq = D["cobertura_quartil"]
    linhas = ["Q1", "Q2", "Q3", "Q4", "total"]
    fig, ax = plt.subplots(figsize=SP.FAIXA)
    y = np.arange(len(linhas))
    segmentos = [
        ("trecho", SP.AZUL),
        ("fantasma", SP.CINZA),
        ("aresta_falsa", SP.TERRACOTA),
        ("pendente", SP.CINZA_CLARO),
    ]
    esquerda = np.zeros(len(linhas))
    for chave, cor in segmentos:
        valores = np.array([cq[linha][chave] for linha in linhas], dtype=float)
        ax.barh(
            y,
            valores,
            left=esquerda,
            color=cor,
            height=0.6,
            label=SEG_LABEL_COBERTURA[chave],
        )
        cor_texto = _texto_contraste(cor)
        for yi, v, l0 in zip(y, valores, esquerda):
            if v > 0:
                ax.text(
                    l0 + v / 2,
                    yi,
                    SP.pt_int(int(v)),
                    ha="center",
                    va="center",
                    fontsize=7.4,
                    color=cor_texto,
                )
        esquerda += valores
    for yi, linha in zip(y, linhas):
        ax.text(
            cq[linha]["total"] + esquerda.max() * 0.012,
            yi,
            f"n={SP.pt_int(cq[linha]['total'])}",
            ha="left",
            va="center",
            fontsize=7.6,
            color=SP.CINZA,
        )
    ax.set_yticks(y)
    ax.set_yticklabels(linhas)
    ax.invert_yaxis()
    ax.set_xlim(0, esquerda.max() * 1.14)
    ax.set_xlabel("citações (n)")
    # loc="lower right" ficava por cima do fim da barra "total" (o "n="
    # de anotação some atrás da caixa de legenda) -- embaixo do eixo,
    # fora da área de desenho, não tem como cobrir barra nenhuma.
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.16),
        ncol=4,
        fontsize=7.4,
        frameon=False,
    )
    SP.sem_grade(ax)
    return fig


@_saida("fig03_quartis.png")
def fig03_quartis(D):
    """Distribuição das citações CLASSIFICADAS por quartil Scimago
    (Q1..Q4) + "sem quartil" (fora_do_scimago + sem_metrica somados), por
    artigo, dois painéis. Bloco `quartil.classificadas` (`audit_70
    §quartil`) -- `periodicos.total`/`periodicos.quartis` contam
    PERIÓDICOS únicos por quartil (eixo diferente: veículos, não
    citações); citado na prosa do relatório, não redesenhado aqui.
    """
    cores_q = dict(zip(["Q4", "Q3", "Q2", "Q1"], SP.rampa(4)))
    cores_q["sem quartil"] = SP.CINZA_CLARO
    cats = ["Q1", "Q2", "Q3", "Q4", "sem quartil"]
    fig, eixos = plt.subplots(1, 2, figsize=SP.PAINEL)
    for ax, paper in zip(eixos, PAPERS):
        bloco = D["quartil"]["classificadas"][paper]
        valores = [bloco.get(q, 0) for q in QUARTIL_ORDER]
        valores.append(bloco.get("fora_do_scimago", 0) + bloco.get("sem_metrica", 0))
        x = np.arange(len(cats))
        ax.bar(x, valores, color=[cores_q[c] for c in cats], width=0.6)
        for xi, v in zip(x, valores):
            ax.text(xi, v, SP.pt_int(v), ha="center", va="bottom", fontsize=8)
        ax.set_xticks(x)
        ax.set_xticklabels(cats, fontsize=8.5)
        ax.set_ylim(0, max(valores) * 1.22 if valores else 1)
        ax.set_ylabel("citações classificadas (n)")
        _rotulo_painel(ax, f"{PAPER_LABEL[paper]} · n={SP.pt_int(sum(valores))}")
    return fig


@_saida("fig04_periodicos.png")
def fig04_periodicos(D):
    """Os 12 periódicos mais citados, pooled (`periodicos.pooled`, já
    ordenado por `n` decrescente -- `audit_70 §periodicos`), barras
    horizontais cinza-neutro (nenhum eixo de anomalia/profundidade/reuso
    entra aqui, então nenhuma cor especial se aplica); quartil anotado
    como texto ao lado de cada barra, não por cor.
    """
    top = D["periodicos"]["pooled"][:12]
    fig, ax = plt.subplots(figsize=SP.FAIXA)
    y = np.arange(len(top))
    valores = [row["n"] for row in top]
    ax.barh(y, valores, color=SP.CINZA, height=0.6)
    for yi, row in zip(y, top):
        ax.text(
            row["n"] + max(valores) * 0.02,
            yi,
            row["quartil"] or "sem quartil",
            va="center",
            fontsize=7.5,
            color=SP.CINZA,
        )
    ax.set_yticks(y)
    ax.set_yticklabels([row["nome_norm"] for row in top], fontsize=7.6)
    ax.invert_yaxis()
    ax.set_xlim(0, max(valores) * 1.2)
    ax.set_xlabel("citações (n)")
    SP.sem_grade(ax)
    return fig


@_saida("fig05_profundidade.png")
def fig05_profundidade(D):
    """Escada de profundidade (drive_by < brief_mention < real_mention <
    supporting < foundational) por artigo, dois painéis, rampa de azul
    (clara=fraca, escura=forte). Bloco `eixos.{airline,grains}.depth`
    (`audit_70 §eixos`), base D = citações em texto (`in_text`) do artigo.
    """
    cores = _escada_azul(DEPTH_ORDER)
    fig, eixos = plt.subplots(1, 2, figsize=SP.PAINEL)
    for ax, paper in zip(eixos, PAPERS):
        bloco = D["eixos"][paper]["depth"]
        valores = [bloco[d]["n"] for d in DEPTH_ORDER]
        pcts = [bloco[d]["pct"] for d in DEPTH_ORDER]
        x = np.arange(len(DEPTH_ORDER))
        ax.bar(x, valores, color=[cores[d] for d in DEPTH_ORDER], width=0.62)
        for xi, v, p in zip(x, valores, pcts):
            ax.text(
                xi, v, f"{SP.pt_int(v)} ({p})", ha="center", va="bottom", fontsize=7.4
            )
        ax.set_xticks(x)
        ax.set_xticklabels(
            [DEPTH_LABEL[d] for d in DEPTH_ORDER], rotation=18, ha="right", fontsize=7.6
        )
        d_total = bloco[DEPTH_ORDER[0]]["D"]
        ax.set_ylim(0, max(valores) * 1.25)
        ax.set_ylabel("citações em texto (n)")
        _rotulo_painel(ax, f"{PAPER_LABEL[paper]} · D={SP.pt_int(d_total)}")
    return fig


@_saida("fig06_postura_acuracia.png")
def fig06_postura_acuracia(D):
    """Dois painéis: postura por artigo (barras 100% empilhadas) e
    acurácia por artigo (accurate / imprecise / misrepresented). Bloco
    `eixos.{airline,grains}.{stance,accuracy}` (`audit_70 §eixos`).

    Dentro de cada eixo as categorias são ordenadas por "normalidade":
    cinza-escuro para a maioria esperada (apoia / precisa), cinza-claro
    para a intermediária (neutra / imprecisa), terracota só para a
    categoria adversa isolada (contrapõe / interpretada errado) -- mesmo
    princípio de destaque único que `aresta_falsa` usa em fig02, agora
    aplicado à postura contraditória além do "misrepresented" que a
    tarefa deu como exemplo.
    """
    cor_stance = {
        "supporting": SP.CINZA,
        "none": SP.CINZA_CLARO,
        "contradictory": SP.TERRACOTA,
    }
    cor_accuracy = {
        "accurate": SP.CINZA,
        "imprecise": SP.CINZA_CLARO,
        "misrepresented": SP.TERRACOTA,
    }
    fig, (ax_postura, ax_acuracia) = plt.subplots(1, 2, figsize=SP.PAINEL)
    especificacao = (
        (ax_postura, "stance", STANCE_ORDER, cor_stance, STANCE_LABEL, "postura"),
        (
            ax_acuracia,
            "accuracy",
            ACCURACY_ORDER,
            cor_accuracy,
            ACCURACY_LABEL,
            "acurácia",
        ),
    )
    y = np.arange(len(PAPERS))
    for ax, eixo, ordem, cores, rotulos, nome_eixo in especificacao:
        esquerda = np.zeros(len(PAPERS))
        for chave in ordem:
            fracoes = np.array(
                [D["eixos"][paper][eixo][chave]["valor"] for paper in PAPERS]
            )
            ax.barh(
                y,
                fracoes * 100,
                left=esquerda * 100,
                color=cores[chave],
                height=0.5,
                label=rotulos[chave],
            )
            cor_texto = _texto_contraste(cores[chave])
            for yi, f, l0 in zip(y, fracoes, esquerda):
                if f > 0.035:
                    ax.text(
                        (l0 + f / 2) * 100,
                        yi,
                        SP.pct(f),
                        ha="center",
                        va="center",
                        fontsize=7.6,
                        color=cor_texto,
                    )
            esquerda += fracoes
        ax.set_yticks(y)
        ax.set_yticklabels([PAPER_LABEL[p] for p in PAPERS], fontsize=8)
        ax.set_xlim(0, 100)
        ax.set_xlabel(f"{nome_eixo} (%)")
        ax.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.22),
            ncol=3,
            fontsize=7.2,
            frameon=False,
        )
        SP.sem_grade(ax)
    return fig


@_saida("fig07_distorcao.png")
def fig07_distorcao(D):
    """Subtipos de distorção de Greenberg (dead_end, diversion,
    transmutation, relayed_attribution), pooled, barras horizontais
    ordenadas por frequência. Bloco `eixos.pooled.distortion` (`audit_70
    §eixos`) -- os 4 subtipos não são mutuamente exaustivos com
    "misrepresented" (a base D é toda citação em texto pooled, não só as
    interpretadas errado: a soma dos 4 fica abaixo de D de propósito, o
    resto não tem subtipo de distorção marcado). Barra única em
    cinza-neutro: os quatro subtipos estão no mesmo nível semântico
    (nenhum é "o" destaque adverso isolado que justificaria terracota
    aqui -- essa cor já está reservada pra `misrepresented`/
    `contradictory` em fig06).
    """
    bloco = D["eixos"]["pooled"]["distortion"]
    ordem = sorted(DISTORTION_ORDER, key=lambda k: -bloco[k]["n"])
    fig, ax = plt.subplots(figsize=SP.FAIXA)
    y = np.arange(len(ordem))
    valores = [bloco[k]["n"] for k in ordem]
    ax.barh(y, valores, color=SP.CINZA, height=0.5)
    for yi, k in zip(y, ordem):
        ax.text(
            bloco[k]["n"] + max(valores) * 0.03,
            yi,
            bloco[k]["pct"],
            va="center",
            fontsize=7.8,
            color=SP.CINZA,
        )
    ax.set_yticks(y)
    ax.set_yticklabels([DISTORTION_LABEL[k] for k in ordem], fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlim(0, max(valores) * 1.25)
    d_total = bloco[ordem[0]]["D"]
    ax.set_xlabel(f"citações em texto, pooled (n; base D={SP.pt_int(d_total)})")
    SP.sem_grade(ax)
    return fig


@_saida("fig08_profundidade_quartil.png")
def fig08_profundidade_quartil(D):
    """Profundidade (papel v2) x quartil, pooled: matriz de contagens
    como heatmap, rampa de azul, números nas células. Bloco
    `papel_quartil.pooled.matriz` (`audit_70 §papel-quartil`).
    """
    matriz = D["papel_quartil"]["pooled"]["matriz"]
    linhas = [q for q in QUARTIL_ORDER_COMPLETO if q in matriz]
    colunas = ROLE_V2_ORDER
    dados_m = np.array(
        [[matriz[l].get(c, 0) for c in colunas] for l in linhas], dtype=float
    )
    fig, ax = plt.subplots(figsize=SP.SLOT)
    vmax = dados_m.max() if dados_m.size else 1.0
    im = ax.imshow(dados_m, cmap=SP.CMAP_INTENSIDADE, aspect="auto", vmin=0, vmax=vmax)
    ax.set_xticks(range(len(colunas)))
    ax.set_xticklabels(
        [ROLE_V2_LABEL[c] for c in colunas], rotation=28, ha="right", fontsize=7.6
    )
    ax.set_yticks(range(len(linhas)))
    ax.set_yticklabels(linhas, fontsize=8.5)
    for i in range(len(linhas)):
        for j in range(len(colunas)):
            v = dados_m[i, j]
            if v <= 0:
                continue
            cor_cel = mcolors.to_hex(SP.CMAP_INTENSIDADE(v / vmax if vmax else 0.0))
            ax.text(
                j,
                i,
                SP.pt_int(int(v)),
                ha="center",
                va="center",
                fontsize=7.8,
                color=_texto_contraste(cor_cel, continuo=True),
            )
    SP.sem_grade(ax)
    ax.set_xticks(np.arange(-0.5, len(colunas), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(linhas), 1), minor=True)
    ax.grid(True, which="minor", color=SP.PAPEL, linewidth=1.3, linestyle="-")
    ax.tick_params(which="minor", bottom=False, left=False)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    cbar.set_label("citações (n)", fontsize=8, color=SP.CINZA)
    cbar.ax.tick_params(labelsize=7)
    return fig


@_saida("fig09_linha_do_tempo.png")
def fig09_linha_do_tempo(D):
    """Citações por ano por artigo, dois painéis empilhados, barras
    empilhadas por classe de tempo. Bloco `linha_do_tempo` (`audit_70
    §linha-do-tempo`): `fundo` = supporting+foundational, `conteudo` =
    real_mention, `passagem` = drive_by+brief_mention (mesma escada de
    profundidade de fig05, agora em 3 baldes), `fantasma` =
    reference_list_only -- mesmo cinza-médio de "fantasma" em fig02
    (uma cor, um significado, no relatório inteiro).
    """
    cores = _escada_azul(["passagem", "conteudo", "fundo"])
    cores["fantasma"] = SP.CINZA
    ordem_pilha = ["fundo", "conteudo", "passagem", "fantasma"]
    fig, eixos = plt.subplots(2, 1, figsize=SP.PAINEL)
    for idx, (ax, paper) in enumerate(zip(eixos, PAPERS)):
        bloco = D["linha_do_tempo"][paper]
        anos = sorted(bloco.keys())
        x = np.arange(len(anos))
        esquerda = np.zeros(len(anos))
        for classe in ordem_pilha:
            valores = np.array([bloco[a].get(classe, 0) for a in anos], dtype=float)
            ax.bar(
                x,
                valores,
                bottom=esquerda,
                color=cores[classe],
                width=0.66,
                label=TIMELINE_LABEL[classe],
            )
            esquerda += valores
        ax.set_xticks(x)
        ax.set_xticklabels(anos, fontsize=7.6)
        # o painel de cima carrega a legenda (só uma vez, vale pros dois);
        # 1.45 (contra 1.18 no painel sem legenda) abre uma faixa de teto
        # que nenhuma barra alcança, pra legenda nunca poder cobrir dado.
        teto = 1.45 if idx == 0 else 1.18
        ax.set_ylim(0, esquerda.max() * teto if len(esquerda) else 1)
        ax.set_ylabel("citações (n)")
        _rotulo_painel(ax, PAPER_LABEL[paper])
        if idx == 0:
            ax.legend(loc="upper left", ncol=4, fontsize=7.2, frameon=False)
    return fig


@_saida("fig10_alegacoes.png")
def fig10_alegacoes(D):
    """Afirmações dos artigos por número de citações que as sustentam, um
    painel por artigo, barras horizontais ordenadas por `n_citations`
    decrescente. Bloco `alegacoes.claims` (`audit_70 §alegacoes`):
    afirmações `relayed` (status transmitido de outra fonte, não
    originais do artigo) em âmbar; as demais (original / interpretation /
    limitation) em azul. Afirmações com 0 citação de sustentação são
    omitidas do gráfico (barra de comprimento zero não é legível) e
    contadas no rótulo do painel.
    """
    claims = D["alegacoes"]["claims"]
    fig, eixos = plt.subplots(1, 2, figsize=SP.PAINEL)
    for idx, (ax, paper) in enumerate(zip(eixos, PAPERS)):
        itens = sorted(
            (
                (cid, c)
                for cid, c in claims.items()
                if c["paper"] == paper and c["n_citations"] > 0
            ),
            key=lambda kv: -kv[1]["n_citations"],
        )
        y = np.arange(len(itens))
        valores = np.array([c["n_citations"] for _, c in itens], dtype=float)
        relayed = np.array([c["status"] == "relayed" for _, c in itens])
        if len(itens) and (~relayed).any():
            ax.barh(
                y[~relayed],
                valores[~relayed],
                color=SP.AZUL,
                height=0.62,
                label="original / interpretação / limitação",
            )
        if len(itens) and relayed.any():
            ax.barh(
                y[relayed],
                valores[relayed],
                color=SP.AMBAR,
                height=0.62,
                label="relayed (repassada de outra fonte)",
            )
        for yi, v in zip(y, valores):
            ax.text(
                v + (valores.max() * 0.02 if len(valores) else 0.1),
                yi,
                SP.pt_int(int(v)),
                va="center",
                fontsize=6.8,
                color=SP.CINZA,
            )
        ax.set_yticks(y)
        ax.set_yticklabels(
            [
                f"{cid} · {TIPO_CLAIM_LABEL.get(c['type'], c['type'])}"
                for cid, c in itens
            ],
            fontsize=6.6,
        )
        ax.invert_yaxis()
        if len(valores):
            ax.set_xlim(0, valores.max() * 1.22)
        ax.set_xlabel("citações que sustentam (n)")
        n_zero = sum(
            1 for c in claims.values() if c["paper"] == paper and c["n_citations"] == 0
        )
        _rotulo_painel(
            ax,
            f"{PAPER_LABEL[paper]} · {len(itens)} com citação (+{n_zero} com 0, omitidas)",
        )
        SP.sem_grade(ax)
        if idx == 0:
            ax.legend(loc="lower right", fontsize=7)
    return fig


@_saida("fig11_irr.png")
def fig11_irr(D):
    """Concordância entre codificadores por eixo: pré (pares cegos c1×c2,
    c1×c3, c2×c3 -- `irr.pre`) e pós (cada codificador contra o rótulo
    final -- `irr.post.c1/c2/c3`). Bloco `irr` (`audit_70 §irr`).

    Uma estatística por eixo, escrita no rótulo do eixo: α ordinal de
    Krippendorff para profundidade (a única categórica ordenada dos
    quatro -- `alpha_metrica` do próprio bloco confirma "ordinal"); κ de
    Cohen para presença/acurácia/postura (`alpha_metrica` = "nominal"
    nesses três -- κ é a estatística clássica pra nominal, e é a que as
    faixas de Landis & Koch, plotadas como fundo, foram desenhadas pra
    ler). `reuse`, `distortion` e `claim_ids` ficam de fora: os três têm
    `point`/`ci95` nulos tanto em `pre` quanto em `post` (prevalência
    baixa demais pra estatística de concordância bem definida) -- não há
    número pra desenhar, então não desenham nada, em vez de inventar.
    """
    bandas = D["constantes"]["landis_koch"]
    ordem_bandas = [
        "pobre",
        "leve",
        "razoavel",
        "moderada",
        "substancial",
        "quase_perfeita",
    ]
    fig, ax = plt.subplots(figsize=SP.PAINEL)
    xlim = (-0.06, 1.04)
    for i, nome in enumerate(ordem_bandas):
        banda = bandas[nome]
        lo = banda["min"] if banda["min"] is not None else xlim[0]
        hi = banda["max"]
        if i % 2 == 0:
            ax.axvspan(lo, hi, color=SP.CINZA_CLARO, alpha=0.3, lw=0, zorder=0)
    n_eixos = len(EIXOS_IRR)
    offsets_pre = (-0.30, -0.18, -0.06)
    offsets_post = (0.06, 0.18, 0.30)
    for i, (eixo, stat, _rotulo_stat) in enumerate(EIXOS_IRR):
        y0 = n_eixos - 1 - i
        pares_pre = D["irr"]["pre"]["eixos"][eixo]["pares"]
        for off, par in zip(offsets_pre, ("c1_vs_c2", "c1_vs_c3", "c2_vs_c3")):
            pv = pares_pre[par]
            ponto = pv["point"][stat]
            lo_ci, hi_ci = pv["ci95"][stat]["lo"], pv["ci95"][stat]["hi"]
            ax.errorbar(
                ponto,
                y0 + off,
                xerr=[[ponto - lo_ci], [hi_ci - ponto]],
                fmt="o",
                ms=4.2,
                color=SP.CINZA,
                ecolor=SP.CINZA,
                elinewidth=1.1,
                capsize=2.4,
                zorder=3,
            )
        for off, coder in zip(offsets_post, ("c1", "c2", "c3")):
            pv = D["irr"]["post"][coder]["eixos"][eixo]["pares"]["c1_vs_c2"]
            ponto = pv["point"][stat]
            lo_ci, hi_ci = pv["ci95"][stat]["lo"], pv["ci95"][stat]["hi"]
            ax.errorbar(
                ponto,
                y0 + off,
                xerr=[[ponto - lo_ci], [hi_ci - ponto]],
                fmt="s",
                ms=4.6,
                color=SP.AZUL,
                ecolor=SP.AZUL,
                elinewidth=1.1,
                capsize=2.4,
                zorder=3,
            )
    ax.axvline(0, color=SP.LINHA, linewidth=0.8, zorder=1)
    ax.set_yticks([n_eixos - 1 - i for i in range(n_eixos)])
    ax.set_yticklabels(
        [f"{EIXO_IRR_LABEL[e]} ({r})" for e, _, r in EIXOS_IRR], fontsize=9.5
    )
    ax.set_ylim(-0.55, n_eixos - 1 + 0.55)
    ax.set_xlim(*xlim)
    ax.set_xlabel(
        "concordância (κ de Cohen ou α ordinal de Krippendorff, conforme o eixo)"
    )
    ax.errorbar(
        [], [], fmt="o", color=SP.CINZA, label="pré (pares cegos: c1×c2, c1×c3, c2×c3)"
    )
    ax.errorbar(
        [], [], fmt="s", color=SP.AZUL, label="pós (cada codificador × rótulo final)"
    )
    # canto superior esquerdo: todo ponto de "presença" fica bem à direita
    # (kappa >= 0,85) -- "lower right" cobria a ponta do whisker mais longo
    # de "postura" pré (chega a 0,86, dentro do canto inferior direito).
    ax.legend(loc="upper left", fontsize=7.6)
    return fig


@_saida("fig12_taxa_base.png")
def fig12_taxa_base(D):
    """Nossas taxas (ponto escuro, pooled, com IC de Wilson já pronto no
    JSON) contra as publicadas na literatura (losango âmbar) por linha de
    `taxa_base.rows` (`audit_70 §taxa-base`); eixo x em %.

    Um ponto escuro por linha (a taxa pooled -- "um ponto por taxa"); zero,
    um ou vários losangos âmbar por linha, um por porcentagem que o campo
    `published` daquela linha efetivamente cita em texto (`method_reuse`,
    `self_or_coauthor` e `duplicate_publication` não têm comparador
    publicado -- ponto escuro sem losango; `misrepresented_plus_
    imprecise_total` cita 3 estudos, 5 porcentagens -- 5 losangos).
    """
    linhas = D["taxa_base"]["rows"]
    fig, ax = plt.subplots(figsize=SP.PAINEL)
    y = np.arange(len(linhas))
    for yi, row in zip(y, linhas):
        res = row["results"]["pooled"]
        if res.get("rate") is not None:
            taxa = res["rate"] * 100
            lo = res["ci95_wilson"][0] * 100
            hi = res["ci95_wilson"][1] * 100
            ax.errorbar(
                taxa,
                yi,
                xerr=[[taxa - lo], [hi - taxa]],
                fmt="o",
                ms=5.6,
                color=SP.ESCURO,
                ecolor=SP.ESCURO,
                elinewidth=1.2,
                capsize=3,
                zorder=3,
            )
        for pv in _valores_publicados(row.get("published")):
            ax.scatter(
                [pv],
                [yi],
                marker="D",
                s=32,
                color=SP.AMBAR,
                zorder=2,
                edgecolors=SP.PAPEL,
                linewidths=0.5,
            )
    ax.set_yticks(y)
    ax.set_yticklabels(
        [INDICATOR_LABEL.get(r["indicator"], r["indicator"]) for r in linhas],
        fontsize=8.4,
    )
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("taxa (%)")
    ax.errorbar(
        [], [], fmt="o", color=SP.ESCURO, label="nossa taxa (pooled, IC95 de Wilson)"
    )
    ax.scatter(
        [], [], marker="D", color=SP.AMBAR, label="valor(es) publicado(s) na literatura"
    )
    ax.legend(loc="lower right", fontsize=7.6)
    return fig


# Série -> chave em `windows[t]["ci_95"]` (o ponto de cada série tem seu
# próprio jeito de ser lido -- ver `_ponto_cd_serie` -- mas a chave do IC
# nem sempre bate com o nome da série: "holst" lê IC em "holst_CD").
CD_SERIES = (("DI5", "DI5"), ("CD_nok", "CD_nok"), ("CD", "CD"), ("holst", "holst_CD"))
CD_SERIE_LABEL = {
    "CD": "CD",
    "CD_nok": "CD sem k (CD_nok)",
    "DI5": "DI5",
    "holst": "holst",
}
CD_SERIE_MARCADOR = {"CD": "o", "CD_nok": "o", "DI5": "o", "holst": "^"}
CD_SERIE_OFFSET = {"DI5": -0.27, "CD_nok": -0.09, "CD": 0.09, "holst": 0.27}


def _ponto_cd_serie(janela, serie):
    """Lê o valor-ponto de uma série do índice de disrupção para uma
    janela `t` (um item de `cd.<artigo>.cd_index.windows`) -- ver
    docstring de `fig13_cd` para a forma completa lida de `dados.json`.
    `CD`/`CD_nok` são números soltos; `DI5` é um dict com `value` (mais
    `n_i`/`n_j`/`n_k` PRÓPRIOS, diferentes dos da janela -- não usados
    aqui); `holst` é um dict cujo ponto mora na chave `CD` dele mesmo.
    """
    if serie in ("CD", "CD_nok"):
        return janela[serie]
    if serie == "DI5":
        return janela["DI5"]["value"]
    if serie == "holst":
        return janela["holst"]["CD"]
    raise ValueError(f"série desconhecida: {serie!r}")


def _painel_cd_real(ax, bloco_paper, *, mostrar_legenda=True):
    """Forest-plot de CD_t por janela `t`, as quatro séries de
    `CD_SERIES`, para UM artigo já confirmado não-pendente pelo chamador
    (`fig13_cd`). `bloco_paper` é `D["cd"][<artigo>]` inteiro (usa só
    `.cd_index`; `.refs_audit` não entra nesta figura).

    Posições de `t` no eixo x são CATEGÓRICAS (0,1,2,3 com rótulo "1"/
    "3"/"5"/"10"), não uma escala linear de verdade -- numa escala linear
    o ponto t=10 ficaria sozinho lá longe e t=1/3/5 amontoados à
    esquerda, pouco legível para só 4 janelas. Cada série ganha um
    pequeno deslocamento horizontal fixo (`CD_SERIE_OFFSET`, não
    aleatório) para os quatro pontos + IC de uma mesma janela não se
    empilharem um em cima do outro.

    Uma janela pode vir truncada (`janela["truncated"]`, ex.: `grains`
    t_nominal=10 só tem `t`=7 anos de citação até hoje -- o artigo é de
    2019, e 2019+10 é ano que ainda não chegou): o rótulo do ponto nesse
    caso mostra os dois números, "10 (7)" -- nominal fora, real dentro
    dos parênteses -- lido de `janela["t_nominal"]`/`janela["t"]`, nunca
    inferido daqui.
    """
    cd_index = bloco_paper["cd_index"]
    janelas = cd_index["windows"]
    ts = sorted(janelas.keys(), key=int)
    x = np.arange(len(ts))
    cores = _escada_azul(["DI5", "CD_nok", "CD"])  # claro=DI5 -> escuro=CD
    cores["holst"] = (
        SP.CINZA
    )  # variante de robustez, não anomalia -- ver docstring do módulo

    ax.axhline(0, color=SP.LINHA, linestyle=(0, (4, 3)), linewidth=1.0, zorder=1)

    for serie, chave_ci in CD_SERIES:
        for xi, t in zip(x, ts):
            janela = janelas[t]
            ponto = _ponto_cd_serie(janela, serie)
            lo, hi = janela["ci_95"][chave_ci]
            ax.errorbar(
                xi + CD_SERIE_OFFSET[serie],
                ponto,
                yerr=[[ponto - lo], [hi - ponto]],
                fmt=CD_SERIE_MARCADOR[serie],
                ms=4.6,
                color=cores[serie],
                ecolor=cores[serie],
                elinewidth=1.1,
                capsize=2.4,
                zorder=3,
                label=CD_SERIE_LABEL[serie] if xi == x[0] else None,
            )

    # anotação n_i/n_j/n_k embaixo do ponto CD -- os n's da própria janela
    # (os mesmos que sustentam CD e holst; DI5 tem os seus próprios,
    # deliberadamente não anotados aqui para não confundir os dois trios).
    y_min = min(
        min(janela["ci_95"][chave_ci][0], _ponto_cd_serie(janela, serie))
        for serie, chave_ci in CD_SERIES
        for janela in janelas.values()
    )
    y_max = max(
        max(janela["ci_95"][chave_ci][1], _ponto_cd_serie(janela, serie))
        for serie, chave_ci in CD_SERIES
        for janela in janelas.values()
    )
    folga = (y_max - y_min) * 0.12
    ax.set_ylim(y_min - folga * 1.6, y_max + folga)
    y_rotulo = y_min - folga * 0.35
    for xi, t in zip(x, ts):
        janela = janelas[t]
        ax.text(
            xi + CD_SERIE_OFFSET["CD"],
            y_rotulo,
            f"{janela['n_i']}/{janela['n_j']}/{janela['n_k']}",
            ha="center",
            va="top",
            fontsize=6.2,
            color=SP.CINZA,
        )

    def _rotulo_t(t):
        janela = janelas[t]
        base = str(janela["t_nominal"])
        return f"{base} ({janela['t']})" if janela.get("truncated") else base

    ax.set_xticks(x)
    ax.set_xticklabels([_rotulo_t(t) for t in ts])
    ax.set_xlim(-0.55, len(ts) - 0.45)
    ax.set_xlabel("janela t (anos)")
    ax.set_ylabel("índice de disrupção (-1 consolida, +1 desloca)")
    if mostrar_legenda:
        # fora do eixo: em t=1 o IC de DI5/CD_nok já encosta no teto
        # (chega a 1,0) -- "upper left" dentro do eixo cobria a ponta do
        # whisker. Este painel é meio PAINEL de largura (lado a lado com
        # o outro artigo), por isso 2 colunas (não 4, que ficaria
        # apertado) em duas linhas. Só um painel mostra (o primeiro) --
        # as quatro séries e cores são as MESMAS nos dois artigos, uma
        # legenda repetida embaixo dos dois painéis não diz nada a mais.
        ax.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.16),
            ncol=2,
            fontsize=7.2,
            frameon=False,
        )


@_saida("fig13_cd.png")
def fig13_cd(D):
    """CD_t (índice de disrupção) por janela t em {1,3,5,10}, com IC
    bootstrap (`ci_95`, lido do JSON, nunca recomputado), por artigo,
    dois painéis. Bloco `cd.<artigo>.cd_index` (`audit_70 §cd`).

    Cada painel decide sozinho, pelo próprio `cd.<artigo>.cd_index.
    pendente`: se `True`, desenha só o aviso "pendente: <motivo>" (ver
    `_desenhar_pendente_no_eixo`); senão desenha o forest-plot de
    verdade (`_painel_cd_real`). Um artigo pendente nunca impede o outro
    de desenhar -- os dois já chegaram (`airline` e `grains`) e os dois
    painéis desenham o gráfico de verdade hoje; a checagem por-artigo
    fica porque `cocitacao`/outros blocos futuros podem voltar a chegar
    um artigo de cada vez, e nenhuma mudança de código deveria ser
    necessária quando isso acontecer de novo -- só regenerar.

    Forma lida em `cd.<artigo>.cd_index` (nenhuma folha aqui vem
    embrulhada em `{"valor","txt"}` -- são números/bool/None crus, ao
    contrário de blocos como `eixos`/`taxa_base`): `backend`, `crosstab`,
    `fisher_p`, `loo` (os três `None` nas duas corridas) e `windows`, um
    dict por janela `t` ("1"/"3"/"5"/"10", strings -- a CHAVE é o t
    NOMINAL) com `CD`, `CD_nok`, `DI2 {n_i,n_j,n_k,value}`, `DI5
    {n_i,n_j,n_k,value}`, `holst {CD,n_i,n_j,n_k}`, `checks {...}` (não
    desenhado -- são validações internas do índice, não dado pra
    figura), `ci_95 {CD, CD_nok, DI2, DI5, holst_CD}` (cada um `[lo,
    hi]`) e, soltos na própria janela, `n_i`, `n_j`, `n_k`, `n_window`,
    `t`, `t_nominal`, `truncated`. Em `grains`, a janela de chave "10"
    tem `truncated=true`, `t_nominal=10` mas `t=7` -- o artigo é de 2019
    e uma janela de 10 anos exigiria dado até 2029, que não existe; o
    rótulo do ponto mostra os dois números ("10 (7)", ver
    `_painel_cd_real`).

    Quatro séries desenhadas (`DI2` fica de fora -- não pedida): `CD`
    (azul escuro), `CD_nok` ("CD sem k", azul médio -- CD_nok ignora o
    termo n_k do denominador, exatamente a nota de `reports/01-impacto/
    figuras.typ`: "CD sem k ignora os antecessores solitários"), `DI5`
    (azul claro -- "DI cinco exige cinco referências em comum", mesma
    fonte) e `holst` (cinza -- é uma variante de robustez do próprio CD,
    não uma anomalia; cinza aqui não colide com "fantasma" de fig02/fig09
    porque cinza sempre significou "o padrão sem destaque", não uma cor
    fixada a UM rótulo -- fantasma É cinza por ser o caso sem destaque
    daquele eixo, não o inverso).
    """
    fig, eixos = plt.subplots(1, 2, figsize=SP.PAINEL)
    for idx, (ax, paper) in enumerate(zip(eixos, PAPERS)):
        bloco_paper = D["cd"][paper]
        if bloco_paper["cd_index"].get("pendente"):
            _desenhar_pendente_no_eixo(
                ax,
                PAPER_LABEL[paper],
                bloco_paper["cd_index"].get(
                    "motivo", "sem motivo registrado em dados.json"
                ),
            )
        else:
            _painel_cd_real(ax, bloco_paper, mostrar_legenda=(idx == 0))
            _rotulo_painel(ax, PAPER_LABEL[paper])
    return fig


COCIT_BROKER_ORDEM = ("AB", "A_only", "B_only", "single_strand")
COCIT_BROKER_LABEL = {
    "AB": "AB (cita os dois lados)",
    "A_only": "só A",
    "B_only": "só B",
    "single_strand": "single-strand",
}


@_saida("fig14_cocitacao.png")
def fig14_cocitacao(D):
    """Co-citação A-B (o artigo focal e o par de disputa mais cocitado
    com ele) -- só `airline`: o bloco descreve um par específico de
    artigos cocitados, sem equivalente natural para `grains` nos dados
    de hoje. Bloco `cocitacao` (`audit_70 §cocitacao`), duas partes lado
    a lado dentro de um SLOT só -- não há "por artigo" aqui que
    justifique PAINEL/dois painéis.

    Forma lida (nenhuma folha embrulhada em `{"valor","txt"}` -- mesma
    convenção numérica crua de `cd`, ao contrário de blocos como
    `eixos`/`taxa_base`): `periods.<cenário>` (`main`, zero ou mais
    `placebo_*`, e um `sensitivity` que NÃO é um placebo -- só desloca o
    ano de corte pós em +1, é checagem de robustez do próprio corte
    principal, não um ano falso; fica de fora do painel de placebos por
    isso, filtrado pelo prefixo `placebo_`) com `pre`/`post`, cada um
    `{N_A,N_B,N_AB,N_union,jaccard,salton_cosine,share_AB,checks}`, e
    `pre_range`/`post_range` (`[ano_ini, ano_fim]`); nenhum IC em
    `share_AB` -- não desenha nenhum, não recomputa um.
    `tests.fisher_period_x_cocites_both.p_two_sided` e
    `tests.permutation_delta_share_AB_main.p_value` (os dois só do
    cenário `main` -- a tabela de contingência do Fisher bate com os
    `N_AB` de pré/pós do `main`). `brokerage.{AB,A_only,B_only,
    single_strand}` com `k_cites_focal`/`n`/`rate`, mais
    `odds_ratio_AB_vs_single`.

    Parte 1 (esquerda): `share_AB` antes/depois, pré/pós dodgeados
    dentro do próprio cenário -- `main` em azul, placebos em cinza (o
    MESMO par azul/cinza da parte 2: azul = o sinal real sendo testado,
    cinza = o comparador/controle -- reaproveitado dentro da mesma
    figura, não só entre figuras). Fisher p e permutação p (`main`)
    anotados como texto.

    Parte 2 (direita): taxa de citação ao artigo focal por classe de
    co-citante, barras horizontais do zero -- `AB` em azul, o resto em
    cinza. `k_cites_focal/n` anotado tipo "14/48"; razão de chances
    AB-vs-single-strand como texto.
    """
    cocit = D["cocitacao"]
    fig, (ax_periodos, ax_broker) = plt.subplots(1, 2, figsize=SP.SLOT)

    # ---- parte 1: share_AB antes/depois, main + placebos ----
    periodos = cocit["periods"]
    cenarios = ["main"] + sorted(k for k in periodos if k.startswith("placebo_"))
    x, fracoes, cores, rotulos_fase = [], [], [], []
    centros_grupo, rotulos_grupo = [], []
    xi = 0.0
    for cenario in cenarios:
        bloco_cen = periodos[cenario]
        cor = SP.AZUL if cenario == "main" else SP.CINZA
        ano_corte = bloco_cen["post_range"][0]
        nome_grupo = "main" if cenario == "main" else "placebo"
        par_x = []
        for fase, rotulo_fase in (("pre", "pré"), ("post", "pós")):
            x.append(xi)
            fracoes.append(bloco_cen[fase]["share_AB"])
            cores.append(cor)
            rotulos_fase.append(rotulo_fase)
            par_x.append(xi)
            xi += 1.0
        centros_grupo.append(sum(par_x) / 2)
        rotulos_grupo.append(f"{nome_grupo} ({ano_corte})")
        xi += 0.6  # respiro entre cenários
    x = np.array(x)
    fracoes = np.array(fracoes)
    ax_periodos.bar(x, fracoes * 100, color=cores, width=0.8)
    for xi_, f in zip(x, fracoes):
        ax_periodos.text(
            xi_, f * 100, SP.pct(f), ha="center", va="bottom", fontsize=6.8
        )
    ax_periodos.set_xticks(x)
    ax_periodos.set_xticklabels(rotulos_fase, fontsize=7.2)
    # rótulo do cenário (o corte que separa pré/pós), um só por par --
    # repetir o nome do cenário em CADA barra (duas por par) foi a causa
    # de uma sobreposição real na primeira versão: "placebo 2011" escrito
    # duas vezes lado a lado, num slot de bar estreito, colidia com o
    # "placebo 2011" vizinho. Uma linha curta por par, embaixo do rótulo
    # pré/pós, não. `get_xaxis_transform()`: x em dado, y em fração do
    # eixo -- não depende de onde o y-range dos dados termina.
    for cx, rot in zip(centros_grupo, rotulos_grupo):
        ax_periodos.text(
            cx,
            -0.15,
            rot,
            ha="center",
            va="top",
            fontsize=6.8,
            color=SP.CINZA,
            transform=ax_periodos.get_xaxis_transform(),
        )
    ax_periodos.set_ylim(0, fracoes.max() * 100 * 1.32)
    ax_periodos.set_ylabel("share de co-citação A-B (%)")
    p_fisher = cocit["tests"]["fisher_period_x_cocites_both"]["p_two_sided"]
    p_perm = cocit["tests"]["permutation_delta_share_AB_main"]["p_value"]
    ax_periodos.text(
        0.02,
        0.97,
        f"main: Fisher p={SP.pt(p_fisher, 3)} · permutação p={SP.pt(p_perm, 3)}",
        transform=ax_periodos.transAxes,
        ha="left",
        va="top",
        fontsize=6.4,
        color=SP.CINZA,
    )

    # ---- parte 2: brokerage ----
    broker = cocit["brokerage"]
    y = np.arange(len(COCIT_BROKER_ORDEM))
    taxas = np.array([broker[c]["rate"] for c in COCIT_BROKER_ORDEM])
    cores_b = [SP.AZUL if c == "AB" else SP.CINZA for c in COCIT_BROKER_ORDEM]
    ax_broker.barh(y, taxas * 100, color=cores_b, height=0.55)
    for yi, c in zip(y, COCIT_BROKER_ORDEM):
        ax_broker.text(
            broker[c]["rate"] * 100 + taxas.max() * 100 * 0.02,
            yi,
            f"{SP.pt_int(broker[c]['k_cites_focal'])}/{SP.pt_int(broker[c]['n'])}",
            va="center",
            fontsize=7,
            color=SP.CINZA,
        )
    ax_broker.set_yticks(y)
    ax_broker.set_yticklabels(
        [COCIT_BROKER_LABEL[c] for c in COCIT_BROKER_ORDEM], fontsize=7.6
    )
    ax_broker.invert_yaxis()
    ax_broker.set_xlim(0, taxas.max() * 100 * 1.32)
    ax_broker.set_xlabel("cita o artigo focal (%)")
    razao = broker["odds_ratio_AB_vs_single"]
    ax_broker.text(
        0.98,
        0.03,
        f"razão de chances AB vs single-strand: {SP.pt(razao, 1)}×",
        transform=ax_broker.transAxes,
        ha="right",
        va="bottom",
        fontsize=6.6,
        color=SP.CINZA,
    )
    SP.sem_grade(ax_broker)
    return fig


# ==========================================================================
# Renderização determinística + regras da casa (usadas só por `--check`).
# ==========================================================================


def _renderizar_bytes(fig) -> bytes:
    """Serializa `fig` como PNG determinístico e fecha a figura.

    Mesma disciplina de `sapians.salvar`: ticks em português
    (`SP.eixos_pt`), layout ajustado sem `bbox_inches="tight"` (que faria
    cada PNG sair com uma proporção diferente do `figsize` nominal --
    exatamente o "pecado" que o docstring de `sapians.py` descreve),
    `facecolor` opaco e `metadata` sem timestamp/versão -- pro PNG só
    mudar quando o DESENHO muda, nunca por causa do relógio ou da versão
    instalada do matplotlib. É esse byte que `--check` compara.
    """
    SP.eixos_pt(fig)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.98))
    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        dpi=SP.DPI,
        facecolor=SP.PAPEL,
        metadata={"Software": None, "Creation Time": None},
    )
    plt.close(fig)
    return buf.getvalue()


def _cores_da_figura(fig):
    """Cores de DADO usadas em `fig`: preenchimento de barras/faixas
    (`ax.patches`), marcador/linha de ponto+IC (`ax.lines`) e scatter
    (`ax.collections`). `ax.images` (o heatmap de fig08, `imshow`) fica de
    fora de propósito -- é uma rampa contínua, não uma escolha categórica
    de cor, e a regra "no máximo 5 cores" é sobre codificação categórica
    (a mesma razão pela qual a rampa de azul de fig03/fig05/fig09 conta
    como N cores discretas, não como "1 rampa" -- aqui o heatmap é
    exatamente o caso oposto: cor contínua codificando magnitude, não
    categoria). Eixos/grade/texto/legenda também ficam de fora: são
    moldura, não dado.
    """
    cores = set()
    for ax in fig.get_axes():
        for patch in ax.patches:
            try:
                cores.add(mcolors.to_hex(patch.get_facecolor(), keep_alpha=False))
            except (ValueError, TypeError):
                pass
        for linha in ax.lines:
            cor = linha.get_color()
            if cor is not None:
                try:
                    cores.add(mcolors.to_hex(cor, keep_alpha=False))
                except (ValueError, TypeError):
                    pass
        for col in ax.collections:
            if isinstance(col, mcollections.QuadMesh):
                continue  # ver docstring: rampa contínua, não categórica
            for fc in col.get_facecolors():
                if len(fc):
                    cores.add(mcolors.to_hex(tuple(fc), keep_alpha=False))
            for ec in col.get_edgecolors():
                if len(ec):
                    cores.add(mcolors.to_hex(tuple(ec), keep_alpha=False))
    return cores


def _barras_da_base_zero(fig, nome):
    """ "Barras sempre do zero": nenhum patch de `BarContainer` com base
    negativa, e o limite do eixo (y pra barra vertical, x pra horizontal)
    inclui o zero -- pega tanto uma barra flutuante quanto um eixo
    recortado pra exagerar diferença.
    """
    problemas = []
    for ax in fig.get_axes():
        containers_barra = [
            c for c in ax.containers if isinstance(c, mcontainer.BarContainer)
        ]
        if not containers_barra:
            continue
        tem_vertical = tem_horizontal = False
        for cont in containers_barra:
            horizontal = getattr(cont, "orientation", None) == "horizontal"
            tem_horizontal = tem_horizontal or horizontal
            tem_vertical = tem_vertical or not horizontal
            for patch in cont.patches:
                base = patch.get_x() if horizontal else patch.get_y()
                if base < -1e-9:
                    problemas.append(
                        f"{nome}: barra com base {base:.4f} != 0 (esperada >= 0)"
                    )
        if tem_vertical and min(ax.get_ylim()) > 1e-6:
            problemas.append(f"{nome}: eixo y não inclui o zero (ylim={ax.get_ylim()})")
        if tem_horizontal and min(ax.get_xlim()) > 1e-6:
            problemas.append(f"{nome}: eixo x não inclui o zero (xlim={ax.get_xlim()})")
    return problemas


def _sem_eixo_twin_no_codigo():
    """ "Sem eixo twin": checagem estática no próprio código-fonte -- mais
    simples e mais confiável do que inferir "twin-ness" a partir da
    árvore de Axes em tempo de execução (`twinx`/`twiny` não deixam
    marca própria num objeto Axes comum).

    Os alvos são montados por concatenação de pedaços em vez de escritos
    como um literal de string pronto -- e nem sequer citados por extenso
    neste comentário: o padrão buscado, se aparecesse aqui inteiro (em
    código OU em prosa), apareceria no PRÓPRIO texto desta função quando
    ela lê `__file__` de volta, e essa checagem acusaria a si mesma -- o
    bug que a primeira versão desta função tinha.
    """
    texto = Path(__file__).read_text(encoding="utf-8")
    alvos = ("." + "twinx" + "(", "." + "twiny" + "(")
    return [alvo for alvo in alvos if alvo in texto]


# ==========================================================================
# main
# ==========================================================================


def _dims(png_bytes):
    """(largura, altura) lidos do IHDR de um PNG."""
    import struct

    return struct.unpack(">II", png_bytes[16:24])


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
        help="regenera em memória/diretório temporário e compara byte a byte com reports/01-impacto/figuras/ já gravado; nunca escreve; sai 1 se houver diferença ou violação de regra da casa",
    )
    ap.add_argument(
        "--tolerant",
        action="store_true",
        help="com --check: compara dimensões (IHDR do PNG) e regras da casa, não bytes -- para CI em outra plataforma, onde o Agg/freetype rasteriza diferente; a byte-igualdade vale dentro do venv pinado da máquina que gerou",
    )
    ap.add_argument(
        "--only",
        default=None,
        metavar="NOME",
        help="gera/confere só esta figura (nome do arquivo, com ou sem .png)",
    )
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    root = args.root.resolve()
    _carregar_sapians(root)

    caminho_dados = root / "reports" / "01-impacto" / "dados.json"
    if not caminho_dados.is_file():
        print(
            f"PROBLEMA: {caminho_dados} não existe -- rode tools/audit_70_numbers.py nessa raiz antes."
        )
        return 1
    D = json.loads(caminho_dados.read_text(encoding="utf-8"))

    alvo = SAIDAS
    if args.only:
        nome = args.only if args.only.endswith(".png") else f"{args.only}.png"
        if nome not in SAIDAS:
            print(
                f"PROBLEMA: --only {args.only!r} não é uma figura conhecida. Válidas: {', '.join(sorted(SAIDAS))}"
            )
            return 1
        alvo = {nome: SAIDAS[nome]}

    print(f"-- audit_81_figures: raiz de dados = {root}")
    print(f"-- saída = {OUT_DIR}")
    print(f"-- {len(alvo)} de {len(SAIDAS)} figura(s) selecionada(s)")

    if args.check:
        problemas_gerais = []
        eixo_twin = _sem_eixo_twin_no_codigo()
        if eixo_twin:
            problemas_gerais.append(
                f"uso de eixo twin encontrado no código-fonte: {eixo_twin}"
            )

        divergentes = []
        with tempfile.TemporaryDirectory(prefix="audit_81_check_") as tmp:
            tmp_dir = Path(tmp)
            for nome, func in alvo.items():
                fig = func(D)
                problemas_gerais.extend(_barras_da_base_zero(fig, nome))
                cores = _cores_da_figura(fig)
                if len(cores) > 5:
                    problemas_gerais.append(
                        f"{nome}: {len(cores)} cores distintas (máx. 5): {sorted(cores)}"
                    )
                png_bytes = _renderizar_bytes(fig)
                (tmp_dir / nome).write_bytes(png_bytes)
                atual = OUT_DIR / nome
                commitado = atual.read_bytes() if atual.is_file() else None
                if args.tolerant:
                    # IHDR: largura e altura nos bytes 16..24 -- o que não pode
                    # mudar entre plataformas é a geometria, não o rasterizado.
                    dim_novo = png_bytes[16:24]
                    dim_velho = commitado[16:24] if commitado else None
                    if dim_velho != dim_novo:
                        divergentes.append(
                            f"{nome} (dimensões {_dims(png_bytes)} geradas vs "
                            f"{_dims(commitado) if commitado else 'ausente'} commitadas)"
                        )
                elif commitado != png_bytes:
                    tam_novo = len(png_bytes)
                    tam_velho = len(commitado) if commitado is not None else 0
                    divergentes.append(
                        f"{nome} ({tam_novo} bytes gerados vs {tam_velho} commitados)"
                    )

        for p in problemas_gerais:
            print(f"REGRA DA CASA: {p}")
        if divergentes:
            print(f"DRIFT: {len(divergentes)} figura(s) diferem do gravado:")
            for d in divergentes:
                print(f"  {d}")
        if problemas_gerais or divergentes:
            return 1
        modo = (
            "com as mesmas dimensões das gravadas"
            if args.tolerant
            else "idênticas às gravadas"
        )
        print(f"ok --check: {len(alvo)} figura(s) {modo}, regras da casa OK")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for nome, func in alvo.items():
        fig = func(D)
        png_bytes = _renderizar_bytes(fig)
        destino = OUT_DIR / nome
        destino.write_bytes(png_bytes)
        print(f"figura: {destino} ({len(png_bytes)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
