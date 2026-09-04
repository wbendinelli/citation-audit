"""Etapa 70: fonte única de todo número que um relatório de impacto de citações
pode citar. Lê `config.json` e `data/*.json` (mesmos loaders de `tools/auditlib.py`,
reimplementados aqui para não criar dependência de import em `tools/`) e grava:

  reports/01-impacto/dados.json    -- toda contagem, em JSON, para consumo por script
  reports/01-impacto/numeros.txt   -- as mesmas contagens, em pt-BR, uma por linha,
                                       organizadas em seções `== audit_70 §chave ==`
                                       para que qualquer número em prosa seja
                                       localizável e conferível

Regra do repositório (CLAUDE.md): todo número quantitativo em prosa é impresso
por um script versionado commitado. Este é esse script para o bloco "impacto".

Uso:
  python3 tools/audit_70_numbers.py                    grava os dois arquivos
  python3 tools/audit_70_numbers.py --check             renderiza em memória e
                                                          compara byte a byte com
                                                          os arquivos commitados
                                                          (nunca grava; sai 1 se
                                                          houver diferença)
  python3 tools/audit_70_numbers.py --root PATH         raiz onde ler config.json/
                                                          data/ (padrão: inferida de
                                                          __file__, como auditlib.ROOT)
  python3 tools/audit_70_numbers.py --classify PATH     usa PATH no lugar de
                                                          <root>/data/classify.json

Os arquivos de saída vivem sempre em <pasta do próprio script>/../reports/01-impacto/
-- independente de --root. Isso deixa ler dados de um lugar (ex.: um repositório
só de leitura) e gravar em outro (ex.: um scratchpad), o que é exatamente o caso
de uso da fase de testes deste script: --root aponta pro repositório real, mas a
gravação cai sempre ao lado do próprio tools/audit_70_numbers.py.
"""

import argparse
import html
import json
import os
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

# --------------------------------------------------------------------------
# Caminhos
# --------------------------------------------------------------------------

# Pasta que contém este script é tools/; a raiz-padrão é o pai dela -- mesma
# convenção de auditlib.ROOT (Path(__file__).resolve().parents[1]). Quando
# este script for movido para dentro do repositório real, isso passa a
# resolver sozinho para a raiz do repositório; até lá, --root aponta pra lá.
SCRIPT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = SCRIPT_ROOT / "reports" / "01-impacto"
OUT_DADOS = OUT_DIR / "dados.json"
OUT_NUMEROS = OUT_DIR / "numeros.txt"

PAPERS = ("airline", "grains")

_JSON_KW = dict(ensure_ascii=False, indent=1, sort_keys=True)


# --------------------------------------------------------------------------
# Vocabulário fechado v2 (METHOD.md §16 / auditlib.TAXONOMIA_V2), duplicado
# aqui em vez de importado de tools/auditlib.py -- este script deve rodar
# sozinho (stdlib only) contra QUALQUER --root, inclusive um snapshot que
# não tenha um tools/auditlib.py compatível ao lado.
# --------------------------------------------------------------------------
PRESENCE_VALUES = ["in_text", "reference_list_only", "not_cited"]
DEPTH_ORDER = [
    "drive_by",
    "brief_mention",
    "real_mention",
    "supporting",
    "foundational",
]
ACCURACY_VALUES = ["accurate", "imprecise", "misrepresented"]
DISTORTION_VALUES = ["dead_end", "diversion", "transmutation", "relayed_attribution"]
STANCE_VALUES = ["none", "supporting", "contradictory"]
REUSE_VALUES = [
    "method_adoption",
    "result_validated",
    "dataset_reuse",
    "benchmarking",
    "work_extended",
]
RELATION_VALUES = ["independent", "coauthor", "self"]
RECORD_FLAGS_VALUES = ["duplicate_publication"]
HIGHLIGHT_VALUES = ["none", "good", "best"]

# Eixo "papel" v2-nativo (funde presence+accuracy+depth numa só categoria de 7
# valores) usado nas tabelas periódico×papel e quartil×papel. Mesma prioridade
# de tools/auditlib.role_flag_v1 (fantasma > interpretado errado >
# profundidade), só que com rótulos v2 em vez dos rótulos v1
# (bibliography_only/wrongly_interpreted) -- o resto do relatório é v2.
ROLE_V2_ORDER = [
    "foundational",
    "supporting",
    "real_mention",
    "brief_mention",
    "drive_by",
    "reference_list_only",
    "misrepresented",
]

QUARTIL_ORDER = ["Q1", "Q2", "Q3", "Q4", "fora_do_scimago", "sem_metrica"]

TIMELINE_CLASSES = ["fundo", "conteudo", "passagem", "fantasma"]


# ==========================================================================
# Formatação pt-BR
# ==========================================================================


def pt_int(n):
    """1234 -> '1.234'. Separador de milhar é ponto, como em pt-BR."""
    n = int(n)
    neg = n < 0
    s = str(abs(n))
    grupos = []
    while len(s) > 3:
        grupos.insert(0, s[-3:])
        s = s[:-3]
    grupos.insert(0, s)
    out = ".".join(grupos)
    return ("-" + out) if neg else out


def pt_dec(x, casas=3):
    """0.5714285714 -> '0,571'. Vírgula decimal, arredondamento ROUND_HALF_UP,
    parte inteira com separador de milhar (via pt_int) quando aplicável."""
    if x is None:
        return "-"
    quantum = Decimal(1).scaleb(-casas) if casas else Decimal(1)
    q = Decimal(str(x)).quantize(quantum, rounding=ROUND_HALF_UP)
    neg = q < 0
    q = abs(q)
    s = f"{q:.{casas}f}" if casas else str(int(q))
    if "." in s:
        intpart, decpart = s.split(".")
        s = pt_int(int(intpart)) + "," + decpart
    else:
        s = pt_int(int(s))
    return ("-" + s) if neg else s


def pt_pct(num, den):
    """(73, 98) -> '74%'. ROUND_HALF_UP; '-' se o denominador for 0/None."""
    if not den:
        return "-"
    pct = (Decimal(num) * 100 / Decimal(den)).quantize(
        Decimal(1), rounding=ROUND_HALF_UP
    )
    return f"{pct}%"


def int_leaf(n):
    """Envelope {valor,txt} só quando o separador de milhar muda a
    representação (|n| >= 1000); inteiro puro no resto -- regra do enunciado
    ("plain ints where not [useful]"). Nesta base (~180 registros), a imensa
    maioria das contagens fica como inteiro puro; só constantes grandes
    (B=2000, seed) e afins ganham o envelope."""
    if n is None:
        return None
    txt = pt_int(n)
    return {"valor": n, "txt": txt} if txt != str(n) else n


def dec_leaf(x, casas=3):
    """Envelope {valor,txt} para decimal -- pt-BR troca '.' por ',', então é
    sempre útil (regra do enunciado)."""
    if x is None:
        return None
    return {"valor": x, "txt": pt_dec(x, casas)}


def pct_leaf(num, den):
    """Envelope {valor,pct,ratio} para percentual: razão 0..1 (ou None se
    den=0), '74%' arredondado e a razão crua '73/98' -- as duas formas que o
    enunciado pede lado a lado. `ratio` usa dígitos puros (sem separador de
    milhar) de propósito: é o formato que tools/check_numbers.py espera para
    reconhecer "a/b" como razão (_RATIO_RE = \\d{1,6}/\\d{1,6}) e gerar a
    leitura percentual derivada -- um "1.234" com ponto quebraria o casamento."""
    ratio_txt = f"{int(num)}/{int(den)}"
    if not den:
        return {"valor": None, "pct": "-", "ratio": ratio_txt}
    return {"valor": round(num / den, 4), "pct": pt_pct(num, den), "ratio": ratio_txt}


def PENDENTE(motivo):
    """Marcador uniforme p/ bloco opcional cujo arquivo-fonte não existe (ou
    existe mas está auto-invalidado) -- nunca inventar o número, só apontar o
    motivo. numeros.txt imprime a palavra PENDENTE onde isto aparecer."""
    return {"pendente": True, "motivo": motivo}


def is_pendente(v):
    return isinstance(v, dict) and v.get("pendente") is True


# ==========================================================================
# Carregadores (mesmo padrão de tools/auditlib.py, reimplementado sem import
# para este script não depender de um auditlib.py compatível em --root)
# ==========================================================================


def _read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_optional_json(path):
    """None se o arquivo não existir ou não for JSON válido -- nunca propaga
    exceção, porque a ausência/invalidez é justamente o caso "pendente"."""
    if not path.exists():
        return None
    try:
        return _read_json(path)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None


def load_versioned(path, key):
    """v1 no disco (dict plano) ou v2 (envelope {"meta","<key>"}) -- sempre
    devolve a forma v2 em memória. Mesma regra de auditlib._load_versioned."""
    raw = _read_json(path)
    if isinstance(raw, dict) and "meta" in raw and key in raw:
        return raw
    return {"meta": {"schema": 1}, key: raw}


def load_config(root):
    return _read_json(root / "config.json")


def load_master(root):
    return load_versioned(root / "data" / "master.json", "papers")


def project_v1_to_v2_entry(entry):
    """Projeta uma entrada v1 (role/flag) para a forma v2 (presence/depth/
    accuracy/...). Inverso de auditlib.role_flag_v1 -- usado só se
    data/classify.json ainda estiver no esquema v1 (não deveria mais
    acontecer nesta base, mas o enunciado pede a rede de segurança).

    Regra: role vem do mesmo vocabulário de depth (drive_by..foundational),
    exceto os dois valores sem equivalente direto em depth:
    "bibliography_only" (-> presence=reference_list_only, depth=None) e
    "wrongly_interpreted" (-> accuracy=misrepresented, depth=None -- a
    profundidade real de uma citação mal interpretada não é recuperável só
    do par role/flag v1, então fica None em vez de adivinhada).
    """
    role = entry.get("role")
    flag = entry.get("flag") or None
    if role == "bibliography_only":
        presence, depth = "reference_list_only", None
        accuracy = None
    elif role == "wrongly_interpreted":
        presence, depth = "in_text", None
        accuracy = "misrepresented"
    else:
        presence, depth = "in_text", role
        accuracy = (
            "imprecise"
            if flag == "weak"
            else ("accurate" if presence == "in_text" else None)
        )
    return {
        "presence": presence,
        "depth": depth,
        "accuracy": accuracy,
        "distortion": None,  # eixo novo em v2, sem equivalente em v1
        "stance": entry.get("stance", "none"),
        "reuse": list(entry.get("reuse") or []),
        "relation": "coauthor"
        if flag == "coautor"
        else ("self" if flag == "autocitacao" else "independent"),
        "record_flags": ["duplicate_publication"] if flag == "duplicate" else [],
        "highlight": "best"
        if flag == "best"
        else ("good" if flag == "good" else "none"),
        "claims": [],  # eixo novo em v2, sem equivalente em v1
        "passages": list(entry.get("passages") or []),
        "note": entry.get("note"),
        "prov": entry.get("prov") or {},
    }


def load_classify(root, override_path):
    """data/classify.json (ou override_path). Aceita v1 (chave "role" na
    entrada) e v2 (chave "presence"); v1 é projetado para v2 por
    project_v1_to_v2_entry. Devolve (classify_dict_v2, usou_projecao_v1:bool)."""
    path = (
        override_path
        if override_path is not None
        else (root / "data" / "classify.json")
    )
    raw = load_versioned(path, "entries")
    entries = raw["entries"]
    projected = {}
    used_v1 = False
    for doi, entry in entries.items():
        if "presence" in entry:
            projected[doi] = entry
        else:
            used_v1 = True
            projected[doi] = project_v1_to_v2_entry(entry)
    out = dict(raw)
    out["entries"] = projected
    return out, used_v1


def load_journals(root):
    return load_versioned(root / "data" / "journals.json", "sources")


def load_decisoes_scimago(root):
    p = root / "data" / "decisoes_scimago.json"
    return _read_json(p) if p.exists() else {}


def load_claims(root):
    p = root / "data" / "claims" / "claims.json"
    return _read_json(p) if p.exists() else []


def scholar_listed(root, paper):
    """Linhas não vazias de data/scholar/{paper}.txt -- mesma regra de
    tools/audit_80_report_html.py (SCHOLAR dict)."""
    p = root / "data" / "scholar" / f"{paper}.txt"
    if not p.exists():
        return 0
    with open(p, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


# ==========================================================================
# Normalização / regras de domínio (portadas de tools/audit_80_report_html.py
# e tools/auditlib.py -- ver docstrings de cada uma para a fonte exata)
# ==========================================================================


def norm_doi(d):
    """Idêntico a auditlib.norm_doi: minúsculas, sem prefixo de URL/"doi:"."""
    if not d:
        return None
    d = d.strip().lower()
    d = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", d)
    d = re.sub(r"^doi:", "", d)
    return d or None


def doi_prefix(doi):
    return (doi or "").split("/", 1)[0]


def is_book_like(doi):
    """Porte literal de audit_80_report_html._livro: DOI com cara de
    ISBN/capítulo. É a ÚNICA checagem do critério 3 de "população" (METHOD.md
    §9: "é artigo de periódico") -- deliberadamente SEM olhar `work_type`,
    porque é assim que tools/audit_80_report_html.py já implementa (e o
    resultado bate com o "87 citações" canônico de METHOD.md §9 e com
    data/base_rates.json). Proxy imperfeito por desenho: capítulo publicado
    com DOI no padrão de artigo comum (ex.: séries de livro da Emerald, como
    10.1108/s2212-...) passa batido mesmo com work_type=book-chapter -- ver
    CLAUDE.md "Recontar a população... por conta própria" antes de
    "corrigir" isso, é decisão de escopo registrada, não bug."""
    if not doi:
        return False
    suf = doi.split("/", 1)[1] if "/" in doi else ""
    return (
        suf.startswith("978")
        or "9781" in suf
        or "9780" in suf
        or doi.startswith("10.1007/978")
    )


_VENUE_FIX = {
    "journal of business research": "Journal of Business Research",
    "journal of plant diseases and protection": "Journal of Plant Diseases and Protection",
    "handbook of agricultural economics": "Handbook of Agricultural Economics",
    "transportation research part e: logistics and transportation review": "Transportation Research Part E",
    "transportation research part e: logistics and t": "Transportation Research Part E",
    "transportation research part a: policy and practice": "Transportation Research Part A",
    "transportation research part c emerging technologies": "Transportation Research Part C",
    "transportation research part b: methodological": "Transportation Research Part B",
}


def venue_norm(v):
    """Porte literal de audit_80_report_html.venue_norm: desescapa HTML,
    colapsa "Transportation Research Part X: ..." e corrige a grafia de
    alguns veículos recorrentes."""
    v = html.unescape(v or "?").strip()
    v = re.sub(r"\s+", " ", v)
    v = re.sub(r"(Transportation Research Part [A-F])\s*:?\s*", r"\1: ", v)
    v = re.sub(r"\s*[:,]\s*$", "", v)
    for a, b in _VENUE_FIX.items():
        if v.lower().startswith(a[:40]):
            return b
    return v


def quartil_scimago(rec, sources):
    """Idêntico a auditlib.quartil_scimago: Q1..Q4 oficial ou None (sem
    correspondência no Scimago OU quartil em branco "-")."""
    m = sources.get(rec.get("source_id") or "")
    if not m:
        return None
    sc = m.get("scimago")
    if not sc:
        return None
    q = sc.get("quartil")
    return q if q in ("Q1", "Q2", "Q3", "Q4") else None


def quartile_bucket(rec, sources):
    """Porte literal de audit_80_report_html.quart: Q1..Q4, "fora_do_scimago"
    (tem periódico identificado mas o Scimago não dá quartil) ou
    "sem_metrica" (nem periódico foi identificado)."""
    m = sources.get(rec.get("source_id") or "")
    if not m:
        return "sem_metrica"
    sc = m.get("scimago")
    if sc and sc.get("quartil") in ("Q1", "Q2", "Q3", "Q4"):
        return sc["quartil"]
    return "fora_do_scimago"


def axis_role(entry):
    """Eixo "papel" v2-nativo (7 valores) -- ver ROLE_V2_ORDER acima."""
    if entry["presence"] == "reference_list_only":
        return "reference_list_only"
    if entry.get("accuracy") == "misrepresented":
        return "misrepresented"
    return entry.get("depth")


def timeline_class(entry):
    """Classe de tempo (linha_do_tempo): fundo=supporting+foundational,
    conteudo=real_mention, passagem=drive_by+brief_mention,
    fantasma=reference_list_only. not_cited não tem classe (nunca
    aconteceu nos dados até agora -- ver auditlib.role_flag_v1)."""
    if entry["presence"] == "reference_list_only":
        return "fantasma"
    if entry["presence"] == "not_cited":
        return None
    depth = entry.get("depth")
    if depth in ("supporting", "foundational"):
        return "fundo"
    if depth == "real_mention":
        return "conteudo"
    if depth in ("drive_by", "brief_mention"):
        return "passagem"
    return None


def editora_de(doi, editoras_estabelecidas):
    return editoras_estabelecidas.get(doi_prefix(doi))


# ==========================================================================
# Estruturas auxiliares
# ==========================================================================


class Ctx:
    """Carrega tudo uma vez e guarda em memória -- todo builder de bloco
    recebe isto em vez de reabrir arquivo."""

    def __init__(self, root, classify_override):
        self.root = root
        self.config = load_config(root)
        self.master = load_master(root)
        self.classify, self.used_v1_projection = load_classify(root, classify_override)
        self.journals = load_journals(root)
        self.decisoes_scimago = load_decisoes_scimago(root)
        self.claims = load_claims(root)

        self.entries = self.classify["entries"]  # doi -> entrada v2
        self.sources = self.journals["sources"]  # source_id -> periódico
        self.editoras_estabelecidas = self.config["editoras_estabelecidas"]

        # índice doi normalizado -> (paper, registro de master.json), só p/
        # registros com DOI -- usado por todo bloco que cruza classify x master
        self.by_doi = {}
        for paper in PAPERS:
            for rec in self.master["papers"][paper]["citing"]:
                d = norm_doi(rec.get("doi"))
                if d:
                    self.by_doi[d] = (paper, rec)

        # entrada de classify.json ligada ao registro de master.json que ela
        # classifica -- só entra aqui se o DOI resolver a um registro real
        # (classify_orfas.json, fora do escopo deste script, é o caso em que
        # não resolve mais).
        self.classified = []  # lista de (paper, rec, doi, entry)
        for doi, entry in self.entries.items():
            hit = self.by_doi.get(doi)
            if hit:
                paper, rec = hit
                self.classified.append((paper, rec, doi, entry))

    def citing(self, paper=None):
        if paper:
            return self.master["papers"][paper]["citing"]
        return [r for p in PAPERS for r in self.master["papers"][p]["citing"]]

    def classified_for(self, paper=None):
        if paper:
            return [(p, r, d, e) for (p, r, d, e) in self.classified if p == paper]
        return self.classified


# ==========================================================================
# Blocos de dados.json
# ==========================================================================


def build_meta(ctx, hoje):
    cd_backend = {}
    for paper in PAPERS:
        cd = read_optional_json(ctx.root / "data" / "cd" / f"cd_{paper}.json")
        cd_backend[paper] = cd.get("backend") if (cd and "windows" in cd) else None
    return {
        "gerado_em": hoje,
        "fontes": ctx.master["meta"].get("fontes"),
        "scholar": ctx.master["meta"].get("scholar"),
        "n_registros": len(ctx.citing()),
        "n_classificados": len(ctx.classified),
        "codebook": ctx.classify["meta"].get("codebook"),
        "backend_cd": cd_backend,
        "usou_projecao_classify_v1": ctx.used_v1_projection,
    }


def build_artigos(ctx):
    out = {}
    for paper in PAPERS:
        p = ctx.config["papers"][paper]
        out[paper] = {
            "doi": p["doi"],
            "titulo": p["title"],
            "veiculo": p["venue"],
            "ano": p["year"],
            "n_citantes": len(ctx.citing(paper)),
        }
    return out


def _counter_dict(items):
    """Counter -> dict com chaves sempre string (None vira o rótulo
    "sem_valor", porque chave de objeto JSON tem que ser string)."""
    from collections import Counter

    c = Counter(items)
    return {
        (k if k is not None else "sem_valor"): v
        for k, v in sorted(c.items(), key=lambda kv: str(kv[0]))
    }


def build_inventario(ctx):
    todos = ctx.citing()
    com_doi = [r for r in todos if r.get("doi")]
    sem_doi = [r for r in todos if not r.get("doi")]
    out = {
        "total": len(todos),
        "classificados": len(ctx.classified),
        "por_artigo": {p: len(ctx.citing(p)) for p in PAPERS},
        "com_doi": {
            "total": len(com_doi),
            **{p: sum(1 for r in ctx.citing(p) if r.get("doi")) for p in PAPERS},
        },
        "sem_doi": {
            "total": len(sem_doi),
            **{p: sum(1 for r in ctx.citing(p) if not r.get("doi")) for p in PAPERS},
        },
        "por_status": _counter_dict(r.get("status") for r in todos),
        "por_status_por_artigo": {
            p: _counter_dict(r.get("status") for r in ctx.citing(p)) for p in PAPERS
        },
        "por_work_type": _counter_dict(r.get("work_type") for r in todos),
        "por_work_type_por_artigo": {
            p: _counter_dict(r.get("work_type") for r in ctx.citing(p)) for p in PAPERS
        },
    }
    return out


FUNIL_ROTULOS = [
    (
        "Google Scholar reporta",
        "Contagem de linhas não vazias em data/scholar/{paper}.txt",
    ),
    (
        "Inventário após dedup e ruído",
        "União OpenAlex+S2+OpenCitations+EuropePMC+Scholar, deduplicada por DOI e título normalizado",
    ),
    ("Com DOI depositado", "Campo doi presente e não vazio no registro"),
    (
        "Editora estabelecida",
        "Prefixo do DOI está em config.json/editoras_estabelecidas",
    ),
    (
        "Periódico (sem capítulo, anais, preprint)",
        'DOI sem cara de ISBN/capítulo (sufixo começando 978, contendo 9781/9780, ou prefixo 10.1007/978) -- proxy de "é artigo de periódico" (METHOD.md §9); ver nota em is_book_like',
    ),
    ("Com evidência verificada", "DOI tem entrada em data/classify.json"),
]


def _funil_steps(ctx, paper):
    recs = ctx.citing(paper)
    scholar = scholar_listed(ctx.root, paper)
    com_doi = [r for r in recs if r.get("doi")]
    editora = [
        r
        for r in com_doi
        if doi_prefix(norm_doi(r["doi"])) in ctx.editoras_estabelecidas
    ]
    periodico = [r for r in editora if not is_book_like(norm_doi(r["doi"]))]
    evidencia = [r for r in periodico if norm_doi(r["doi"]) in ctx.entries]
    valores = [
        scholar,
        len(recs),
        len(com_doi),
        len(editora),
        len(periodico),
        len(evidencia),
    ]
    steps = []
    for i, (rotulo, motivo) in enumerate(FUNIL_ROTULOS):
        valor = valores[i]
        delta = None if i == 0 else valores[i] - valores[i - 1]
        steps.append(
            {
                "rotulo": rotulo,
                "motivo": motivo,
                "valor": int_leaf(valor),
                "delta": delta,
            }
        )
    return steps, valores


def build_funil(ctx):
    out = {}
    valores_por_paper = {}
    for paper in PAPERS:
        steps, valores = _funil_steps(ctx, paper)
        out[paper] = {"steps": steps}
        valores_por_paper[paper] = valores
    linhas = []
    for i, (rotulo, motivo) in enumerate(FUNIL_ROTULOS):
        linha = {"rotulo": rotulo, "motivo": motivo}
        for paper in PAPERS:
            valores = valores_por_paper[paper]
            txt = pt_int(valores[i])
            if i > 0:
                delta = valores[i] - valores[i - 1]
                if delta != 0:
                    txt += f" ({delta:+d})"
            linha[f"{paper}_txt"] = txt
        linhas.append(linha)
    out["linhas"] = linhas
    return out, valores_por_paper


def build_populacao(ctx, funil_valores):
    # "Periódico" é o índice 4 (0-based) na lista FUNIL_ROTULOS/valores.
    pop = {p: funil_valores[p][4] for p in PAPERS}
    total = sum(pop.values())
    classificados = {p: funil_valores[p][5] for p in PAPERS}
    return {
        "total": total,
        **pop,
        "classificados_dentro_da_populacao": {
            "total": sum(classificados.values()),
            **classificados,
        },
    }


def build_cobertura_quartil(ctx):
    """Universo: registros com DOI e com quartil Scimago oficial (Q1..Q4),
    QUALQUER work_type (bloco não usa o filtro de "população"). Partição
    validada em 4 categorias mutuamente exclusivas e exaustivas -- ver
    verify_cobertura_partition()."""

    pendentes = []

    def bucket(paper_filter):
        rows = {
            q: {
                "total": 0,
                "trecho": 0,
                "fantasma": 0,
                "aresta_falsa": 0,
                "pendente": 0,
            }
            for q in ("Q1", "Q2", "Q3", "Q4")
        }
        for paper in PAPERS:
            if paper_filter and paper != paper_filter:
                continue
            for r in ctx.citing(paper):
                d = norm_doi(r.get("doi"))
                if not d:
                    continue
                q = quartil_scimago(r, ctx.sources)
                if not q:
                    continue
                row = rows[q]
                row["total"] += 1
                entry = ctx.entries.get(d)
                if r.get("status") == "aresta_falsa":
                    row["aresta_falsa"] += 1
                elif entry and entry["presence"] == "reference_list_only":
                    row["fantasma"] += 1
                elif entry and entry["presence"] == "in_text" and entry.get("passages"):
                    row["trecho"] += 1
                elif not entry:
                    row["pendente"] += 1
                    if paper_filter is None:
                        pendentes.append(
                            {
                                "id": r["id"],
                                "doi": d,
                                "quartil": q,
                                "editora": (
                                    ctx.sources.get(r.get("source_id")) or {}
                                ).get("editora"),
                                "status": r.get("status"),
                            }
                        )
                else:
                    row["pendente"] += (
                        1  # rede de segurança; não deveria acontecer (ver verificação)
                    )
        return rows

    def finalize(rows):
        out = {}
        tot = {"total": 0, "trecho": 0, "fantasma": 0, "aresta_falsa": 0, "pendente": 0}
        for q, row in rows.items():
            for k in tot:
                tot[k] += row[k]
            out[q] = {
                "total": row["total"],
                "trecho": row["trecho"],
                "fantasma": row["fantasma"],
                "aresta_falsa": row["aresta_falsa"],
                "pendente": row["pendente"],
                "pct_trecho": pct_leaf(row["trecho"], row["total"]),
                "pct_evidencia": pct_leaf(
                    row["trecho"] + row["fantasma"], row["total"]
                ),
            }
        out["total"] = {
            "total": tot["total"],
            "trecho": tot["trecho"],
            "fantasma": tot["fantasma"],
            "aresta_falsa": tot["aresta_falsa"],
            "pendente": tot["pendente"],
            "pct_trecho": pct_leaf(tot["trecho"], tot["total"]),
            "pct_evidencia": pct_leaf(tot["trecho"] + tot["fantasma"], tot["total"]),
        }
        return out

    pooled = finalize(bucket(None))
    por_artigo = {p: finalize(bucket(p)) for p in PAPERS}
    pendentes.sort(key=lambda x: x["id"])
    return {**pooled, "por_artigo": por_artigo, "pendentes": pendentes}


def build_quartil(ctx):
    def bucket(recs):
        return _counter_dict(quartile_bucket(r, ctx.sources) for r in recs)

    def bucket_classificados(recs):
        sel = [r for r in recs if norm_doi(r.get("doi")) in ctx.entries]
        return _counter_dict(quartile_bucket(r, ctx.sources) for r in sel)

    todas = {p: bucket(ctx.citing(p)) for p in PAPERS}
    todas["pooled"] = bucket(ctx.citing())
    classificadas = {p: bucket_classificados(ctx.citing(p)) for p in PAPERS}
    classificadas["pooled"] = bucket_classificados(ctx.citing())

    from collections import Counter

    veredito = Counter(v["veredito"] for v in ctx.decisoes_scimago.values())
    razao = Counter(v["razao"] for v in ctx.decisoes_scimago.values())
    ausencia = {
        "total_decisoes": len(ctx.decisoes_scimago),
        "correto": veredito.get("correto", 0),
        "periodico": veredito.get("periodico", 0),
        "por_razao": dict(sorted(razao.items())),
    }
    return {
        "todas_citacoes": todas,
        "classificadas": classificadas,
        "ausencia": ausencia,
    }


def build_editoras(ctx):
    def bucket(recs):
        out = {}
        for r in recs:
            d = norm_doi(r.get("doi"))
            if not d:
                continue
            nome = (
                editora_de(d, ctx.editoras_estabelecidas)
                or "não listada em config.editoras_estabelecidas"
            )
            out[nome] = out.get(nome, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))

    out = {p: bucket(ctx.citing(p)) for p in PAPERS}
    out["pooled"] = bucket(ctx.citing())
    return out


def _journals_json_resumo(ctx):
    """Recorte de data/journals.json: TODAS as fontes dos citantes (README §2 fala
    deste recorte), não só as dos classificados -- os dois números convivem."""
    jj = read_optional_json(ctx.root / "data" / "journals.json") or {}
    src = jj.get("sources") or {}
    vals = list(src.values()) if isinstance(src, dict) else list(src)
    casados = [v for v in vals if v.get("scimago")]
    quart = [(v.get("scimago") or {}).get("quartil") for v in casados]
    com_q = [q for q in quart if q in ("Q1", "Q2", "Q3", "Q4")]
    return {
        "total_fontes": len(vals),
        "scimago_casados": len(casados),
        "scimago_casados_com_quartil": len(com_q),
        "scimago_casados_sem_quartil": len(casados) - len(com_q),
        "nao_casados": len(vals) - len(casados),
        "por_quartil": _counter_dict(com_q),
    }


def build_periodicos(ctx):
    """Universo: "população" (DOI + editora estabelecida + periódico, mesmo
    filtro do funil) ∩ classificados -- porte de
    audit_80_report_html.render_revistas. Agrupado por venue_norm(venue)."""

    def populacao_classificada(paper):
        out = []
        for r in ctx.citing(paper):
            d = norm_doi(r.get("doi"))
            if (
                not d
                or doi_prefix(d) not in ctx.editoras_estabelecidas
                or is_book_like(d)
            ):
                continue
            entry = ctx.entries.get(d)
            if entry:
                out.append((r, entry))
        return out

    def build_group(rows):
        from collections import defaultdict

        groups = defaultdict(list)
        for r, entry in rows:
            groups[venue_norm(r.get("venue"))].append((r, entry))
        lista = []
        for nome, items in groups.items():
            rep = ctx.sources.get(items[0][0].get("source_id") or "")
            sc = (rep or {}).get("scimago")
            papeis = _counter_dict(axis_role(e) for _, e in items)
            lista.append(
                {
                    "nome_norm": nome,
                    "quartil": (sc.get("quartil") if sc else None),
                    "sjr": dec_leaf(sc.get("sjr"))
                    if sc and sc.get("sjr") is not None
                    else None,
                    "overton": dec_leaf(sc.get("overton"), 0)
                    if sc and sc.get("overton") is not None
                    else None,
                    "n": len(items),
                    "papeis": papeis,
                    "reuso_n": sum(1 for _, e in items if e.get("reuse")),
                }
            )
        lista.sort(key=lambda row: (-row["n"], row["nome_norm"]))
        return lista

    por_artigo = {}
    todas_rows = []
    for paper in PAPERS:
        rows = populacao_classificada(paper)
        todas_rows.extend(rows)
        por_artigo[paper] = build_group(rows)

    pooled_lista = build_group(todas_rows)
    total = len(pooled_lista)
    casados = [j for j in pooled_lista if j["quartil"] is not None]
    quartis = _counter_dict(j["quartil"] for j in casados)

    return {
        "fontes_journals_json": _journals_json_resumo(ctx),
        "total": total,
        "scimago_casados": len(casados),
        "quartis": quartis,
        "por_artigo": por_artigo,
        "pooled": pooled_lista,
    }


def _axis_tally(items, universe_values, D):
    """{valor: {n,D,ratio,pct}} p/ um eixo de rótulo único (não multi-label).
    universe_values fixa a ordem/o conjunto de categorias impressas (mesmo
    sem contagem, para o vocabulário fechado ficar visível)."""
    from collections import Counter

    c = Counter(items)
    out = {}
    for v in universe_values:
        n = c.get(v, 0)
        out[v] = {"n": n, "D": D, **pct_leaf(n, D)}
    return out


def _multilabel_tally(list_of_lists, universe_values, D):
    """Mesma ideia, mas para eixo multi-rótulo (reuse, record_flags): um
    registro pode contribuir para mais de uma categoria, então a soma dos n
    pode passar de D -- não é bug, é overlap esperado de eixo multi-label."""
    from collections import Counter

    c = Counter(tag for lst in list_of_lists for tag in (lst or []))
    out = {}
    for v in universe_values:
        n = c.get(v, 0)
        out[v] = {"n": n, "D": D, **pct_leaf(n, D)}
    return out


def build_eixos(ctx):
    def for_universe(rows):
        # rows: lista de entradas v2 (dict) já filtradas por paper/pooled
        all_n = len(rows)
        in_text_rows = [e for e in rows if e["presence"] == "in_text"]
        D_all = all_n
        D_txt = len(in_text_rows)

        substantivo_n = sum(
            1 for e in in_text_rows if e.get("depth") in ("supporting", "foundational")
        )
        perfunctorio_n = sum(
            1 for e in in_text_rows if e.get("depth") in ("drive_by", "brief_mention")
        )
        background_n = sum(
            1
            for e in in_text_rows
            if e.get("depth") in ("drive_by", "brief_mention", "real_mention")
            and not e.get("reuse")
        )

        return {
            "presence": _axis_tally(
                (e["presence"] for e in rows), PRESENCE_VALUES, D_all
            ),
            "depth": _axis_tally(
                (e.get("depth") for e in in_text_rows), DEPTH_ORDER, D_txt
            ),
            "stance": _axis_tally(
                (e.get("stance") for e in in_text_rows), STANCE_VALUES, D_txt
            ),
            "accuracy": _axis_tally(
                (e.get("accuracy") for e in in_text_rows), ACCURACY_VALUES, D_txt
            ),
            "distortion": _axis_tally(
                (e.get("distortion") for e in in_text_rows if e.get("distortion")),
                DISTORTION_VALUES,
                D_txt,
            ),
            "reuse": _multilabel_tally(
                (e.get("reuse") for e in in_text_rows), REUSE_VALUES, D_txt
            ),
            "relation": _axis_tally(
                (e.get("relation") for e in rows), RELATION_VALUES, D_all
            ),
            "record_flags": _multilabel_tally(
                (e.get("record_flags") for e in rows), RECORD_FLAGS_VALUES, D_all
            ),
            "highlight": _axis_tally(
                (e.get("highlight") for e in in_text_rows), HIGHLIGHT_VALUES, D_txt
            ),
            "substantivo": {
                "n": substantivo_n,
                "D": D_txt,
                **pct_leaf(substantivo_n, D_txt),
                "definicao": "supporting + foundational",
            },
            "perfunctorio": {
                "n": perfunctorio_n,
                "D": D_txt,
                **pct_leaf(perfunctorio_n, D_txt),
                "definicao": "drive_by + brief_mention",
            },
            "background_like": {
                "n": background_n,
                "D": D_txt,
                **pct_leaf(background_n, D_txt),
                "definicao": "drive_by + brief_mention + real_mention com reuse vazio",
            },
        }

    out = {}
    for paper in PAPERS:
        rows = [e for (p, r, d, e) in ctx.classified_for(paper)]
        out[paper] = for_universe(rows)
    out["pooled"] = for_universe([e for (p, r, d, e) in ctx.classified])
    return out


def build_papel_quartil(ctx):
    """Matriz quartil(6 baldes) x papel(7 valores v2), porte de
    audit_80_report_html.matriz_q -- SEM o filtro de "população" (mesmo
    universo do bloco `quartil`: todo classificado com DOI, qualquer
    work_type). Mais reuso_por_quartil/fantasma_por_quartil (_reuse_q/_ghost_q
    do mesmo arquivo)."""

    def build(rows):
        from collections import Counter, defaultdict

        matriz = defaultdict(Counter)
        reuso_q = Counter()
        fantasma_q = Counter()
        for r, e in rows:
            q = quartile_bucket(r, ctx.sources)
            matriz[q][axis_role(e)] += 1
            if e.get("reuse"):
                reuso_q[q] += 1
            if e["presence"] == "reference_list_only":
                fantasma_q[q] += 1
        return (
            {
                q: {role: matriz[q].get(role, 0) for role in ROLE_V2_ORDER}
                for q in QUARTIL_ORDER
                if matriz.get(q)
            },
            {q: reuso_q.get(q, 0) for q in QUARTIL_ORDER if reuso_q.get(q)},
            {q: fantasma_q.get(q, 0) for q in QUARTIL_ORDER if fantasma_q.get(q)},
        )

    out = {}
    todas_rows = []
    for paper in PAPERS:
        rows = [(r, e) for (p, r, d, e) in ctx.classified_for(paper)]
        todas_rows.extend(rows)
        matriz, reuso_q, fantasma_q = build(rows)
        out[paper] = {
            "matriz": matriz,
            "reuso_por_quartil": reuso_q,
            "fantasma_por_quartil": fantasma_q,
        }
    matriz, reuso_q, fantasma_q = build(todas_rows)
    out["pooled"] = {
        "matriz": matriz,
        "reuso_por_quartil": reuso_q,
        "fantasma_por_quartil": fantasma_q,
    }
    return out


def build_linha_do_tempo(ctx):
    from collections import Counter, defaultdict

    out = {}
    for paper in PAPERS:
        por_ano = defaultdict(Counter)
        for p, r, d, e in ctx.classified_for(paper):
            cls = timeline_class(e)
            if cls:
                por_ano[r.get("year")][cls] += 1
        out[paper] = {
            str(ano): {cls: contagem.get(cls, 0) for cls in TIMELINE_CLASSES}
            for ano, contagem in sorted(
                por_ano.items(), key=lambda kv: (kv[0] is None, kv[0])
            )
        }
    return out


def build_alegacoes(ctx):
    from collections import defaultdict

    # cada entrada de classify pode referenciar 0+ claims em `claims[]`
    citations_por_claim = defaultdict(list)
    for paper, rec, doi, entry in ctx.classified:
        for claim_id in entry.get("claims") or []:
            citations_por_claim[claim_id].append(entry)

    claims_out = {}
    for c in ctx.claims:
        cid = c["id"]
        cited_by = citations_por_claim.get(cid, [])
        claims_out[cid] = {
            "paper": c["paper"],
            "type": c["type"],
            "status": c["status"],
            "n_citations": len(cited_by),
            "n_faithful": sum(1 for e in cited_by if e.get("accuracy") == "accurate"),
            "n_imprecise": sum(1 for e in cited_by if e.get("accuracy") == "imprecise"),
            "n_misrepresented": sum(
                1 for e in cited_by if e.get("accuracy") == "misrepresented"
            ),
        }

    por_artigo = {}
    for paper in PAPERS:
        claims_p = [c for c in ctx.claims if c["paper"] == paper]
        por_artigo[paper] = {
            "total": len(claims_p),
            "por_type": _counter_dict(c["type"] for c in claims_p),
            "por_status": _counter_dict(c["status"] for c in claims_p),
        }

    sustentadas = [cid for cid, v in claims_out.items() if v["n_citations"] >= 1]
    for paper in PAPERS:
        por_artigo[paper]["sustentadas"] = sum(
            1 for cid in sustentadas if claims_out[cid]["paper"] == paper
        )
    return {
        "total": len(ctx.claims),
        "sustentadas": len(sustentadas),
        "sem_citacao": len(claims_out) - len(sustentadas),
        "por_type": _counter_dict(c["type"] for c in ctx.claims),
        "por_status": _counter_dict(c["status"] for c in ctx.claims),
        "por_artigo": por_artigo,
        "claims": claims_out,
    }


ANOMALIA_TIPOS = [
    "fantasma",
    "aresta_falsa",
    "misrepresented",
    "imprecise",
    "duplicate_publication",
    "self",
    "coauthor",
]


def build_anomalias(ctx):
    """Uma linha por (registro, tipo de anomalia que ele apresenta) -- um
    registro pode aparecer sob mais de um tipo (ex.: misrepresented + self),
    então a soma de `por_tipo` pode passar do nº de registros anômalos
    distintos. `por_artigo` conta linhas, não registros distintos, pela mesma
    razão."""
    registros = []

    def add(r, tipo, doi, quartil, subcodigo, evidencia, paper):
        registros.append(
            {
                "id": r["id"],
                "paper": paper,
                "doi": doi,
                "veiculo": r.get("venue"),
                "quartil": quartil,
                "tipo": tipo,
                "subcodigo": subcodigo,
                "evidencia": evidencia,
            }
        )

    for paper, rec, doi, entry in ctx.classified:
        quartil = quartil_scimago(rec, ctx.sources)
        subcodigo = entry.get("distortion")
        evidencia = (entry.get("prov") or {}).get("evidence_kind")
        if entry["presence"] == "reference_list_only":
            add(rec, "fantasma", doi, quartil, subcodigo, evidencia, paper)
        if entry.get("accuracy") == "misrepresented":
            add(rec, "misrepresented", doi, quartil, subcodigo, evidencia, paper)
        if entry.get("accuracy") == "imprecise":
            add(rec, "imprecise", doi, quartil, subcodigo, evidencia, paper)
        if "duplicate_publication" in (entry.get("record_flags") or []):
            add(rec, "duplicate_publication", doi, quartil, subcodigo, evidencia, paper)
        if entry.get("relation") == "self":
            add(rec, "self", doi, quartil, subcodigo, evidencia, paper)
        if entry.get("relation") == "coauthor":
            add(rec, "coauthor", doi, quartil, subcodigo, evidencia, paper)

    # aresta_falsa é veredito no registro de master.json, não em classify.json
    # (CLAUDE.md: "aresta_falsa é veredito manual terminal" -- essas citações
    # nunca chegam a ser classificadas, porque não há o que classificar).
    for paper in PAPERS:
        for r in ctx.citing(paper):
            if r.get("status") == "aresta_falsa":
                d = norm_doi(r.get("doi"))
                add(
                    r,
                    "aresta_falsa",
                    d,
                    quartil_scimago(r, ctx.sources) if d else None,
                    None,
                    None,
                    paper,
                )

    registros.sort(key=lambda row: (row["paper"], row["tipo"], row["id"]))
    return {
        "registro": registros,
        "por_tipo": _counter_dict(row["tipo"] for row in registros),
        "por_artigo": _counter_dict(row["paper"] for row in registros),
    }


def build_inventario_classificados(ctx):
    """Anexo A: uma linha por citação classificada (id, veículo normalizado,
    ano, quartil, os 7 eixos v2 relevantes). Ordenado por (paper, id) para
    determinismo."""
    out = []
    for paper, rec, doi, entry in sorted(
        ctx.classified, key=lambda t: (t[0], t[1]["id"])
    ):
        out.append(
            {
                "id": rec["id"],
                "paper": paper,
                "veiculo_norm": venue_norm(rec.get("venue")),
                "ano": rec.get("year"),
                "quartil": quartil_scimago(rec, ctx.sources),
                "presence": entry["presence"],
                "depth": entry.get("depth"),
                "stance": entry.get("stance"),
                "accuracy": entry.get("accuracy"),
                "reuse": list(entry.get("reuse") or []),
                "relation": entry.get("relation"),
                "highlight": entry.get("highlight"),
            }
        )
    return out


# ---------------- blocos opcionais (pendente quando o arquivo-fonte falta) ----------------


def build_cd(ctx):
    out = {}
    for paper in PAPERS:
        refs = read_optional_json(ctx.root / "data" / "cd" / f"refs_audit_{paper}.json")
        cd = read_optional_json(ctx.root / "data" / "cd" / f"cd_{paper}.json")
        block = {}
        if refs is not None:
            false_refs = refs.get("false_references") or []
            unresolvable = refs.get("unresolvable") or []
            block["refs_audit"] = {
                "n_openalex_raw": refs.get("n_openalex_raw"),
                "n_pdf": refs.get("n_pdf"),
                "n_valid": refs.get("n_valid"),
                "n_false_references": len(false_refs),
                "n_unresolvable": len(unresolvable),
                "false_references": [
                    {
                        "openalex_id": x.get("id"),
                        "titulo": x.get("title"),
                        "ano": x.get("year"),
                    }
                    for x in false_refs
                ],
                "unresolvable": [
                    {
                        "titulo": x.get("title"),
                        "ano": x.get("year"),
                        "n_no_pdf": x.get("n"),
                    }
                    for x in unresolvable
                ],
            }
        else:
            block["refs_audit"] = PENDENTE(
                f"data/cd/refs_audit_{paper}.json não existe"
            )

        if cd is not None and "windows" in cd:
            block["cd_index"] = {
                "windows": cd.get("windows"),
                "loo": cd.get("loo"),
                "crosstab": cd.get("crosstab"),
                "fisher_p": cd.get("fisher_p"),
                "backend": cd.get("backend"),
            }
        elif cd is not None:
            motivo = (
                cd.get("motivo")
                or cd.get("status")
                or "arquivo presente sem a chave 'windows' (dado incompleto/invalidado)"
            )
            block["cd_index"] = PENDENTE(f"data/cd/cd_{paper}.json: {motivo}")
        else:
            block["cd_index"] = PENDENTE(f"data/cd/cd_{paper}.json não existe")
        out[paper] = block
    return out


def build_cocitacao(ctx):
    path = ctx.root / "data" / "cocit" / "cocit_airline.json"
    data = read_optional_json(path)
    if data is None:
        return PENDENTE(
            "data/cocit/cocit_airline.json não existe (só data/cocit/seeds_airline.json, que é insumo, não resultado)"
        )
    return {
        "periods": data.get("periods"),
        "brokerage": data.get("brokerage"),
        "tests": data.get("tests"),
        "passage_confirmation": data.get("passage_confirmation"),
    }


def _published_txt(published):
    """'25.4% (Jergas…); 13.1-20.4%' -> ['25,4%', '13,1%', '20,4%']: o walker só
    imprime número, e a prosa cita esses valores da literatura."""
    if not isinstance(published, str):
        return None
    nums = re.findall(r"\d+(?:\.\d+)?(?=\s*%|-\d)", published)
    return [n.replace(".", ",") + "%" for n in nums] or None


def build_taxa_base(ctx):
    path = ctx.root / "data" / "base_rates.json"
    data = read_optional_json(path)
    if data is None:
        return PENDENTE("data/base_rates.json não existe")
    for row in data.get("rows") or []:
        txt = _published_txt(row.get("published"))
        if txt:
            row["published_txt"] = txt
    return data


def build_fantasmas_auditados(ctx):
    path = ctx.root / "data" / "ghost_audit.json"
    data = read_optional_json(path)
    if data is None:
        return PENDENTE("data/ghost_audit.json não existe")
    return data


def _summarize_irr_axis_pairs(pairs, axis):
    """pairs = irr_stats["pairs"] (c1_vs_c2, c1_vs_c3, ...). Devolve, por par
    de codificadores, o sub-dicionário inteiro daquele eixo dentro de
    `primary`, tal como existe no arquivo -- sem tentar forçar um esquema
    fixo. Eixos diferentes têm formatos bem diferentes nos dados reais (ex.:
    "presence"/"stance"/"accuracy" trazem point+ci95 com alpha_ordinal,
    kappa, kappa_quadratic, pabak, ac1/gwet_ac1, raw_agreement conforme o
    eixo é nominal ou ordinal; já "distortion" traz confusion/kappa/
    raw_agreement direto, sem point/ci95; "reuse"/"claim_ids" trazem
    jaccard). `primary` também mistura, entre os eixos, chaves escalares
    soltas (n_items, n_coded_both) -- por isso o filtro isinstance(dict)."""
    out = {}
    for pair_name, pair in (pairs or {}).items():
        primary = (pair or {}).get("primary")
        if not isinstance(primary, dict):
            continue
        axis_data = primary.get(axis)
        if isinstance(axis_data, dict):
            out[pair_name] = axis_data
    return out


def _summarize_irr_file(data):
    if data is None:
        return None
    multi = (data.get("multi_coder_alpha") or {}).get("primary") or {}
    # só promove a eixo quem de fato tem um sub-dicionário -- multi_coder_alpha
    # e pairs[*].primary misturam eixos de verdade com chaves escalares soltas
    # (n_items, coders, n_coded_both).
    axes = {k for k, v in multi.items() if isinstance(v, dict)}
    pairs = data.get("pairs") or {}
    for pair in pairs.values():
        primary = (pair or {}).get("primary") or {}
        axes.update(k for k, v in primary.items() if isinstance(v, dict))

    out = {
        "n_items": multi.get("n_items") or data.get("meta", {}).get("n_primary"),
        "seed": data.get("meta", {}).get("seed"),
        "B": data.get("meta", {}).get("B"),
        "eixos": {},
    }
    for axis in sorted(axes):
        alpha_block = multi.get(axis) if isinstance(multi.get(axis), dict) else {}
        out["eixos"][axis] = {
            "alpha": alpha_block.get("alpha"),
            "alpha_metrica": alpha_block.get("metric"),
            "pares": _summarize_irr_axis_pairs(pairs, axis),
        }
    return out


def build_irr(ctx):
    pre = read_optional_json(ctx.root / "data" / "irr" / "irr_stats_pre.json")
    # Pós-adjudicação: um arquivo por codificador, cada um contra o rótulo
    # final (coder_final) -- o desenho de METHOD §17 não produz um arquivo único.
    post_raw = {
        c: read_optional_json(ctx.root / "data" / "irr" / f"irr_stats_post_{c}.json")
        for c in ("c1", "c2", "c3")
    }
    adjud = read_optional_json(ctx.root / "data" / "irr" / "adjudication.json")

    pre_out = (
        _summarize_irr_file(pre)
        if pre is not None
        else PENDENTE("data/irr/irr_stats_pre.json não existe")
    )
    if all(v is None for v in post_raw.values()):
        post_out = PENDENTE("data/irr/irr_stats_post_c{1,2,3}.json não existem")
    else:
        post_out = {
            c: (
                _summarize_irr_file(v)
                if v is not None
                else PENDENTE(f"data/irr/irr_stats_post_{c}.json não existe")
            )
            for c, v in post_raw.items()
        }

    if adjud is not None:
        adjud_out = {
            "n_items": len(adjud.get("items") or {}),
            "n_contested": len(adjud.get("contested") or []),
            "stats": adjud.get("stats"),
        }
    else:
        adjud_out = PENDENTE("data/irr/adjudication.json não existe")

    # Efeito da adjudicação: distribuição de c1 (rótulo original, prov.labels_c1)
    # contra o rótulo final, por eixo -- é o "de 4 para 16" de METHOD §18.
    efeito = {}
    for axis in ("presence", "depth", "stance", "accuracy", "distortion"):
        c1_vals, fin_vals = [], []
        for paper, rec, doi, entry in ctx.classified:
            l1 = (entry.get("prov") or {}).get("labels_c1")
            if not isinstance(l1, dict):
                continue
            c1_vals.append(l1.get(axis))
            fin_vals.append(entry.get(axis))
        if c1_vals:
            efeito[axis] = {
                "c1": _counter_dict(c1_vals),
                "final": _counter_dict(fin_vals),
                "n_itens": len(c1_vals),
            }
    pack = read_optional_json(ctx.root / "data" / "irr" / "pack_blind.json")
    n_pack = None
    if isinstance(pack, dict):
        itens = pack.get("items") or pack.get("itens") or pack
        n_pack = len(itens)
    elif isinstance(pack, list):
        n_pack = len(pack)
    panel = read_optional_json(ctx.root / "data" / "irr" / "panel.json")
    if isinstance(panel, dict) and panel:
        colegiado = {
            "n_itens": len(panel),
            "n_decisoes": sum(1 for v in panel.values() for k in v if k != "rationale"),
            "por_eixo": _counter_dict(
                k for v in panel.values() for k in v if k != "rationale"
            ),
        }
    else:
        colegiado = PENDENTE("data/irr/panel.json ausente")
    return {
        "pre": pre_out,
        "post": post_out,
        "adjudication": adjud_out,
        "colegiado": colegiado,
        "efeito_adjudicacao": efeito or PENDENTE("prov.labels_c1 ausente"),
        "pacote_cego": {"n_itens": n_pack}
        if n_pack
        else PENDENTE("data/irr/pack_blind.json ausente"),
    }


LANDIS_KOCH = {
    "pobre": {"min": None, "max": 0.0},
    "leve": {"min": 0.0, "max": 0.2},
    "razoavel": {"min": 0.2, "max": 0.4},
    "moderada": {"min": 0.4, "max": 0.6},
    "substancial": {"min": 0.6, "max": 0.8},
    "quase_perfeita": {"min": 0.8, "max": 1.0},
}
KRIPPENDORFF_CUTOFFS = {"tentativo": 0.667, "confiavel": 0.800}


def build_constantes(ctx):
    return {
        "B": int_leaf(2000),
        "seed": int_leaf(20260904),
        "janela_cd": [1, 3, 5, 10],
        "janela_passagem_auto_chars": int_leaf(700),
        "landis_koch": LANDIS_KOCH,
        "krippendorff_cutoffs": KRIPPENDORFF_CUTOFFS,
        "scimago_edition": ctx.config.get("scimago", {}).get("edition"),
    }


# ==========================================================================
# numeros.txt -- travessia genérica de dados.json
# ==========================================================================

SECOES_NUMEROS = [
    ("inventario", ["inventario"]),
    ("funil", ["funil"]),
    ("populacao", ["populacao"]),
    ("cobertura", ["cobertura_quartil"]),
    ("quartil", ["quartil"]),
    ("periodicos", ["periodicos"]),
    ("editoras", ["editoras"]),
    ("eixos", ["eixos"]),
    ("papel-quartil", ["papel_quartil"]),
    ("linha-do-tempo", ["linha_do_tempo"]),
    ("alegacoes", ["alegacoes"]),
    ("anomalias", ["anomalias"]),
    ("irr", ["irr"]),
    ("cd", ["cd"]),
    ("cocitacao", ["cocitacao"]),
    ("taxa-base", ["taxa_base"]),
    ("fantasmas", ["fantasmas_auditados"]),
    ("constantes", ["constantes"]),
]

# Chaves cujo conteúdo é lista de referência (Anexo) e não deve virar linha de
# numeros.txt número-a-número (ex.: "ano" de cada uma das ~150 citações
# classificadas -- não é um número que prosa cita, é dado de apêndice).
NUMEROS_IGNORA_CAMINHO = {"inventario_classificados"}


def _is_leaf(obj):
    if not isinstance(obj, dict):
        return False
    ks = set(obj.keys())
    return ks == {"valor", "txt"} or ks == {"valor", "pct", "ratio"}


def format_scalar(x):
    if isinstance(x, bool):
        return None
    if isinstance(x, int):
        return pt_int(x)
    if isinstance(x, float):
        return pt_dec(x, 3)
    return None


def render_leaf(label, obj):
    if "pct" in obj and "ratio" in obj:
        return f"{label}: {obj['pct']} ({obj['ratio']})"
    if "txt" in obj:
        return f"{label}: {obj['txt']}"
    s = format_scalar(obj.get("valor"))
    return f"{label}: {s}" if s is not None else None


def walk_numbers(obj, path):
    """Gera uma linha de texto por folha numérica de `obj`, com `path` como
    rótulo -- é o mecanismo que garante que todo número em dados.json apareça
    em algum lugar de numeros.txt (regra do enunciado)."""
    if isinstance(obj, dict):
        if is_pendente(obj):
            yield f"{' / '.join(path)}: PENDENTE ({obj.get('motivo', '')})"
            return
        if _is_leaf(obj):
            line = render_leaf(" / ".join(path), obj)
            if line:
                yield line
            return
        for k in sorted(obj.keys(), key=str):
            yield from walk_numbers(obj[k], path + [str(k)])
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_numbers(v, path + [str(i)])
    else:
        s = format_scalar(obj)
        if s is not None:
            yield f"{' / '.join(path)}: {s}"


def render_numeros_txt(dados):
    linhas = []
    for chave, dados_paths in SECOES_NUMEROS:
        linhas.append(f"== audit_70 §{chave} ==")
        any_line = False
        for dp in dados_paths:
            valor = dados.get(dp)
            if valor is None:
                continue
            for line in (
                walk_numbers(valor, [dp]) if dp not in NUMEROS_IGNORA_CAMINHO else []
            ):
                linhas.append(line)
                any_line = True
        if not any_line:
            linhas.append("(sem números)")
        linhas.append("")
    return "\n".join(linhas).rstrip("\n") + "\n"


# ==========================================================================
# Verificação de autoconsistência
# ==========================================================================


def verify(ctx, dados):
    """Confere as invariantes do enunciado. `problemas` = falhas duras
    (o script sai com erro); `avisos` = casos esperados/sinalizados (ex.: o
    Scholar de grains reportar menos que o inventário depois de dedup) que só
    são impressos, nunca fazem o script falhar."""
    problemas = []
    avisos = []

    # (1) funil monótono não-crescente a partir do passo 2 (0-based: índice
    # 1 em diante); o passo 0->1 (Scholar -> inventário) pode SUBIR --
    # grains é o caso conhecido (83 > 76) -- e isso é só aviso.
    for paper in PAPERS:
        valores = [
            step["valor"]
            if not isinstance(step["valor"], dict)
            else step["valor"]["valor"]
            for step in dados["funil"][paper]["steps"]
        ]
        if valores[1] > valores[0]:
            avisos.append(
                f"funil[{paper}]: passo 1 (inventário={valores[1]}) > passo 0 (Scholar={valores[0]}) -- "
                f"esperado quando a união de APIs acha mais registro que o Scholar lista; não é falha."
            )
        for i in range(1, len(valores) - 1):
            if valores[i + 1] > valores[i]:
                problemas.append(
                    f"funil[{paper}]: passo {i + 1} ({valores[i + 1]}) > passo {i} ({valores[i]}) -- funil deveria ser não-crescente daqui em diante"
                )

    # (2) sum(quartil counts) == n citantes, por artigo
    for paper in PAPERS:
        soma = sum(dados["quartil"]["todas_citacoes"][paper].values())
        n = len(ctx.citing(paper))
        if soma != n:
            problemas.append(
                f"quartil[{paper}]: soma dos baldes ({soma}) != nº de citantes ({n})"
            )

    # (3) cobertura_quartil: cada linha (Q1..Q4 e total) soma trecho+fantasma+aresta_falsa+pendente == total
    cq = dados["cobertura_quartil"]
    for q in ("Q1", "Q2", "Q3", "Q4", "total"):
        row = cq[q]
        soma = row["trecho"] + row["fantasma"] + row["aresta_falsa"] + row["pendente"]
        if soma != row["total"]:
            problemas.append(
                f"cobertura_quartil[{q}]: trecho+fantasma+aresta_falsa+pendente ({soma}) != total ({row['total']})"
            )
    soma_q = sum(cq[q]["total"] for q in ("Q1", "Q2", "Q3", "Q4"))
    if soma_q != cq["total"]["total"]:
        problemas.append(
            f"cobertura_quartil: soma de Q1..Q4 ({soma_q}) != total ({cq['total']['total']})"
        )

    # (4) eixos: D declarado bate com o universo esperado (all classified / in_text)
    for escopo in (*PAPERS, "pooled"):
        bloco = dados["eixos"][escopo]
        n_all = len(ctx.classified_for(None if escopo == "pooled" else escopo))
        n_txt = sum(
            1
            for (p, r, d, e) in ctx.classified_for(
                None if escopo == "pooled" else escopo
            )
            if e["presence"] == "in_text"
        )
        for axis in ("presence", "relation"):
            for v in bloco[axis].values():
                if v["D"] != n_all:
                    problemas.append(
                        f"eixos[{escopo}][{axis}]: D={v['D']} != nº total classificado ({n_all})"
                    )
                break
        for axis in ("depth", "stance", "accuracy", "highlight"):
            for v in bloco[axis].values():
                if v["D"] != n_txt:
                    problemas.append(
                        f"eixos[{escopo}][{axis}]: D={v['D']} != nº in_text ({n_txt})"
                    )
                break
        # presence: soma dos n bate com D (single-label, exaustivo)
        soma_presence = sum(v["n"] for v in bloco["presence"].values())
        if soma_presence != n_all:
            problemas.append(
                f"eixos[{escopo}][presence]: soma dos n ({soma_presence}) != D ({n_all})"
            )

    # (5) todo claim id referenciado em classify.json existe em claims.json
    ids_validos = {c["id"] for c in ctx.claims}
    for paper, rec, doi, entry in ctx.classified:
        for cid in entry.get("claims") or []:
            if cid not in ids_validos:
                problemas.append(
                    f"classify[{doi}]: referencia claim id {cid!r} que não existe em claims.json"
                )

    # (6) todo id em anomalias resolve a um registro real de master.json
    ids_master = {rec["id"] for paper in PAPERS for rec in ctx.citing(paper)}
    for row in dados["anomalias"]["registro"]:
        if row["id"] not in ids_master:
            problemas.append(
                f"anomalias: id {row['id']!r} não resolve a nenhum registro de master.json"
            )

    return problemas, avisos


# ==========================================================================
# main
# ==========================================================================


def build_dados(ctx, hoje):
    funil, funil_valores = build_funil(ctx)
    dados = {
        "meta": build_meta(ctx, hoje),
        "artigos": build_artigos(ctx),
        "inventario": build_inventario(ctx),
        "funil": funil,
        "populacao": build_populacao(ctx, funil_valores),
        "cobertura_quartil": build_cobertura_quartil(ctx),
        "quartil": build_quartil(ctx),
        "editoras": build_editoras(ctx),
        "periodicos": build_periodicos(ctx),
        "eixos": build_eixos(ctx),
        "papel_quartil": build_papel_quartil(ctx),
        "linha_do_tempo": build_linha_do_tempo(ctx),
        "alegacoes": build_alegacoes(ctx),
        "anomalias": build_anomalias(ctx),
        "irr": build_irr(ctx),
        "cd": build_cd(ctx),
        "cocitacao": build_cocitacao(ctx),
        "taxa_base": build_taxa_base(ctx),
        "fantasmas_auditados": build_fantasmas_auditados(ctx),
        "constantes": build_constantes(ctx),
        "inventario_classificados": build_inventario_classificados(ctx),
    }
    return dados


def parse_args(argv):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--root",
        type=Path,
        default=SCRIPT_ROOT,
        help="raiz onde ler config.json/data/ (padrão: inferida de __file__)",
    )
    ap.add_argument(
        "--classify",
        type=Path,
        default=None,
        help="usa este arquivo no lugar de <root>/data/classify.json",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="renderiza em memória e compara byte a byte com os arquivos commitados; nunca grava; sai 1 se houver diferença",
    )
    ap.add_argument(
        "--date",
        default=None,
        help="data gravada em meta.gerado_em (padrão: hoje, AAAA-MM-DD); use para saída determinística em teste",
    )
    return ap.parse_args(argv)


def main(argv=None):
    import datetime

    args = parse_args(argv)
    root = args.root.resolve()
    hoje = args.date or datetime.date.today().isoformat()

    ctx = Ctx(root, args.classify.resolve() if args.classify else None)
    dados = build_dados(ctx, hoje)

    problemas, avisos = verify(ctx, dados)

    dados_json = json.dumps(dados, **_JSON_KW) + "\n"
    numeros_txt = render_numeros_txt(dados)

    print(f"-- audit_70_numbers: raiz de dados = {root}")
    if args.classify:
        print(f"-- classify override = {args.classify.resolve()}")
    print(
        f"-- {len(ctx.citing())} citantes | {len(ctx.classified)} classificados | usou_projecao_v1={ctx.used_v1_projection}"
    )
    for a in avisos:
        print(f"AVISO: {a}")
    for p in problemas:
        print(f"PROBLEMA: {p}")

    if args.check:
        atual_dados = (
            OUT_DADOS.read_text(encoding="utf-8") if OUT_DADOS.exists() else None
        )
        atual_numeros = (
            OUT_NUMEROS.read_text(encoding="utf-8") if OUT_NUMEROS.exists() else None
        )
        drift = []
        if atual_dados != dados_json:
            drift.append(
                f"dados.json: {len(dados_json.encode('utf-8'))} bytes gerados vs "
                f"{len(atual_dados.encode('utf-8')) if atual_dados is not None else 0} commitados"
            )
        if atual_numeros != numeros_txt:
            drift.append(
                f"numeros.txt: {len(numeros_txt.encode('utf-8'))} bytes gerados vs "
                f"{len(atual_numeros.encode('utf-8')) if atual_numeros is not None else 0} commitados"
            )
        if drift or problemas:
            for d in drift:
                print(f"DRIFT: {d}")
            return 1
        print(
            f"ok --check: dados.json e numeros.txt idênticos ao gerado ({len(dados_json)} + {len(numeros_txt)} chars)"
        )
        return 0

    if problemas:
        print(
            f"-- {len(problemas)} problema(s) de autoconsistência; NÃO gravando arquivos de saída."
        )
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Escrita atômica: quem lê dados.json (figuras, HTML) nunca vê arquivo pela metade.
    for out, txt in ((OUT_DADOS, dados_json), (OUT_NUMEROS, numeros_txt)):
        tmp = out.with_suffix(out.suffix + ".tmp")
        tmp.write_text(txt, encoding="utf-8")
        os.replace(tmp, out)
    print(
        f"ok: {OUT_DADOS} ({len(dados_json)} chars) | {OUT_NUMEROS} ({len(numeros_txt)} chars)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
