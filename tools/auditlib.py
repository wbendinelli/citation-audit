"""Biblioteca compartilhada dos scripts de auditoria de citações.

Reúne caminhos, carregadores/gravadores de `data/*.json`, helpers de rede e
texto, e as constantes de taxonomia usadas por todo `tools/`. Nenhuma
dependência fora da stdlib.
"""
import hashlib
import json
import re
import subprocess
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TEXT = ROOT / "text"
PDF = ROOT / "pdf"
REPORTS = ROOT / "report"

_JSON_KW = dict(ensure_ascii=False, indent=1, sort_keys=True)


def _dump(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, **_JSON_KW)
        f.write("\n")


def load_config():
    with open(ROOT / "config.json", encoding="utf-8") as f:
        return json.load(f)


# ---------------- data/master.json ----------------

def load_master():
    """Carrega data/master.json.

    Aceita tanto o esquema v1 em disco (dict plano `{"airline": {...},
    "grains": {...}}`) quanto o v2 (`{"meta": {...}, "papers": {...}}`), e
    sempre devolve a forma v2 em memória. A migração definitiva do arquivo
    em disco é feita uma única vez por `tools/_migrar_v2.py`; este loader
    só evita que cada script precise saber qual dos dois formatos está
    gravado. `load_classify`/`load_journals` seguem o mesmo padrão, com
    "entries"/"sources" no lugar de "papers".
    """
    return _load_versioned("master.json", "papers")


def save_master(master):
    """Grava data/master.json preservando o esquema com que foi carregado:
    schema 1 continua plano no disco, schema >= 2 grava com o envelope
    `meta`. Só `tools/_migrar_v2.py` deve elevar `meta.schema` para 2.
    """
    _save_versioned("master.json", master, "papers")


def iter_records(master):
    """Itera `(paper_key, registro)` sobre todos os citantes de
    `master["papers"]`."""
    for key, block in master["papers"].items():
        for rec in block["citing"]:
            yield key, rec


# ---------------- data/classify.json ----------------

def load_classify():
    return _load_versioned("classify.json", "entries")


def save_classify(classify):
    _save_versioned("classify.json", classify, "entries")


def classify_entries(classify):
    """`classify["entries"]` — o dict `doi minúsculo -> classificação`.
    Serve tanto `load_classify()` quanto `load_classify_orfas()` — as duas
    guardam o mesmo formato de entrada."""
    return classify["entries"]


def load_classify_orfas():
    """data/classify_orfas.json: classificações órfãs, cujo DOI foi
    absorvido por deduplicação e não resolve mais a nenhum registro de
    master.json. Mesmo formato de load_classify(); use classify_entries()
    para pegar o dict."""
    return _load_versioned("classify_orfas.json", "entries")


def load_decisoes_scimago():
    """data/decisoes_scimago.json: vereditos manuais (dict `id -> {veredito,
    razao}`) para os registros com DOI cujo periódico não tem quartil
    Scimago. Sem envelope meta -- é um dict plano por design."""
    with open(DATA / "decisoes_scimago.json", encoding="utf-8") as f:
        return json.load(f)


# ---------------- data/journals.json ----------------

def load_journals():
    return _load_versioned("journals.json", "sources")


def save_journals(journals):
    _save_versioned("journals.json", journals, "sources")


def journal_sources(journals):
    """`journals["sources"]` — o dict `source_id (OpenAlex) -> periódico`."""
    return journals["sources"]


def quartil_scimago(rec, sources):
    """Quartil oficial do Scimago do periódico de `rec` (via `source_id`),
    ou None se não há quartil real (Q1..Q4) atribuído — seja por o
    periódico não casar com o Scimago, seja por casar com quartil em
    branco ("-"). Usado por audit_50_pending e check_data para que as
    duas nunca possam divergir sobre o que conta como "sem quartil"."""
    m = sources.get(rec.get("source_id") or "")
    if not m:
        return None
    sc = m.get("scimago")
    if not sc:
        return None
    q = sc.get("quartil")
    return q if q in ("Q1", "Q2", "Q3", "Q4") else None


# Regra de tier de periódico (audit_41_scimago). Vive aqui, não em
# audit_41_scimago.py, para que check_data possa validar journals.json
# contra a MESMA função em vez de reimplementar a regra por conta própria.
TIER_CORTES = [(6.0, "T1"), (3.5, "T2"), (2.0, "T3"), (0.0, "T4")]


def tier_proxy_de(citedness):
    if citedness is None:
        return None
    for lim, t in TIER_CORTES:
        if citedness >= lim:
            return t
    return "T4"


def tier_e_base(tier_proxy, scimago):
    """tier/tier_base de um periódico: casou ISSN com o Scimago -> quartil
    oficial prevalece (mesmo quando o Scimago não atribui quartil, valor
    "-"); senão, o proxy de citedness do OpenAlex, marcado como tal."""
    if scimago is not None:
        return scimago.get("quartil"), "Scimago SJR Best Quartile"
    return tier_proxy, "proxy OpenAlex (sem correspondência no Scimago)"


def tier_erros(sources):
    """Confere `tier_proxy`/`tier`/`tier_base` de cada periódico contra a
    regra acima; devolve a lista de mensagens de erro (vazia se ok).
    Usado por `audit_41_scimago.py --check` e por `check_data.py`."""
    erros = []
    for sid, m in sources.items():
        tp = tier_proxy_de(m.get("citedness_2a"))
        tier, base = tier_e_base(tp, m.get("scimago"))
        if m.get("tier_proxy") != tp:
            erros.append(f"{sid} ({m.get('nome')}): tier_proxy={m.get('tier_proxy')!r}, esperado {tp!r}")
        if m.get("tier") != tier:
            erros.append(f"{sid} ({m.get('nome')}): tier={m.get('tier')!r}, esperado {tier!r}")
        if m.get("tier_base") != base:
            erros.append(f"{sid} ({m.get('nome')}): tier_base={m.get('tier_base')!r}, esperado {base!r}")
    return erros


# ---------------- v1/v2 genérico ----------------

def _load_versioned(filename, key):
    """Carrega `data/<filename>`. Aceita o v1 plano (o próprio dict de
    dados, sem envelope) e o v2 (`{"meta": {...}, <key>: {...}}`); sempre
    devolve a forma v2 em memória — ver `load_master` para o porquê."""
    with open(DATA / filename, encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict) and "meta" in raw and key in raw:
        return raw
    return {"meta": {"schema": 1}, key: raw}


def _save_versioned(filename, obj, key):
    """Grava `data/<filename>` preservando o esquema com que foi
    carregado — ver `save_master`."""
    meta = obj.get("meta") or {"schema": 1}
    out = {"meta": meta, key: obj[key]} if meta.get("schema", 1) >= 2 else obj[key]
    _dump(out, DATA / filename)


# ---------------- rede ----------------

def jget(url, tries=5, timeout=90, headers=None):
    """GET JSON com retry e backoff exponencial (máx. 25s). HTTP 404 é
    tratado como resposta definitiva — devolve None sem tentar de novo."""
    cfg = load_config()
    mail = cfg.get("mailto") or cfg.get("contact_email", "")
    h = {"Accept": "application/json", "User-Agent": f"citation-audit/1.0 (mailto:{mail})"}
    if headers:
        h.update(headers)
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(min(25, 2 ** attempt))
        except Exception:
            time.sleep(min(25, 2 ** attempt))
    return None


# ---------------- texto ----------------

def norm_doi(d):
    if not d:
        return None
    d = d.strip().lower()
    d = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", d)
    d = re.sub(r"^doi:", "", d)
    return d or None


def norm_title(t):
    """NFKD + minúsculas + só alfanumérico/espaço. Usado para casar títulos
    entre fontes (Scholar trunca, Crossref/OpenAlex variam pontuação e
    acentuação)."""
    t = unicodedata.normalize("NFKD", t or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", t)).strip()


def strip_html(b):
    s = b.decode("utf-8", "ignore")
    s = re.sub(r"(?is)<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    for a, c in [("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&#39;", "'")]:
        s = s.replace(a, c)
    return re.sub(r"[ \t]+", " ", s)


def pdftext(path, min_len=2500):
    """Roda `pdftotext` sobre um PDF já salvo em disco. Devolve None se o
    texto extraído for curto demais para ser corpo de artigo (heurística:
    é só página de rosto/abstract, não o texto completo)."""
    try:
        o = subprocess.run(["pdftotext", "-q", "-enc", "UTF-8", str(path), "-"],
                            capture_output=True, timeout=150)
        t = o.stdout.decode("utf-8", "ignore")
        return t if len(t) > min_len else None
    except Exception:
        return None


def doi_prefix(doi):
    return (doi or "").split("/", 1)[0]


def evidence_sha256_16(passages):
    """Hash gravado em classify.json `prov.evidence_sha256_16`: os 16
    primeiros hex do SHA-256 das passagens unidas por `\\n`."""
    return hashlib.sha256("\n".join(passages).encode("utf-8")).hexdigest()[:16]


# ---------------- taxonomia ----------------

# Vocabulário fechado por eixo de classify.json (role/stance/reuse/flag),
# copiado dos valores efetivamente em uso. `flag` nunca inclui a ausência de
# flag: no esquema v1 isso era "", no v2 é `null` — os dois ficam fora desta
# lista de propósito, e são tratados como "sem flag" por quem valida.
TAXONOMIA = {
    "role": ["bibliography_only", "brief_mention", "drive_by", "real_mention",
             "supporting", "foundational", "wrongly_interpreted"],
    "stance": ["none", "supporting", "contradictory"],
    "reuse": ["method_adoption", "result_validated", "work_extended"],
    "flag": ["ghost", "critical", "weak", "good", "misattribution", "duplicate",
             "best", "coautor", "autocitacao"],
}

# Vocabulário fechado de master[*].citing[*].status.
STATUS = (
    "fechado", "oa_baixavel", "oa_sem_pdf_direto", "oa_bloqueado", "oa_antibot",
    "tem_texto", "texto_parcial", "texto_incorreto", "evidencia_insuficiente",
    "aresta_falsa", "sem_doi", "so_scholar", "so_scholar_sem_doi",
)
