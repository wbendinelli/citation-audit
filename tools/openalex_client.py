"""Cliente OpenAlex compartilhado por audit_64/65/66.

Camada fina sobre `auditlib.jget`: cache em disco por URL (uma chamada de
rede idêntica nunca é repetida entre execuções), paginação por cursor,
lotes de `filter=ids.openalex:...` e um contador de chamadas de rede vs.
acertos de cache que cada script grava em seu campo `requests` de saída.

Não é um script — só é importado por audit_64_refs_audit.py,
audit_65_cd_index.py e audit_66_cocitation.py.
"""

import hashlib
import json
import sys
import threading
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# Mesmo truque de import dos três scripts que usam este módulo: funciona
# direto quando openalex_client.py está ao lado de auditlib.py (produção,
# em tools/); durante o desenvolvimento no diretório de staging, cai no
# fallback abaixo (procura tools/ a partir do cwd, depois um caminho
# absoluto do repositório).
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

API = "https://api.openalex.org/works"

# Selects compartilhados: usar a MESMA string em audit_65 e audit_66 garante
# que as duas batem na mesma URL (portanto no mesmo arquivo de cache) quando
# pedem os citantes do artigo-foco, em vez de refazer a mesma paginação.
SELECT_P_CITERS = "id,publication_year,referenced_works,referenced_works_count,doi"
SELECT_R_CITERS = "id,publication_year"


def short_id(x):
    """'https://openalex.org/W123' ou 'W123' -> 'W123'. None-safe."""
    if not x:
        return None
    return x.rsplit("/", 1)[-1]


def select_param(fields):
    """Aceita string pronta ("a,b,c") ou lista/tupla de campos."""
    if isinstance(fields, str):
        return fields
    return ",".join(fields)


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def save_json(obj, path):
    """Grava JSON determinístico (sort_keys=True, indent=1, ensure_ascii=False),
    o mesmo padrão de auditlib._dump. Vive aqui só para não duplicar o
    boilerplate nos três scripts que importam este módulo de qualquer forma."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")


class OpenAlexClient:
    """GET com cache em disco (`data/cache/openalex/<sha1(url)>.json`) +
    índice (`index.json`: sha1 -> {url, fetched_at}) + contadores de rede.

    Thread-safe o suficiente para uso com ThreadPoolExecutor: as escadas de
    paginação de referências diferentes rodam em threads separadas, cada
    uma fazendo várias chamadas `.get()`; um Lock protege o índice e os
    contadores compartilhados.
    """

    def __init__(self, mailto=None, cache_dir=None, use_cache=True):
        cfg = auditlib.load_config()
        self.mailto = mailto or cfg.get("mailto") or cfg.get("contact_email") or ""
        self.cache_dir = (
            Path(cache_dir) if cache_dir else (auditlib.DATA / "cache" / "openalex")
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.use_cache = use_cache
        self.n_network = 0
        self.n_cache_hit = 0
        self.n_none = 0  # respostas nulas (404 definitivo ou falha após retries)
        self._lock = threading.Lock()
        self._index_path = self.cache_dir / "index.json"
        self._index = self._load_index()

    # ---------------- índice/cache ----------------

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

    def get(self, url):
        """GET JSON com cache. Adiciona `mailto=` à URL se ainda não tiver.

        NÃO cacheia resposta nula: `auditlib.jget` devolve `None` tanto
        para um 404 definitivo quanto para uma falha persistente depois
        dos retries (rate limit, timeout, erro 5xx) -- as duas situações
        são indistinguíveis no valor de retorno, e não há como diferenciar
        sem reimplementar o retry (o enunciado pede reaproveitar
        `auditlib.jget`, não substituí-lo). Cachear a segunda situação
        seria catastrófico: uma falha passageira de hoje (ex. orçamento
        de crédito do OpenAlex zerado -- ver nota de decisões ambíguas)
        viraria um "zero resultados" permanente e silencioso em toda
        execução futura que reusar o cache, mesmo depois do orçamento
        voltar. Então: só grava em disco (arquivo + índice) quando a
        resposta é não-nula; uma URL que falhou é tentada de novo na
        próxima chamada, cacheada ou não."""
        if "mailto=" not in url:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}mailto={urllib.parse.quote(self.mailto)}"
        key = self._cache_key(url)
        path = self.cache_dir / f"{key}.json"
        if self.use_cache and path.exists():
            with self._lock:
                self.n_cache_hit += 1
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        data = auditlib.jget(url)
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
        }

    # ---------------- endpoints ----------------

    def work_by_doi(self, doi, select=None):
        """GET /works/https://doi.org/<doi>. None se não resolver."""
        url = f"{API}/https://doi.org/{urllib.parse.quote(doi)}"
        if select:
            url += "?select=" + urllib.parse.quote(select_param(select), safe=",")
        return self.get(url)

    def work_by_id(self, work_id, select=None):
        wid = short_id(work_id)
        url = f"{API}/{wid}"
        if select:
            url += "?select=" + urllib.parse.quote(select_param(select), safe=",")
        return self.get(url)

    def works_by_ids(self, ids, select=None, batch_size=50):
        """Metadados de uma lista de IDs OpenAlex, em lotes de até
        `batch_size` via filter=ids.openalex:W1|W2|... Devolve dict
        id_curto -> registro. IDs que o OpenAlex não resolve (stub) ficam
        de fora do dict devolvido -- é assim que o chamador detecta stub."""
        out = {}
        ids = [short_id(i) for i in ids if i]
        for i in range(0, len(ids), batch_size):
            batch = ids[i : i + batch_size]
            filt = "ids.openalex:" + "|".join(batch)
            q = {"filter": filt, "per-page": str(batch_size)}
            if select:
                q["select"] = select_param(select)
            url = f"{API}?" + urllib.parse.urlencode(q, safe=",|:")
            page = self.get(url) or {}
            for rec in page.get("results", []) or []:
                out[short_id(rec["id"])] = rec
        return out

    def search_works(self, query, per_page=3, select=None):
        """Busca por título via `filter=title.search:<query>` -- NÃO usa o
        parâmetro genérico `search=` do OpenAlex. Achado testando o reparo
        do script 64 no artigo airline: `search=` faz busca de texto
        completo com ranking que não prioriza o título -- para "Causes
        and Effects of Air Traffic Delays: Evidence From Aggregated Data"
        ele devolveu artigos de poluição do ar e doença cardiovascular
        nos 3 primeiros resultados, porque o termo aparece disperso em
        corpos de texto irrelevantes entre 24 mil resultados; `title.search`
        restringe ao campo de título e achou o artigo certo como único
        resultado.

        `?` e `*` são removidos da consulta: o OpenAlex trata os dois como
        wildcard de "no-stem search" em QUALQUER campo `.search` (não só
        no `search=` genérico) e devolve erro 4xx se aparecerem no meio
        do texto -- ex. o título real "Do incumbents improve service
        quality in response to entry? Evidence from airlines' on-time
        performance" (referência 19 do airline) tem "?" no meio, não no
        fim, então nem dava pra só cortar a string. Sem tirar isso, a
        chamada falhava, `.get(url)` devolvia o payload de erro do
        OpenAlex (não None), e sem checar isso o chamador achava,
        silenciosamente, que a busca tinha dado zero resultados."""
        query = query.replace("?", " ").replace("*", " ")
        q = {"filter": f"title.search:{query}", "per-page": str(per_page)}
        if select:
            q["select"] = select_param(select)
        url = f"{API}?" + urllib.parse.urlencode(q)
        page = self.get(url)
        if not page or "results" not in page:
            return []
        return page.get("results", []) or []

    def works_citing(
        self, work_id, from_year=None, to_year=None, select=None, per_page=200, cap=None
    ):
        """Gera os registros de `works?filter=cites:<id>[,from_publication_date:...,
        to_publication_date:...]`, paginando por cursor até esgotar (ou até
        `cap` registros, se dado). `work_id` aceita ID curto ou URL completa."""
        wid = short_id(work_id)
        filt = f"cites:{wid}"
        if from_year:
            filt += f",from_publication_date:{from_year}-01-01"
        if to_year:
            filt += f",to_publication_date:{to_year}-12-31"
        q = {"filter": filt, "per-page": str(per_page)}
        if select:
            q["select"] = select_param(select)
        n = 0
        cursor = "*"
        while cursor:
            qq = dict(q, cursor=cursor)
            url = f"{API}?" + urllib.parse.urlencode(qq, safe=",|:*")
            page = self.get(url)
            if not page:
                break
            results = page.get("results") or []
            for rec in results:
                yield rec
                n += 1
                if cap is not None and n >= cap:
                    return
            cursor = (page.get("meta") or {}).get("next_cursor")
            if not results:
                break
