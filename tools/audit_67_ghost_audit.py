#!/usr/bin/env python3
"""Etapa 67 (stage_e): decompõe as citações "só na bibliografia" (`presence ==
reference_list_only`, esperado 13) em quatro categorias:

  - genuine             corpo comprovado no disco, sem menção no texto
  - extraction_failure  há marcador em-texto e o pipeline perdeu -> reclassificar
  - body_unavailable    sem corpo no disco; o veredito depende só da leitura
                         documentada do codificador (via SSO/PDF externo)
  - false_edge          o citante nem sequer lista o artigo na bibliografia

Lê `data/master.json`, `data/classify.json` (ou o override `--classify`) e
`text/*.txt` do repositório `citation-audit`; nunca escreve lá. Saída em
`<pasta deste script>/../data/ghost_audit.json` (ver `--root` vs. auto-raiz
abaixo).

Raiz dos dados de ENTRADA (`--root`) vs. raiz de SAÍDA (auto-detectada por
`__file__`): propositalmente independentes. Hoje este script mora em
`stage_e/tools/`, então a auto-raiz é `stage_e/` (onde `data/ghost_audit.json`
deve cair, por instrução da tarefa) enquanto `--root` aponta para o
repositório real `citation-audit` (onde os insumos vivem). Quando o dono do
repositório mover este arquivo para `citation-audit/tools/`, `--root` deixa
de ser necessário: as duas raízes coincidem automaticamente, porque ambas são
derivadas de `Path(__file__).resolve().parents[1]`.
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

# ----------------------------------------------------------------------
# Raízes: auto-raiz (onde a SAÍDA deste script cai) vs. --root (onde os
# INSUMOS do repositório citation-audit são lidos). Ver docstring acima.
# ----------------------------------------------------------------------
SELF_ROOT = Path(__file__).resolve().parents[1]
OUT_DATA = SELF_ROOT / "data"
CACHE_DIR = OUT_DATA / "cache" / "openalex"

# Fallback documentado de --classify: data/classify.json do repositório real
# ainda está no esquema v1 (role/flag) enquanto outro agente o migra para v2
# nesta mesma sessão. O stage_c é uma pasta IRMà de stage_e (mesmo
# diretório de stage), então referenciamos por caminho relativo ao invés de um
# absoluto fixo — sobrevive a uma mudança de sessão, desde que a estrutura
# stage_c/stage_e do diretório de stage se mantenha.
STAGE_C_CLASSIFY_FALLBACK = SELF_ROOT.parent / "stage_c" / "data" / "classify.json"

_JSON_KW = {"ensure_ascii": False, "indent": 1, "sort_keys": True}


def dump_json(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, **_JSON_KW)
        f.write("\n")


# ---------------------------------------------------------------------
# Carregamento de classify.json com deteção v1/v2 e fallback para stage_c
# ---------------------------------------------------------------------


def load_classify_v2(explicit_path, root):
    """Devolve (entries_dict, meta_de_carregamento). `entries_dict` é sempre
    o dicionário `doi_minusculo -> classificação` no esquema v2 (eixos
    `presence/depth/stance/accuracy/...`). Se o caminho usado (default ou
    explícito) resolver para um arquivo ainda em v1 (`role`/`flag`), cai
    para STAGE_C_CLASSIFY_FALLBACK — mas só quando o caminho não foi
    escolhido explicitamente por quem chamou o script (`--classify`
    explícito é respeitado como está, mesmo se v1: é escolha de quem
    chamou)."""
    was_explicit = explicit_path is not None
    path = (
        Path(explicit_path).resolve()
        if explicit_path
        else (root / "data" / "classify.json")
    )

    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    entries = (
        raw["entries"]
        if (isinstance(raw, dict) and "meta" in raw and "entries" in raw)
        else raw
    )

    is_v2 = any(("presence" in v) for v in entries.values())
    fallback_used = False
    warn = None
    if not is_v2 and not was_explicit:
        fallback_used = True
        warn = (
            f"AVISO: {path} ainda está no esquema v1 (role/flag); "
            f"usando fallback documentado {STAGE_C_CLASSIFY_FALLBACK}"
        )
        print(warn)
        with open(STAGE_C_CLASSIFY_FALLBACK, encoding="utf-8") as f:
            raw = json.load(f)
        entries = (
            raw["entries"]
            if (isinstance(raw, dict) and "meta" in raw and "entries" in raw)
            else raw
        )
        path = STAGE_C_CLASSIFY_FALLBACK
        is_v2 = any(("presence" in v) for v in entries.values())
        if not is_v2:
            raise SystemExit(
                f"ERRO: fallback {path} também não está em v2 (presence/depth/...)."
            )
    elif not is_v2 and was_explicit:
        raise SystemExit(
            f"ERRO: --classify {path} está em v1 (role/flag), e foi passado explicitamente "
            f"— não aplico fallback automático sobre uma escolha explícita. "
            f"Rode sem --classify para usar o fallback documentado, ou aponte para um arquivo v2."
        )

    return entries, {"path": str(path), "fallback_used": fallback_used, "warning": warn}


# ---------------------------------------------------------------------
# Fronteira corpo / lista de referências
# ---------------------------------------------------------------------
# Regra pedida: heading estrito (references|bibliography|referências sozinho
# na linha) ou, na ausência, os últimos 40% do texto. Na prática, o texto
# extraído de HTML de publisher (a maioria destes 13 arquivos) cola o heading
# e a primeira entrada na MESMA linha de texto ("References Abbey JA...");
# a regra estrita quase nunca casa, e o fallback cru de 40% acaba cortando
# a fronteira DEPOIS do trecho "Bendinelli, ..." na bibliografia real (raiz
# no meio de rodapé/menu, não no corpo) -- verificado manualmente nos 13
# arquivos antes de escrever este script. Por isso o fallback aqui tem um
# degrau intermediário, documentado e antes do corte de 40%: procura a
# primeira ocorrência (não a última — a última costuma ser um link de rodapé
# tipo "Download references") de um heading solto (plural/singular,
# multi-idioma), pulando um "guarda" inicial pequeno para não casar item de
# menu de navegação no topo da página. Ver seção "decisões" no relatório
# final do agente que escreveu este script.
STRICT_REFS_RE = re.compile(r"(?im)^[ \t]*(references|bibliography|referências)[ \t]*$")
LOOSE_REFS_RE = re.compile(
    r"(?i)\b(references?|bibliography|referências|literature cited|works cited|"
    r"список\s+литературы)\b"
)
HEADING_RE = re.compile(
    r"(?i)\b(introduction|introdu[cç][aã]o|m[eé]todo|methodology)\b"
)


def find_refs_start(t):
    m = STRICT_REFS_RE.search(t)
    if m:
        return m.start(), "strict"
    guard = max(300, int(len(t) * 0.02))
    for m in LOOSE_REFS_RE.finditer(t):
        if m.start() >= guard:
            return m.start(), "loose-first"
    return int(len(t) * 0.6), "fallback60"


def body_is_real(t, refs_start):
    """>= 8000 caracteres antes das referências E heading de
    Introdução/Método -- limiar pedido pela tarefa (não é o critério de
    `eh_pagina_de_rosto` de audit_32_gate_bibonly.py, que conta menções a
    Google Scholar/CrossRef/PubMed; aqui a régua é a especificada nesta
    tarefa, aplicada sobre a fronteira corpo/referências acima)."""
    if refs_start < 8000:
        return False
    return bool(HEADING_RE.search(t[:refs_start]))


# ---------------------------------------------------------------------
# Busca no corpo: sobrenome, "et al." + ano, marcador numérico, DOI, legendas
# ---------------------------------------------------------------------


def window200(t, start, end):
    lo = max(0, start - 100)
    hi = min(len(t), end + 100)
    return t[lo:hi].replace("\n", " ").strip()


def find_surname_hits(body, surname):
    hits = []
    for m in re.finditer(re.escape(surname), body, re.IGNORECASE):
        hits.append(
            {
                "pattern": "surname",
                "position": m.start(),
                "window": window200(body, m.start(), m.end()),
            }
        )
    return hits


def find_etal_year_hits(body, years):
    """ "et al." a até 40 caracteres do ano focal (janela nos dois
    sentidos, já que "dentro de 40 caracteres" não define direção)."""
    year_pat = "|".join(re.escape(y) for y in years)
    hits = []
    for m in re.finditer(r"et\s+al\.?", body, re.IGNORECASE):
        lo, hi = max(0, m.start() - 40), min(len(body), m.end() + 40)
        if re.search(year_pat, body[lo:hi]):
            hits.append(
                {
                    "pattern": "et_al_year",
                    "position": m.start(),
                    "window": window200(body, m.start(), m.end()),
                }
            )
    return hits


def find_doi_hits(body, doi):
    hits = []
    for variant in (doi, f"doi.org/{doi}", f"https://doi.org/{doi}"):
        for m in re.finditer(re.escape(variant), body, re.IGNORECASE):
            hits.append(
                {
                    "pattern": "doi",
                    "position": m.start(),
                    "window": window200(body, m.start(), m.end()),
                }
            )
    return hits


def find_caption_hits(body, surname):
    """Legendas de figura/tabela que mencionam o sobrenome. A busca de
    sobrenome acima já cobre o corpo inteiro (legendas incluídas, já que o
    texto extraído não separa estrutura); isto aqui é uma marcação
    ESPECÍFICA e rastreável de "achei perto de uma legenda", pedida à
    parte pela tarefa, não um canal de busca novo."""
    hits = []
    for m in re.finditer(r"(?im)^\s*(figure|fig\.|table|quadro|tabela)\s*\d+", body):
        lo, hi = m.start(), min(len(body), m.end() + 300)
        seg = body[lo:hi]
        sm = re.search(re.escape(surname), seg, re.IGNORECASE)
        if sm:
            pos = lo + sm.start()
            hits.append(
                {
                    "pattern": "caption",
                    "position": pos,
                    "window": window200(body, pos, pos + len(surname)),
                }
            )
    return hits


CITE_NUM_BRACKET_RE_TMPL = r"\[[^\]]*\b{n}\b[^\]]*\]"


def extract_ref_marker_number(refs_text, surname, bend_pos_in_refs):
    """Número do marcador ([n], n. etc.) que abre a entrada de bibliografia
    que contém o sobrenome, procurado nos ~400 caracteres antes da
    ocorrência (dentro da própria seção de referências). Em bibliografia
    estilo autor-data (a maioria destes 13 arquivos) não há marcador
    algum -- devolve None, e o canal numérico fica mudo (correto)."""
    window_start = max(0, bend_pos_in_refs - 400)
    chunk = refs_text[window_start:bend_pos_in_refs]
    m_list = list(re.finditer(r"\[(\d{1,4})\]", chunk))
    if m_list:
        return m_list[-1].group(1), "bracket"
    m_list = list(re.finditer(r"(?:^|\n)\s*(\d{1,4})[.)]\s", chunk))
    if m_list:
        return m_list[-1].group(1), "dot_or_paren"
    return None, None


def find_numeric_marker_hits(body, n):
    if n is None:
        return [], []
    bracket_hits, super_hits = [], []
    bracket_pat = re.compile(CITE_NUM_BRACKET_RE_TMPL.format(n=re.escape(n)))
    for m in bracket_pat.finditer(body):
        bracket_hits.append(
            {
                "pattern": "numeric_marker_bracket",
                "position": m.start(),
                "window": window200(body, m.start(), m.end()),
            }
        )
    # estilo sobrescrito: número colado a letra/pontuação, sem espaço antes,
    # não emendado a outro dígito (evita casar dentro de um ano ou de um
    # número maior). Peso baixo por desenho -- ver decisão no relatório.
    super_pat = re.compile(r"(?<![\d.])" + re.escape(n) + r"(?!\d)(?=[.,;:)\s]|$)")
    for m in super_pat.finditer(body):
        before = body[max(0, m.start() - 1) : m.start()]
        if before and (before.isalpha() or before in ").,;"):
            super_hits.append(
                {
                    "pattern": "numeric_marker_super",
                    "position": m.start(),
                    "window": window200(body, m.start(), m.end()),
                }
            )
    return bracket_hits, super_hits


TITLE_FIRST6_RE_CACHE = {}


def title_first6_pattern(title):
    if title not in TITLE_FIRST6_RE_CACHE:
        words = re.findall(r"[A-Za-zÀ-ÿ0-9]+", title)[:6]
        pat = r"\s+".join(re.escape(w) for w in words)
        TITLE_FIRST6_RE_CACHE[title] = re.compile(pat, re.IGNORECASE)
    return TITLE_FIRST6_RE_CACHE[title]


# ---------------------------------------------------------------------
# OpenAlex: verificação opcional da aresta via referenced_works, com cache
# ---------------------------------------------------------------------


def oa_id_bare(url_or_id):
    if not url_or_id:
        return None
    return url_or_id.rsplit("/", 1)[-1]


def oa_fetch_cached(cache_key, url, mailto, tries=3, timeout=20):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        with open(cache_file, encoding="utf-8") as f:
            return json.load(f)
    result = {"ok": False, "error": "não tentado"}
    headers = {
        "Accept": "application/json",
        "User-Agent": f"citation-audit-stage-e/1.0 (mailto:{mailto})",
    }
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                result = {"ok": True, "data": json.load(r)}
            break
        except urllib.error.HTTPError as e:
            result = {"ok": False, "error": f"HTTP {e.code}"}
            if e.code == 404:
                break
            time.sleep(min(5, 2**attempt))
        except Exception as e:
            result = {"ok": False, "error": str(e)}
            time.sleep(min(5, 2**attempt))
    # cacheia sucesso E falha -- é o que garante reprodutibilidade byte-a-
    # -byte numa segunda rodada, independente do estado da rede.
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    return result


def resolve_focal_openalex_id(paper_key, doi, mailto):
    result = oa_fetch_cached(
        f"focal_{paper_key}",
        f"https://api.openalex.org/works/doi:{doi}?select=id&mailto={mailto}",
        mailto,
    )
    if result.get("ok"):
        return oa_id_bare(result["data"].get("id"))
    return None


def openalex_edge_check(citing_openalex_url, focal_id_bare, mailto):
    if not citing_openalex_url or not focal_id_bare:
        return {
            "attempted": False,
            "confirmed": None,
            "detail": "sem openalex id do citante ou do foco",
        }
    citing_id = oa_id_bare(citing_openalex_url)
    result = oa_fetch_cached(
        citing_id,
        f"https://api.openalex.org/works/{citing_id}?select=id,referenced_works&mailto={mailto}",
        mailto,
    )
    if not result.get("ok"):
        return {
            "attempted": True,
            "confirmed": None,
            "detail": f"indisponível: {result.get('error')}",
        }
    refs = result["data"].get("referenced_works", []) or []
    refs_bare = {oa_id_bare(u) for u in refs}
    hit = focal_id_bare in refs_bare
    return {
        "attempted": True,
        "confirmed": hit,
        "detail": f"{len(refs)} referenced_works; foco {'presente' if hit else 'ausente'}",
    }


# ---------------------------------------------------------------------
# População do estudo (METHOD.md §9): DOI + editora estabelecida + artigo
# de periódico (sem capítulo/anais/preprint). Espelha _livro()/funil() de
# tools/audit_80_report_html.py -- é a MESMA função que produziu o "87" (49
# aviação + 38 grãos) documentado em METHOD.md §9 e no CHANGELOG. A tarefa
# descreveu esta população como "exclude book/chapter/preprint by work_type
# and DOI suffix 978…"; a implementação real do repositório filtra só pelo
# sufixo do DOI (sem olhar work_type) -- reproduzido aqui por igual, com a
# checagem feita e registrada no relatório final (bate exatamente 49+38=87).
def is_book_doi(doi):
    suf = doi.split("/", 1)[1] if "/" in doi else ""
    return (
        suf.startswith("978")
        or "9781" in suf
        or "9780" in suf
        or doi.startswith("10.1007/978")
    )


def in_population_87(rec, editoras_estabelecidas):
    doi = rec.get("doi")
    if not doi:
        return False
    prefix = doi.split("/", 1)[0]
    if prefix not in editoras_estabelecidas:
        return False
    return not is_book_doi(doi)


# ---------------------------------------------------------------------
# Wilson score interval (95%)
# ---------------------------------------------------------------------


def wilson_ci(k, n, z=1.959963984540054):
    if n == 0:
        return (0.0, 0.0)
    k = np.asarray(k, dtype=float)
    n = np.asarray(n, dtype=float)
    phat = k / n
    denom = 1.0 + z * z / n
    center = phat + z * z / (2 * n)
    margin = z * np.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))
    lo = (center - margin) / denom
    hi = (center + margin) / denom
    # arredonda a 6 casas -- sem isso, k=0 ou k=n produzem ruído de ponto
    # flutuante tipo 3.58e-17 em vez de 0.0 (a fórmula é exata nesses
    # extremos; só o sqrt/subtração não é). 6 casas preserva toda a
    # precisão que importa para uma taxa sobre no máximo 104 observações.
    lo = round(float(max(0.0, lo)), 6)
    hi = round(float(min(1.0, hi)), 6)
    if lo < 1e-9:
        lo = 0.0
    if hi > 1 - 1e-9:
        hi = 1.0
    return (lo, hi)


def rate_block(k, n):
    lo, hi = wilson_ci(k, n)
    rate = round(k / n, 6) if n else None
    return {
        "numerator": int(k),
        "denominator": int(n),
        "rate": rate,
        "ci95_wilson": [lo, hi],
    }


# =======================================================================
# main
# =======================================================================


def main():
    ap = argparse.ArgumentParser(
        description="Decompõe as citações reference_list_only em genuine/extraction_failure/body_unavailable/false_edge."
    )
    ap.add_argument(
        "--root",
        type=str,
        default=None,
        help="raiz do repositório citation-audit (default: inferida de __file__, "
        "ou seja, esta mesma pasta -- passe explicitamente enquanto o script "
        "mora fora do repositório)",
    )
    ap.add_argument(
        "--classify",
        type=str,
        default=None,
        help="caminho para classify.json (default: <root>/data/classify.json, com "
        "fallback documentado para stage_c se ainda v1)",
    )
    args = ap.parse_args()

    root = Path(args.root).resolve() if args.root else SELF_ROOT
    sys.path.insert(0, str(root / "tools"))
    import auditlib

    cfg = auditlib.load_config()
    mailto = cfg.get("mailto", "")
    master = auditlib.load_master()
    journals = auditlib.load_journals()
    sources = auditlib.journal_sources(journals)
    editoras_estabelecidas = cfg["editoras_estabelecidas"]

    entries, classify_meta = load_classify_v2(args.classify, root)

    # mapa doi_minusculo -> [(paper_key, record), ...]
    recs_by_doi = {}
    for key, block in master["papers"].items():
        for r in block["citing"]:
            d = (r.get("doi") or "").lower()
            if d:
                recs_by_doi.setdefault(d, []).append((key, r))

    ghost_dois = sorted(
        doi for doi, e in entries.items() if e.get("presence") == "reference_list_only"
    )

    # -------------------- os dois falsos-edge fora de classify --------------------
    false_edges_outside_classify = []
    for key, block in master["papers"].items():
        for r in block["citing"]:
            if (
                r.get("status") == "aresta_falsa"
                and (r.get("doi") or "").lower() not in entries
            ):
                false_edges_outside_classify.append(
                    {
                        "id": r["id"],
                        "paper": key,
                        "doi": r.get("doi"),
                        "venue": r.get("venue"),
                        "nota_integridade": r.get("nota_integridade"),
                    }
                )
    false_edges_outside_classify.sort(key=lambda x: x["id"])

    # -------------------- decompõe cada uma das (esperado 13) --------------------
    out_entries = {}
    focal_oa_id = {}
    for paper_key in ("airline", "grains"):
        focal_doi = cfg["papers"][paper_key]["doi"]
        focal_oa_id[paper_key] = resolve_focal_openalex_id(paper_key, focal_doi, mailto)

    for doi in ghost_dois:
        matches = recs_by_doi.get(doi, [])
        if len(matches) != 1:
            print(
                f"AVISO: doi {doi} resolve a {len(matches)} registros em master.json (esperado 1)"
            )
        if not matches:
            continue
        paper_key, rec = matches[0]
        classify_entry = entries[doi]
        focal_doi = cfg["papers"][paper_key]["doi"]
        focal_title = cfg["papers"][paper_key]["title"]
        surname = cfg["author_surname"]

        text_path = rec.get("text_path")
        text_exists = bool(text_path and (root / text_path).exists())
        t = None
        refs_start, refs_method = None, "no_text"
        has_head, real_body = False, False
        hits = []
        marker_n, marker_kind = None, None
        bracket_hits, super_hits = [], []

        if text_exists:
            t = (root / text_path).read_text(encoding="utf-8", errors="ignore")
            refs_start, refs_method = find_refs_start(t)
            has_head = bool(HEADING_RE.search(t[:refs_start]))
            real_body = body_is_real(t, refs_start)

            body_txt = t[:refs_start]
            refs_txt = t[refs_start:]

            hits += find_surname_hits(body_txt, surname)
            hits += find_etal_year_hits(
                body_txt,
                [str(cfg["papers"][paper_key]["year"]), "2016", "2019", "2020"],
            )
            hits += find_doi_hits(body_txt, focal_doi)
            hits += find_caption_hits(body_txt, surname)
            tfp = title_first6_pattern(focal_title)
            for m in tfp.finditer(body_txt):
                hits.append(
                    {
                        "pattern": "title6",
                        "position": m.start(),
                        "window": window200(body_txt, m.start(), m.end()),
                    }
                )

            # marcador numérico: localiza a entrada de bibliografia com o
            # sobrenome DENTRO da seção de referências e tenta extrair o [n]
            surname_in_refs = list(
                re.finditer(re.escape(surname), refs_txt, re.IGNORECASE)
            )
            if surname_in_refs:
                bend_pos = surname_in_refs[0].start()
                marker_n, marker_kind = extract_ref_marker_number(
                    refs_txt, surname, bend_pos
                )
                bracket_hits, super_hits = find_numeric_marker_hits(body_txt, marker_n)
                hits += bracket_hits + super_hits

        hits.sort(key=lambda h: h["position"])

        # -------------------- edge_confirmed --------------------
        strong_local_edge = text_exists and bool(
            re.search(re.escape(surname), t, re.IGNORECASE)
            or re.search(re.escape(focal_doi), t, re.IGNORECASE)
            or title_first6_pattern(focal_title).search(t)
        )
        oa_check = openalex_edge_check(
            rec.get("openalex"), focal_oa_id.get(paper_key), mailto
        )

        if strong_local_edge:
            edge_confirmed, edge_verification = True, "local"
        elif oa_check["confirmed"] is True:
            edge_confirmed, edge_verification = True, "openalex"
        elif oa_check["confirmed"] is False and text_exists and not strong_local_edge:
            # contradição real: nem local nem OpenAlex confirmam. Não
            # vira false_edge automaticamente (OpenAlex tem cobertura de
            # referenced_works incompleta e comprovadamente lacunosa —
            # ver docs/revisao-literatura.md, "OpenAlex reference-count
            # caveat"); registra o conflito e mantém a nota do codificador
            # como evidência de desempate, sinalizado explicitamente.
            edge_confirmed, edge_verification = (
                True,
                "coder_note_conflict_with_openalex",
            )
        else:
            # nem local (sem corpo real ou corpo truncado) nem OpenAlex
            # concluíram algo -- vale a nota documentada do codificador em
            # classify.json (SHA-256 da evidência, §2 do METHOD.md: nenhuma
            # classificação sem passagem/leitura registrada).
            edge_confirmed, edge_verification = True, "coder_note_only"

        # -------------------- categoria --------------------
        strong_hit_types = {"surname", "et_al_year", "doi", "title6", "caption"}
        has_strong_hit = any(h["pattern"] in strong_hit_types for h in hits)
        has_strong_numeric = (
            len(bracket_hits) >= 2
            or len(super_hits) >= 2
            or (len(bracket_hits) + len(super_hits)) >= 2
        )

        if not edge_confirmed:
            category = "false_edge"
            reason = "aresta não confirmada nem localmente nem via OpenAlex."
        elif has_strong_hit or has_strong_numeric:
            category = "extraction_failure"
            bits = []
            if has_strong_hit:
                bits.append(
                    "marcador forte (sobrenome/et al.+ano/DOI/título/legenda) no corpo"
                )
            if has_strong_numeric:
                bits.append(
                    f"marcador numérico [{marker_n}] com >=2 ocorrências no corpo"
                )
            reason = "; ".join(bits) + " -- reclassificar como in_text."
        elif (not text_exists) or (not real_body):
            category = "body_unavailable"
            if not text_exists:
                reason = "sem text_path/arquivo local; veredito depende da leitura documentada do codificador."
            else:
                reason = (
                    f"corpo local não é real pela régua desta auditoria "
                    f"(refs_start={refs_start} via {refs_method}, heading_intro_metodo={has_head}); "
                    f"veredito depende da leitura documentada do codificador."
                )
        else:
            category = "genuine"
            reason = f"corpo real comprovado no disco ({refs_start} caracteres antes das referências), sem menção no texto."

        out_entries[doi] = {
            "id": rec["id"],
            "paper": paper_key,
            "doi": doi,
            "venue": rec.get("venue"),
            "year": rec.get("year"),
            "status_master": rec.get("status"),
            "work_type": rec.get("work_type"),
            "text_path": text_path,
            "text_exists": text_exists,
            "refs_boundary_method": refs_method,
            "body_chars_before_refs": refs_start,
            "has_intro_or_metodo_heading": has_head,
            "body_is_real": real_body,
            "hits": hits,
            "numeric_marker": {
                "n": marker_n,
                "kind": marker_kind,
                "bracket_hits": len(bracket_hits),
                "superscript_hits": len(super_hits),
            },
            "edge_confirmed": edge_confirmed,
            "edge_verification": edge_verification,
            "openalex_check": oa_check,
            "category": category,
            "category_reason": reason,
            "in_population_87": in_population_87(rec, editoras_estabelecidas),
            "quartil_scimago": auditlib.quartil_scimago(rec, sources),
            "coder_note": classify_entry.get("note"),
            "coder_prov": classify_entry.get("prov"),
        }

    # -------------------- resumo e taxas --------------------
    n_read_all = len(entries)  # D_read do ESTUDO inteiro (104), não só os 13
    cats = [e["category"] for e in out_entries.values()]
    counts_by_category = {
        c: cats.count(c)
        for c in ("genuine", "extraction_failure", "body_unavailable", "false_edge")
    }

    genuine_dois = [d for d, e in out_entries.items() if e["category"] == "genuine"]
    body_real_dois = [d for d, e in out_entries.items() if e["body_is_real"]]
    pop_dois = [d for d, e in out_entries.items() if e["in_population_87"]]
    genuine_in_pop = [d for d in genuine_dois if d in pop_dois]

    ghost_rate = {
        "D_read": dict(
            denominator_label="D_read (todas as 104 classificadas)",
            **rate_block(len(genuine_dois), n_read_all),
        ),
        "D_body": dict(
            denominator_label=f"D_body (das {len(out_entries)} só-bibliografia, com corpo real comprovado em disco)",
            **rate_block(
                len([d for d in genuine_dois if d in body_real_dois]),
                len(body_real_dois),
            ),
        ),
        "D_pop": dict(
            denominator_label=f"D_pop (das {len(out_entries)} só-bibliografia, dentro da população METHOD.md §9: DOI + editora "
            "estabelecida + artigo de periódico, sem capítulo/anais/preprint)",
            **rate_block(len(genuine_in_pop), len(pop_dois)),
        ),
    }

    # -------------------- cross-check com METHOD.md §12/13 --------------------
    quartile_dois = [
        d
        for d, e in out_entries.items()
        if e["quartil_scimago"] in ("Q1", "Q2", "Q3", "Q4")
    ]
    genuine_in_quartile = [d for d in genuine_dois if d in quartile_dois]
    cross_check = {
        "quartile_98_population_intersect_13": len(quartile_dois),
        "quartile_98_population_dois": sorted(quartile_dois),
        "genuine_among_quartile_98": len(genuine_in_quartile),
        "method_md_fantasma_count_S13": 7,
        "matches_method_md": len(genuine_in_quartile) == 7,
        "note": (
            "METHOD.md §13 já soma estas 7 entradas (6 Q1 + 1 Q3) como 'fantasma verificado' "
            "no total 98. Esta auditoria reexamina cada uma independentemente: "
            f"{len(genuine_in_quartile)} sobrevivem como 'genuine' sob a régua desta auditoria "
            "(corpo real comprovado NO DISCO, não apenas leitura do codificador via SSO); "
            "as demais viram body_unavailable e não devem ser lidas como refutação do achado "
            "original -- são um pedido de reverificação, não uma correção."
        ),
    }

    summary = {
        "n_ghost_entries": len(ghost_dois),
        "n_read_all_classified": n_read_all,
        "counts_by_category": counts_by_category,
        "ghost_rate": ghost_rate,
        "cross_check_method_md_S13": cross_check,
        "false_edges_outside_classify_check": {
            "expected_ids": ["airline_s008", "grains_s001"],
            "found_ids": [x["id"] for x in false_edges_outside_classify],
            "match": sorted(x["id"] for x in false_edges_outside_classify)
            == ["airline_s008", "grains_s001"],
        },
    }

    out = {
        "meta": {
            "script": "audit_67_ghost_audit.py",
            "root_insumos": str(root),
            "classify_source": classify_meta,
        },
        "entries": out_entries,
        "false_edges_outside_classify": false_edges_outside_classify,
        "summary": summary,
    }

    out_path = OUT_DATA / "ghost_audit.json"
    dump_json(out, out_path)

    # -------------------- tabela impressa --------------------
    print()
    print(f"ghost_audit.json escrito em {out_path}")
    print(
        f"classify usado: {classify_meta['path']} (fallback_used={classify_meta['fallback_used']})"
    )
    print()
    print(
        f"{'id':14s} {'paper':8s} {'categoria':18s} {'edge':6s} {'corpo_real':10s} {'n_hits':7s} {'quartil':7s} {'pop87':6s}"
    )
    for doi in ghost_dois:
        e = out_entries.get(doi)
        if not e:
            continue
        print(
            f"{e['id']:14s} {e['paper']:8s} {e['category']:18s} {e['edge_confirmed']!s:6s} "
            f"{e['body_is_real']!s:10s} {len(e['hits']):<7d} {e['quartil_scimago']!s:7s} {e['in_population_87']!s:6s}"
        )
    print()
    print("contagem por categoria:", counts_by_category)
    print()
    print("taxa de fantasma corrigida:")
    for label, blk in ghost_rate.items():
        r = blk["rate"]
        print(
            f"  {label}: {blk['numerator']}/{blk['denominator']} = {r * 100:.2f}%  IC95% Wilson=[{blk['ci95_wilson'][0] * 100:.2f}%, {blk['ci95_wilson'][1] * 100:.2f}%]  ({blk['denominator_label']})"
        )
    print()
    print(
        "cross-check METHOD.md §13 (7 fantasma entre os 98 com quartil):",
        cross_check["genuine_among_quartile_98"],
        "-> match"
        if cross_check["matches_method_md"]
        else "-> DIVERGE (ver nota no JSON)",
    )
    print()
    print("arestas falsas fora de classify.json (esperado airline_s008, grains_s001):")
    for x in false_edges_outside_classify:
        print(f"   {x['id']}  {x['doi']}  {x['venue']}")


if __name__ == "__main__":
    main()
