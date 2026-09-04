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
    gravado.
    """
    with open(DATA / "master.json", encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict) and "meta" in raw and "papers" in raw:
        return raw
    return {"meta": {"schema": 1}, "papers": raw}


def save_master(master):
    """Grava data/master.json preservando o esquema com que foi carregado:
    schema 1 continua plano no disco, schema >= 2 grava com o envelope
    `meta`. Só `tools/_migrar_v2.py` deve elevar `meta.schema` para 2.
    """
    meta = master.get("meta") or {"schema": 1}
    obj = {"meta": meta, "papers": master["papers"]} if meta.get("schema", 1) >= 2 \
        else master["papers"]
    _dump(obj, DATA / "master.json")


def iter_records(master):
    """Itera `(paper_key, registro)` sobre todos os citantes de
    `master["papers"]`."""
    for key, block in master["papers"].items():
        for rec in block["citing"]:
            yield key, rec


# ---------------- data/classify.json ----------------

def load_classify():
    with open(DATA / "classify.json", encoding="utf-8") as f:
        return json.load(f)


def save_classify(classify):
    _dump(classify, DATA / "classify.json")


# ---------------- data/journals.json ----------------

def load_journals():
    with open(DATA / "journals.json", encoding="utf-8") as f:
        return json.load(f)


def save_journals(journals):
    _dump(journals, DATA / "journals.json")


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
