"""Migração de uso único: eleva master/classify/journals ao esquema v2 e
cria data/decisoes_scimago.json a partir do CSV que ele substitui.

Roda uma vez, é commitada junto com o resultado, e depois se remove (git rm)
— não faz parte do pipeline reprodutível. Ver o plano de reorganização
(passo 2) para o que cada transformação abaixo faz e por quê.
"""
import collections
import csv
import json

import auditlib

HOJE = "2026-09-04"

FONTES = {
    "airline": {"openalex": 53, "s2": 49, "opencitations": 39, "europepmc": 0, "uniao": 69},
    "grains":  {"openalex": 60, "s2": 54, "opencitations": 50, "europepmc": 0, "uniao": 62},
}
SCHOLAR_META = {
    "airline": {"listadas": 95, "ruido": 5, "casados": 66, "novos": 24},
    "grains":  {"listadas": 76, "ruido": 3, "casados": 52, "novos": 21},
}
STATUS_TEM_TEXTO_SEM_ARQUIVO = ("airline_002", "airline_007", "airline_051", "grains_028")


def migrar_master():
    master = auditlib.load_master()
    if master["meta"].get("schema", 1) >= 2:
        print("master.json já está no esquema v2 -- pulando"); return

    # back-fill de s2_intents/s2_influential a partir do inventário (round 1),
    # por DOI em minúsculas -- só nos registros em que o inventário os traz.
    inv_by_doi = {}
    try:
        with open(auditlib.DATA / "inventory.json", encoding="utf-8") as f:
            inv = json.load(f)
        for blk in inv.values():
            for it in blk["citing"]:
                d = (it.get("doi") or "").lower()
                if d: inv_by_doi[d] = it
    except FileNotFoundError:
        print("aviso: data/inventory.json não encontrado -- s2_intents/s2_influential não serão back-filled")

    dropados = renomeados = backfilled = anos_normalizados = 0
    for key, r in auditlib.iter_records(master):
        for campo in ("classificado", "type", "nota"):
            if campo in r: r.pop(campo); dropados += 1
        for old, new in (("passages", "passages_auto"), ("passage_how", "passages_how"),
                          ("citation_status", "citation_status_auto")):
            if old in r:
                r[new] = r.pop(old); renomeados += 1
        if not r.get("text_path"):
            r.pop("text_source", None)
        inv_rec = inv_by_doi.get((r.get("doi") or "").lower())
        if inv_rec:
            if "s2_intents" in inv_rec: r["s2_intents"] = inv_rec["s2_intents"]; backfilled += 1
            if "s2_influential" in inv_rec: r["s2_influential"] = inv_rec["s2_influential"]
        if isinstance(r.get("year"), str) and r["year"].strip().isdigit():
            r["year"] = int(r["year"]); anos_normalizados += 1

    # os 4 registros que alegam tem_texto sem arquivo (a leitura do SSO está
    # em classify.prov.source, não em master): fecham explicitamente.
    fixados_explicito = 0
    for key, r in auditlib.iter_records(master):
        if r["id"] in STATUS_TEM_TEXTO_SEM_ARQUIVO:
            assert r["status"] == "tem_texto" and not r.get("text_path"), \
                f"{r['id']}: pressuposto do passo 2 não bate mais, reveja a migração"
            r["status"] = "fechado"
            fixados_explicito += 1

    # invariante tem_texto <=> text_path existe em disco -- qualquer OUTRO
    # violador (não deveria haver nenhum a essa altura) é rebaixado.
    outros_violadores = 0
    for key, r in auditlib.iter_records(master):
        p = r.get("text_path")
        tem_arquivo = bool(p) and (auditlib.ROOT / p).exists()
        if r["status"] == "tem_texto" and not tem_arquivo:
            novo = "oa_bloqueado" if r.get("is_oa") else "fechado"
            print(f"  invariante: {r['id']} tem_texto sem arquivo -> {novo}")
            r["status"] = novo
            outros_violadores += 1

    master["meta"] = {
        "schema": 2,
        "harvested_at": HOJE,
        "fontes": FONTES,
        "scholar": SCHOLAR_META,
    }
    auditlib.save_master(master)
    print(f"master.json -> v2: {dropados} campos removidos, {renomeados} renomeados, "
          f"{backfilled} registros com s2_intents/s2_influential back-filled, "
          f"{anos_normalizados} anos normalizados para int, "
          f"{fixados_explicito} registros fechados explicitamente, "
          f"{outros_violadores} outros violadores da invariante corrigidos")


def _migrar_classify(nome, coders):
    path = auditlib.DATA / nome
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict) and "meta" in raw and "entries" in raw:
        print(f"{nome} já está no esquema v2 -- pulando"); return
    entries = raw
    limpos = 0
    for doi, e in entries.items():
        if "citation_status" in e:
            e.pop("citation_status"); limpos += 1
        if e.get("flag") == "":
            e["flag"] = None; limpos += 1
    out = {"meta": {"schema": 2, "codebook": "METHOD.md@v1", "coders": coders}, "entries": entries}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    print(f"{nome} -> v2: {len(entries)} entradas, {limpos} campos limpos")


def migrar_journals():
    journals = auditlib.load_journals()
    if journals["meta"].get("schema", 1) >= 2:
        print("journals.json já está no esquema v2 -- pulando"); return
    cfg = auditlib.load_config()
    journals["meta"] = {
        "schema": 2,
        "scimago_edition": cfg["scimago"]["edition"],
        "scimago_sha256": cfg["scimago"]["sha256"],
    }
    auditlib.save_journals(journals)
    print(f"journals.json -> v2: {len(auditlib.journal_sources(journals))} periódicos")


def criar_decisoes_scimago():
    src = auditlib.DATA / "com_doi_sem_scimago.csv"
    dest = auditlib.DATA / "decisoes_scimago.json"
    out = {}
    with open(src, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[row["id"]] = {"veredito": row["veredito"], "razao": row["razao"]}
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    print(f"data/decisoes_scimago.json <- {len(out)} vereditos de {src.name}")


if __name__ == "__main__":
    migrar_master()
    _migrar_classify("classify.json", ["claude-opus-5"])
    _migrar_classify("classify_orfas.json", ["claude-opus-5"])
    migrar_journals()
    criar_decisoes_scimago()
