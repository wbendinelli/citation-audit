"""Cliente Semantic Scholar (S2) -- backend alternativo ao OpenAlex para
audit_65_cd_index.py e audit_66_cocitation.py, usado quando o orçamento
diário de queries de lista do OpenAlex está zerado (HTTP 402/429
persistente -- foi exatamente o que travou a corrida de hoje, ver
data/cd/cd_airline.json antes deste script existir).

Academic Graph API (https://api.semanticscholar.org/graph/v1), sem chave
obrigatória. `works_citing()` abaixo tem A MESMA assinatura de
`OpenAlexClient.works_citing()` (openalex_client.py) -- work_id, from_year,
to_year, select -- e interpreta a MESMA string de `select`
(`oax.SELECT_P_CITERS`/`oax.SELECT_R_CITERS`, reaproveitadas daqui, não
redefinidas) para decidir que campos pedir ao S2 e traduzi-los de volta
para o formato de registro do OpenAlex (`id`, `publication_year`, `doi`,
`referenced_works`, `referenced_works_count`). É essa tradução -- não uma
reescrita dos scripts chamadores -- que deixa audit_65/audit_66 tratarem
os dois clientes de forma intercambiável: só troca qual objeto `client` é
construído (ver `--backend` em cada um).

Não é um script -- só é importado por audit_65_cd_index.py e
audit_66_cocitation.py (e por eles reexportado como `s2c`).
"""

import difflib
import hashlib
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import auditlib
except ImportError:
    for _cand in (
        Path.cwd() / "tools",
        Path("/Users/wbendinelli/Documents/citation-audit/tools"),
    ):
        if (_cand / "auditlib.py").exists():
            sys.path.insert(0, str(_cand))
            break
    import auditlib
import openalex_client as oax  # reaproveita SELECT_P_CITERS/SELECT_R_CITERS/short_id/save_json

API = "https://api.semanticscholar.org/graph/v1"

# ---------------- ritmo e retry (enunciado: 1.1s entre chamadas; 429 com
# backoff exponencial até 60s) ----------------
PACING_SECONDS = 1.1
MAX_TRIES = 5  # ver nota de decisões ambíguas #5: reduzido de 10
# depois de observar, nesta sessão, o pool sem
# chave recusando uma URL isolada por 14+ minutos
# seguidos -- 10 tentativas com teto de 60s soma
# ~5min PRESAS numa única URL; 5 tentativas (soma
# ~31s) falha rápido e deixa o restante do
# pipeline (ensure_id_map com retomada -- ver
# abaixo -- e as chamadas de fetch_r_citers, que
# são independentes por referência) seguir para
# a PRÓXIMA url em vez de travar minutos numa só.
BACKOFF_CAP = 60.0  # continua sendo o teto pedido no enunciado --
# com MAX_TRIES=5 nunca é alcançado de fato
# (2**4=16s é o maior intervalo desta sequência),
# mas fica como teto de segurança caso MAX_TRIES
# suba de novo no futuro.

# S2 recusa offset+limit > 10000 em /citations e /references.
OFFSET_LIMIT_CAP = 10000
PAGE_SIZE = 1000

# Limiares de casamento do mapeamento R_valid -> S2 paperId (ver
# build_id_map abaixo e a nota de decisões ambíguas no fim do arquivo).
TITLE_SIM_FLOOR = 0.90  # busca por título -- valor pedido no enunciado
DOI_SANITY_FLOOR = 0.40  # mesmo crivo de audit_64.DOI_SANITY_FLOOR

short_id = oax.short_id
save_json = oax.save_json
SELECT_P_CITERS = oax.SELECT_P_CITERS
SELECT_R_CITERS = oax.SELECT_R_CITERS


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _select_fields(select):
    if not select:
        return []
    if isinstance(select, str):
        return [s.strip() for s in select.split(",") if s.strip()]
    return list(select)


def _title_sim_raw(a, b):
    """Mesma ideia de audit_64_refs_audit.sim_raw(): razão difflib CRUA
    sobre auditlib.norm_title, sem a variante "token sort" de
    _title_sim() abaixo. Usada SÓ pelo crivo de sanidade de DOI
    (DOI_SANITY_FLOOR em build_id_map) -- nunca para aceitar um
    casamento por busca de título (isso é _title_sim). A razão crua é
    estrita de propósito: a variante token-sort é boa demais para esse
    job -- dois títulos sem nenhuma relação real podem convergir por
    coincidência de palavras curtas e comuns ao reordenar, que é
    exatamente o caso que este crivo existe para pegar. Achado testando
    o grains: para W1887601576 (ref 29, "cold storages... Bihar", cujo
    DOI no PDF aponta pra um manual de neurocirurgia -- ver decisão #2
    no fim do arquivo), a razão token-sort dá 0.45 (passaria um crivo de
    0.40), a mesma inflação que audit_64_refs_audit.py já documentou
    para esse par exato (nota #1 das decisões ambíguas de lá) -- a razão
    crua dá ~0.17, reprovando corretamente. Usar _title_sim() aqui
    (como uma primeira versão deste arquivo fez, ANTES desta função
    existir) reproduziria ao vivo o mesmo falso positivo que o crivo do
    lado OpenAlex existe para evitar."""
    na, nb = auditlib.norm_title(a or ""), auditlib.norm_title(b or "")
    if not na or not nb:
        return 0.0
    return difflib.SequenceMatcher(None, na, nb).ratio()


def _title_sim(a, b):
    """Mesma ideia de audit_64_refs_audit.sim(): melhor entre a razão
    difflib crua e a mesma razão com as palavras reordenadas
    alfabeticamente ("token sort"), sobre auditlib.norm_title. Usada
    para ACEITAR um casamento (DOI já resolvido, ou candidato de busca
    por título) -- nunca para o crivo de sanidade de DOI, que precisa da
    razão crua sozinha (_title_sim_raw acima). Duplicada aqui em vez de
    importada de audit_64 -- mesma convenção que fisher_exact_2x2 já
    segue entre audit_65/audit_66 (arquivo pequeno, cada script/módulo
    novo fica com a função por perto em vez de criar um acoplamento a um
    script que o enunciado marcou como "não mude")."""
    na, nb = auditlib.norm_title(a or ""), auditlib.norm_title(b or "")
    if not na or not nb:
        return 0.0
    r1 = difflib.SequenceMatcher(None, na, nb).ratio()
    ta, tb = " ".join(sorted(na.split())), " ".join(sorted(nb.split()))
    r2 = difflib.SequenceMatcher(None, ta, tb).ratio()
    return max(r1, r2)


class S2Client:
    """GET com cache em disco (`data/cache/s2/<sha1(url)>.json`) + índice
    + contadores de rede, mesmo desenho de `OpenAlexClient`
    (openalex_client.py) -- inclusive a mesma regra de nunca cachear
    resposta nula (ver o docstring de `OpenAlexClient.get`, idêntico aqui:
    um 429 sustentado hoje não pode virar um "zero citantes" permanente
    amanhã). Acrescenta o que o S2 exige e o OpenAlex não: ritmo mínimo
    entre chamadas (`_throttle`, com lock -- importante porque
    fetch_r_citers/fetch_seed_citers disparam várias referências em
    paralelo via ThreadPoolExecutor, e o limite de taxa do S2 é do
    processo inteiro, não por thread) e backoff exponencial em 429."""

    def __init__(self, api_key=None, cache_dir=None, use_cache=True):
        cfg = auditlib.load_config()
        mailto = cfg.get("mailto") or cfg.get("contact_email") or ""
        self.user_agent = f"citation-audit/1.0 (mailto:{mailto})"
        self.api_key = api_key if api_key is not None else os.environ.get("S2_API_KEY")
        self.cache_dir = (
            Path(cache_dir) if cache_dir else (auditlib.DATA / "cache" / "s2")
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.use_cache = use_cache
        self.n_network = 0
        self.n_cache_hit = 0
        self.n_none = 0  # respostas nulas (404 definitivo ou falha após retries)
        self.n_429 = 0  # só existe no lado S2 -- contagem de 429 absorvidos por retry
        self.truncated_ids = set()  # paperIds onde bateu o teto offset+limit<=10000
        self._lock = threading.Lock()
        self._rate_lock = threading.Lock()
        self._next_allowed_ts = 0.0
        self._index_path = self.cache_dir / "index.json"
        self._index = self._load_index()

    # ---------------- índice/cache (mesmo padrão de OpenAlexClient) ----------------

    def _load_index(self):
        if self._index_path.exists():
            try:
                with open(self._index_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_index_locked(self):
        with open(self._index_path, "w", encoding="utf-8") as f:
            json.dump(self._index, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.write("\n")

    @staticmethod
    def _cache_key(url):
        return hashlib.sha1(url.encode("utf-8")).hexdigest()

    # ---------------- ritmo + rede ----------------

    def _throttle(self):
        """Garante >= PACING_SECONDS entre o INÍCIO de duas chamadas de
        rede sucessivas, para TODAS as threads do processo (lock cobre só
        o cálculo/atualização do próximo horário permitido -- o sleep de
        espera acontece com o lock preso de propósito, para serializar as
        threads na fila; a chamada HTTP em si roda fora do lock)."""
        with self._rate_lock:
            now = time.monotonic()
            wait = self._next_allowed_ts - now
            if wait > 0:
                time.sleep(wait)
                now = time.monotonic()
            self._next_allowed_ts = now + PACING_SECONDS

    def _fetch(self, url):
        headers = {"Accept": "application/json", "User-Agent": self.user_agent}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        for attempt in range(MAX_TRIES):
            self._throttle()
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=90) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None
                if e.code == 429:
                    with self._lock:
                        self.n_429 += 1
                    retry_after = e.headers.get("Retry-After") if e.headers else None
                    try:
                        wait = (
                            float(retry_after)
                            if retry_after
                            else min(BACKOFF_CAP, 2**attempt)
                        )
                    except ValueError:
                        wait = min(BACKOFF_CAP, 2**attempt)
                    time.sleep(min(BACKOFF_CAP, max(1.0, wait)))
                    continue
                time.sleep(min(BACKOFF_CAP, 2**attempt))
            except Exception:
                time.sleep(min(BACKOFF_CAP, 2**attempt))
        return None

    def get(self, url):
        key = self._cache_key(url)
        path = self.cache_dir / f"{key}.json"
        if self.use_cache and path.exists():
            with self._lock:
                self.n_cache_hit += 1
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        data = self._fetch(url)
        with self._lock:
            self.n_network += 1
            if data is None:
                self.n_none += 1
        if data is not None:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            with self._lock:
                self._index[key] = {"url": url, "fetched_at": _now_iso()}
                self._save_index_locked()
        return data

    def stats(self):
        return {
            "network": self.n_network,
            "cache_hits": self.n_cache_hit,
            "none_responses": self.n_none,
            "total": self.n_network + self.n_cache_hit,
            "http_429_absorbed": self.n_429,
        }

    # ---------------- endpoints "de artigo único" ----------------

    def resolve_by_doi(
        self, doi, fields="paperId,externalIds,year,citationCount,referenceCount,title"
    ):
        """GET /paper/DOI:<doi>. None se o S2 não conhece o DOI (404) ou
        depois de esgotar os retries."""
        doi = auditlib.norm_doi(doi)
        if not doi:
            return None
        url = f"{API}/paper/DOI:{urllib.parse.quote(doi, safe='')}?fields={urllib.parse.quote(fields, safe=',')}"
        return self.get(url)

    def work_by_id(
        self,
        paper_id,
        fields="paperId,externalIds,year,citationCount,referenceCount,title",
    ):
        pid = short_id(paper_id)
        url = f"{API}/paper/{pid}?fields={urllib.parse.quote(fields, safe=',')}"
        return self.get(url)

    def search_title(self, query, limit=3, fields="paperId,title,year"):
        """GET /paper/search?query=<title>. `?`/`*` trocados por espaço
        por cautela (o crivo equivalente do lado OpenAlex, em
        audit_64.search_works, existe porque esses caracteres SÃO
        operador de wildcard lá; não há evidência de que o S2 trate os
        mesmos caracteres como operador, mas tirá-los da query não tem
        custo e evita depender dessa suposição)."""
        q = query.replace("?", " ").replace("*", " ")
        url = (
            f"{API}/paper/search?query={urllib.parse.quote(q)}"
            f"&fields={urllib.parse.quote(fields, safe=',')}&limit={limit}"
        )
        page = self.get(url)
        if not page or "data" not in page:
            return []
        return page.get("data") or []

    # ---------------- citantes (mesma interface de OpenAlexClient.works_citing) ----------------

    def works_citing(
        self,
        work_id,
        from_year=None,
        to_year=None,
        select=None,
        per_page=PAGE_SIZE,
        cap=None,
    ):
        """Gera registros no MESMO formato dos work dicts do OpenAlex
        (`id`, `publication_year`, `doi`, `referenced_works`,
        `referenced_works_count`) a partir de `/paper/{id}/citations`,
        paginando por offset até devolver menos que `limit` OU bater o
        teto do S2 (offset+limit<=10000 -- marca `self.truncated_ids` e
        avisa; ver docstring da classe/módulo).

        from_year/to_year são filtrados no CLIENTE: o endpoint de
        citações do S2 não tem um `filter=...,from_publication_date:...`
        como o OpenAlex, então não tem como pular página nem pedir só o
        intervalo -- é preciso paginar tudo e descartar o que cair fora
        (é por isso que o enunciado estima "algumas centenas de
        requisições" para o grains: não tem atalho). Um citante sem ano
        conhecido é excluído quando from_year/to_year é dado (mesmo
        comportamento efetivo do filtro de data do OpenAlex, que também
        não devolve registro sem data resolvida).

        `select` é A MESMA string usada no lado OpenAlex
        (oax.SELECT_P_CITERS/SELECT_R_CITERS) -- só SELECT_P_CITERS pede
        "referenced_works", e só por isso este método dispara uma chamada
        extra a /references POR CITANTE (ver `references_of` abaixo);
        nunca faz isso para os citantes de uma referência de R_valid
        (SELECT_R_CITERS não pede "referenced_works"), que é exatamente a
        distinção que o enunciado pede ("needed ONLY for citers of the
        focal paper")."""
        pid = short_id(work_id)
        fields = set(_select_fields(select))
        want_doi = "doi" in fields
        want_rwc = "referenced_works_count" in fields
        want_refs = "referenced_works" in fields
        s2_fields = ["citingPaper.paperId", "citingPaper.year"]
        if want_doi:
            s2_fields.append("citingPaper.externalIds")
        if want_rwc or want_refs:
            s2_fields.append("citingPaper.referenceCount")
        fields_param = urllib.parse.quote(",".join(s2_fields), safe=",.")

        n = 0
        offset = 0
        while True:
            limit = min(per_page, PAGE_SIZE, OFFSET_LIMIT_CAP - offset)
            if limit <= 0:
                with self._lock:
                    self.truncated_ids.add(pid)
                print(
                    f"    AVISO: {pid} atingiu o teto do S2 (offset+limit<=10000) -- "
                    f"cortando aqui, pode haver mais citantes não coletados"
                )
                break
            url = f"{API}/paper/{pid}/citations?fields={fields_param}&offset={offset}&limit={limit}"
            page = self.get(url)
            if not page:
                # None aqui pode ser exaustão genuína (raro nesta borda --
                # exaustão genuína normalmente aparece como 200 com
                # "data": [] antes de chegar perto do teto) ou a página
                # exatamente na borda offset+limit==10000 sendo recusada
                # pelo S2. Distingue: só perto do teto (>= 90% dele) marca
                # truncado; longe do teto, uma falha aqui já esgotou os
                # MAX_TRIES/backoff de _fetch e não há nada melhor a fazer
                # além de seguir em frente sem os citantes restantes desta
                # referência (mesma filosofia de "nunca cachear None" do
                # resto do cliente: fica faltando, não fica errado).
                if offset + limit >= OFFSET_LIMIT_CAP:
                    with self._lock:
                        self.truncated_ids.add(pid)
                    print(
                        f"    AVISO: {pid} -- página em offset={offset} (perto do teto de "
                        f"10000) falhou; tratando como teto atingido, pode haver mais citantes"
                    )
                break
            data = page.get("data") or []
            for item in data:
                cp = item.get("citingPaper") or {}
                cid = cp.get("paperId")
                if not cid:
                    continue
                year = cp.get("year")
                if from_year is not None or to_year is not None:
                    if year is None:
                        continue
                    if from_year is not None and year < from_year:
                        continue
                    if to_year is not None and year > to_year:
                        continue
                rec = {"id": cid, "publication_year": year}
                if want_doi:
                    ext = cp.get("externalIds") or {}
                    rec["doi"] = auditlib.norm_doi(ext.get("DOI"))
                rwc = cp.get("referenceCount")
                if want_rwc or want_refs:
                    rec["referenced_works_count"] = rwc
                if want_refs:
                    rec["referenced_works"] = self.references_of(cid) if rwc else []
                yield rec
                n += 1
                if cap is not None and n >= cap:
                    return
            if len(data) < limit:
                break
            offset += limit

    def references_of(self, paper_id, limit=1000):
        """Lista de S2 paperIds referenciados por `paper_id` -- usado só
        por works_citing() acima quando "referenced_works" está no
        select (ou seja, só para os citantes do artigo-foco), para o log
        de discrepâncias referenced_works x pertença de
        audit_65_cd_index.py. Capada no mesmo teto offset+limit<=10000 de
        works_citing, mas isto é a lista de referências de UM artigo só
        -- na prática nunca chega perto disso; um valor tão alto aqui
        seria sinal de bug, não de paginação legítima."""
        pid = short_id(paper_id)
        out = []
        offset = 0
        while offset < OFFSET_LIMIT_CAP:
            page_limit = min(limit, OFFSET_LIMIT_CAP - offset)
            url = (
                f"{API}/paper/{pid}/references?fields=citedPaper.paperId"
                f"&offset={offset}&limit={page_limit}"
            )
            page = self.get(url)
            if not page:
                break
            data = page.get("data") or []
            for item in data:
                cited = (item.get("citedPaper") or {}).get("paperId")
                if cited:
                    out.append(cited)
            if len(data) < page_limit:
                break
            offset += page_limit
        return out


# ================= mapeamento OpenAlex ID -> S2 paperId (R_valid) =================
#
# Ver nota de decisões ambíguas no fim do arquivo: refs_audit_<artigo>.json
# NÃO carrega DOI por referência (só openalex_refs[].title/year e
# pdf_refs[].status/openalex_id); o DOI, quando existe, está em
# refs_pdf_<artigo>.json (extração do PDF, não conferida). Por isso o
# mapeamento lê os dois arquivos.


def load_pdf_refs(paper):
    path = auditlib.DATA / "cd" / f"refs_pdf_{paper}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _reference_catalog(refs_audit, pdf_refs):
    """Por ID OpenAlex de R_valid: melhor título disponível (o título já
    casado pelo OpenAlex em openalex_refs -- preferido, é o que
    audit_64_refs_audit.py já confirmou contra o PDF -- senão o título
    cru extraído do PDF), ano e o DOI cru do PDF (pode ser None -- ver
    nota)."""
    oa_title = {
        r["id"]: (r.get("title"), r.get("year")) for r in refs_audit["openalex_refs"]
    }
    pdf_by_n = {r["n"]: r for r in pdf_refs}
    n_by_oid = {
        r["openalex_id"]: r["n"] for r in refs_audit["pdf_refs"] if r.get("openalex_id")
    }
    catalog = {}
    for oid in refs_audit["r_valid"]:
        n = n_by_oid.get(oid)
        pdf_r = pdf_by_n.get(n, {}) if n is not None else {}
        title, year = oa_title.get(oid, (None, None))
        if not title:
            title = pdf_r.get("title")
        if not year:
            year = pdf_r.get("year")
        catalog[oid] = {
            "pdf_n": n,
            "title": title,
            "year": year,
            "doi": auditlib.norm_doi(pdf_r.get("doi")),
        }
    return catalog


def _resolve_one_reference(client, oid, info):
    """Resolve uma única referência de R_valid (DOI, se houver, com o
    crivo de sanidade de título; senão busca por título). Devolve
    (oid, entry_ou_None, reason_se_None). Extraído de build_id_map para
    poder ser chamado em paralelo (ver nota abaixo)."""
    title = info["title"]
    entry = None
    if info["doi"]:
        hit = client.resolve_by_doi(
            info["doi"], fields="paperId,title,year,externalIds"
        )
        if hit and hit.get("paperId"):
            # _title_sim_raw (razão CRUA), não _title_sim (token-sort) --
            # ver o docstring de _title_sim_raw: usar a variante lenient
            # aqui deixaria passar o mesmo falso positivo que
            # audit_64_refs_audit.py documentou para este par exato.
            s = _title_sim_raw(hit.get("title"), title) if title else 1.0
            if s >= DOI_SANITY_FLOOR:
                entry = {
                    "s2_paper_id": hit["paperId"],
                    "via": "doi",
                    "sim": round(s, 4),
                    "doi_used": info["doi"],
                    "s2_title": hit.get("title"),
                }
            else:
                print(
                    f"    aviso: DOI {info['doi']} (ref OpenAlex {oid}, pdf_n={info['pdf_n']}) "
                    f"resolveu no S2 mas título não bate (sim={s:.2f} < {DOI_SANITY_FLOOR}) -- "
                    f"tratando como DOI errado na origem (mesmo caso do DOI_SANITY_FLOOR de "
                    f"audit_64), tentando busca por título"
                )
    if entry is None and title:
        cands = client.search_title(title, limit=3, fields="paperId,title,year")
        best, best_s = None, 0.0
        for c in cands:
            s = _title_sim(c.get("title"), title)
            if s > best_s:
                best, best_s = c, s
        if best is not None and best_s >= TITLE_SIM_FLOOR:
            entry = {
                "s2_paper_id": best["paperId"],
                "via": "title_search",
                "sim": round(best_s, 4),
                "doi_used": None,
                "s2_title": best.get("title"),
            }
    if entry is not None:
        entry.update(pdf_n=info["pdf_n"], title=title, year=info["year"])
        return oid, entry, None
    reason = (
        "sem DOI utilizável e busca por título não atingiu sim >= 0.90"
        if not info["doi"]
        else "DOI não resolveu ou reprovou o crivo de título, e busca por título "
        "não atingiu sim >= 0.90"
    )
    return oid, None, reason


def build_id_map(client, paper, refs_audit, only_oids=None, max_workers=6):
    """R_valid (IDs OpenAlex) -> S2 paperId. DOI primeiro quando
    disponível -- mas TODO acerto por DOI é conferido por similaridade de
    título antes de aceitar (mesmo raciocínio do DOI_SANITY_FLOOR de
    audit_64: refs_pdf_grains.json tem pelo menos um DOI errado na
    extração -- ref 29, "cold storages ... Bihar", aponta para um manual
    de neurocirurgia -- e sem essa conferência o mapeamento aceitaria a
    referência errada). Quando falta DOI, a resolução falha ou reprova o
    crivo de título, cai para busca por título (top 3, aceita
    sim >= TITLE_SIM_FLOOR=0.90, como pedido).

    Referências resolvidas em PARALELO (ThreadPoolExecutor, mesmo padrão
    de fetch_r_citers em audit_65_cd_index.py) -- não pela vazão de rede
    (o `_throttle` de S2Client serializa toda chamada real do processo
    inteiro, então N threads não fazem N requisições por segundo), mas
    porque o pool sem chave do S2 pode recusar uma URL específica por
    vários ciclos INTEIROS de backoff (visto nesta sessão: uma única
    referência presa mais de um minuto). Em série, esse tempo de espera
    fica ocioso -- nenhuma OUTRA referência avança enquanto uma está
    presa. Em paralelo, o `_throttle` compartilhado ainda impede duas
    chamadas simultâneas, mas assim que uma referência libera o próximo
    horário permitido (ela mesma em retry, ou outra pronta pra tentar), é
    isso que usa o horário -- a fila nunca fica vazia enquanto houver
    QUALQUER referência pendente. `only_oids`, se dado, restringe o
    processamento a este subconjunto de R_valid (usado por
    `ensure_id_map` para retomar só as referências que ficaram sem
    mapeamento numa chamada anterior)."""
    pdf_refs = load_pdf_refs(paper)
    catalog = _reference_catalog(refs_audit, pdf_refs)
    if only_oids is not None:
        catalog = {oid: info for oid, info in catalog.items() if oid in only_oids}
    mapped, unmapped = {}, []
    ordered_oids = sorted(catalog)
    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {
            ex.submit(_resolve_one_reference, client, oid, catalog[oid]): oid
            for oid in ordered_oids
        }
        for fut in as_completed(futs):
            oid, entry, reason = fut.result()
            info = catalog[oid]
            done += 1
            if entry is not None:
                mapped[oid] = entry
                print(
                    f"    [{done}/{len(ordered_oids)}] {oid} (pdf_n={info['pdf_n']}) -> "
                    f"{entry['s2_paper_id']} via={entry['via']} sim={entry['sim']}"
                )
            else:
                unmapped.append(
                    {
                        "openalex_id": oid,
                        "pdf_n": info["pdf_n"],
                        "title": info["title"],
                        "year": info["year"],
                        "doi_tried": info["doi"],
                        "reason": reason,
                    }
                )
                print(
                    f"    [{done}/{len(ordered_oids)}] {oid} (pdf_n={info['pdf_n']}) -> "
                    f"SEM MAPEAMENTO ({reason})"
                )
    return mapped, unmapped


def id_map_path(paper):
    return auditlib.DATA / "cd" / f"id_map_{paper}.json"


def load_id_map(paper):
    path = id_map_path(paper)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def ensure_id_map(
    client, paper, refs_audit, snapshot_date, force=False, retry_unmapped=True
):
    """Carrega data/cd/id_map_<paper>.json se já existir (garante reuso
    entre audit_65 e audit_66 no mesmo artigo, e as duas rodadas do
    airline pedidas para o diff byte-a-byte); senão constrói (DOI + busca
    por título) e grava.

    Retomável por referência (`retry_unmapped`, default True): se o
    arquivo já existe mas tem entradas em "unmapped", tenta de novo SÓ
    essas (não reprocessa quem já mapeou) e mescla no mesmo arquivo. Isto
    é o que torna viável rodar este script várias vezes em sequência como
    estratégia contra o pool sem chave do S2 -- observado nesta sessão
    recusando uma única URL por 14+ minutos seguidos: em vez de uma
    corrida só, muito paciente, por URL (MAX_TRIES alto), cada passada é
    rápida (MAX_TRIES=5, ~31s no pior caso por URL) e o que sobrar
    "unmapped" nesta passada tenta de novo na próxima chamada -- sem
    nunca refazer trabalho já bem-sucedido. `focal.s2_paper_id` também é
    re-tentado se ficou None (resolução do artigo-foco falhou antes)."""
    cached = None if force else load_id_map(paper)
    need_focal = cached is None or not (cached.get("focal") or {}).get("s2_paper_id")
    focal_hit = None
    if need_focal:
        focal_doi = refs_audit["focal"]["doi"]
        focal_hit = (
            client.resolve_by_doi(
                focal_doi,
                fields="paperId,externalIds,year,citationCount,referenceCount,title",
            )
            or {}
        )

    if cached is None:
        mapped, unmapped = build_id_map(client, paper, refs_audit)
    else:
        mapped = dict(cached.get("mapped") or {})
        prev_unmapped = cached.get("unmapped") or []
        if retry_unmapped and prev_unmapped:
            retry_oids = {u["openalex_id"] for u in prev_unmapped}
            print(
                f"  id_map_{paper}.json já existe com {len(prev_unmapped)} sem mapeamento -- "
                f"tentando de novo só essas ({len(mapped)} já mapeadas ficam como estão)..."
            )
            new_mapped, unmapped = build_id_map(
                client, paper, refs_audit, only_oids=retry_oids
            )
            mapped.update(new_mapped)
        else:
            unmapped = prev_unmapped

    focal_block = (
        cached.get("focal")
        if (cached is not None and not need_focal)
        else {
            "openalex_id": refs_audit["focal"]["openalex_id"],
            "doi": refs_audit["focal"]["doi"],
            "s2_paper_id": (focal_hit or {}).get("paperId"),
            "s2_citation_count": (focal_hit or {}).get("citationCount"),
            "s2_reference_count": (focal_hit or {}).get("referenceCount"),
            "s2_year": (focal_hit or {}).get("year"),
            "s2_title": (focal_hit or {}).get("title"),
            "openalex_cited_by_count": refs_audit["focal"]["cited_by_count"],
            "openalex_year": refs_audit["focal"]["year"],
        }
    )
    out = {
        "paper": paper,
        "backend": "semanticscholar",
        "snapshot_date": snapshot_date,
        "focal": focal_block,
        "n_r_valid": len(refs_audit["r_valid"]),
        "n_mapped": len(mapped),
        "n_unmapped": len(unmapped),
        "mapped": mapped,
        "unmapped": unmapped,
    }
    save_json(out, id_map_path(paper))
    return out


# ---------------- decisões ambíguas (ver relatório final) ----------------
# 1. refs_audit_<artigo>.json NÃO carrega DOI por referência (só
#    openalex_refs[].title/year, que audit_64_refs_audit.py monta sem o
#    campo "doi" mesmo pedindo-o no select de rede -- REF_SELECT inclui
#    "doi", só não é escrito no dicionário de saída). O enunciado descreve
#    R_valid como tendo "DOIs in refs_audit"; na prática o DOI (quando
#    existe) só está em refs_pdf_<artigo>.json (extração crua do PDF, não
#    conferida) -- e mesmo assim: 0/26 referências do airline têm DOI
#    extraído, e 23/45 do grains (das quais 35 são R_valid -- 23 têm DOI,
#    12 não). Por isso build_id_map() lê os dois arquivos e trata a busca
#    por título como o caminho PRINCIPAL (não o de reserva "para as ~5
#    reparadas sem DOI" que o enunciado antecipava) -- é o único caminho
#    disponível para 100% do airline e ~1/3 do grains.
# 2. Todo acerto por DOI é reconferido por similaridade de título
#    (DOI_SANITY_FLOOR=0.40, igual audit_64) antes de aceitar, em vez de
#    confiar direto no DOI como o enunciado sugere. Descoberto olhando os
#    dados: refs_pdf_grains.json tem o DOI de um manual de neurocirurgia
#    (10.1227/01.NEU.0000349921.14519.2A) anexado à referência 29 (Minten
#    et al., sobre armazenamento de batata em Bihar) -- exatamente o
#    mesmo DOI errado que a nota de decisões ambíguas #1 de
#    audit_64_refs_audit.py já documentou como razão de existir o crivo
#    do lado OpenAlex. Sem reconferir, o mapeamento S2 aceitaria esse DOI
#    (ele resolve para um artigo real no S2, só que o errado) e
#    contaminaria R_valid no lado S2 com uma referência completamente
#    alheia à bibliografia do PDF.
# 3. Foco (paper-alvo, não R_valid) resolvido só por DOI, sem o crivo de
#    título: os DOIs de config.json (via refs_audit["focal"]["doi"]) são
#    os mesmos usados por audit_64_refs_audit.py pra resolver os dois
#    artigos-foco no OpenAlex -- confirmados corretos (é o próprio artigo
#    do autor). Testado manualmente antes de escrever este cliente: os
#    dois resolvem no S2 para o paperId certo (título bate 100% nos dois
#    casos), mas com o campo "year" errado (airline: 2024 em vez de 2016;
#    grains: 2020 em vez de 2019 -- provável mesclagem de metadado do S2
#    com uma versão/preprint diferente). Por isso o ano do artigo-foco
#    (y_p, que define as janelas t do índice CD) SEMPRE vem de
#    refs_audit_<artigo>.json (produzido pelo OpenAlex via audit_64, já
#    correto), nunca do campo "year" do S2 -- o valor de "s2_year" é
#    gravado em id_map_<artigo>.json só como registro/diagnóstico.
# 4. Ritmo fixo em 1.1s mesmo com S2_API_KEY presente: o enunciado só
#    pede mandar a chave quando existir (eleva o limite de taxa), não
#    pedir mais rápido com ela. Não há chave configurada nesta sessão
#    (S2_API_KEY ausente do ambiente); o ritmo de 1.1s ficou fixo por
#    simplicidade e porque testes manuais desta sessão devolveram 429 do
#    pool sem chave mesmo com uma única chamada isolada (não uma rajada) —
#    sinal de que o pool compartilhado pode estar sob pressão de outros
#    clientes independente do meu próprio ritmo; ver MAX_TRIES/BACKOFF_CAP
#    acima para como isso é absorvido.
# 5. MAX_TRIES=5 (não 10) e ensure_id_map() retomável por referência
#    ("unmapped" de uma chamada anterior é tentado de novo, sem repetir
#    quem já mapeou -- controlado por `--remap` em audit_65/audit_66,
#    default DESLIGADO para não introduzir não-determinismo na corrida
#    "rodar 2x e comparar" pedida no enunciado): na primeira tentativa de
#    corrida real desta sessão, uma ÚNICA url (busca por título) ficou
#    presa 14+ minutos sem resolver com MAX_TRIES=10 (soma de backoff
#    ~5min POR url) -- o pool sem chave do S2 pareceu recusar a mesma URL
#    por vários ciclos de backoff inteiros seguidos. Esperar 5min por URL
#    presa, multiplicado por dezenas de referências (mais ainda no
#    grains), não fecha na janela de tempo disponível. Tentativas mais
#    curtas (MAX_TRIES=5, soma ~31s) mais VÁRIAS passadas do script
#    (cada uma só tentando de novo o que faltou, graças ao cache +
#    id_map retomável) usam o tempo de espera de forma muito mais
#    produtiva: enquanto uma URL específica pode continuar presa entre
#    passadas, as OUTRAS geralmente progridem, e o pool pode desafogar
#    entre uma passada e a próxima.
