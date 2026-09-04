"""Etapa 10: reparo. Os textos da primeira rodada foram nomeados pelos IDs antigos,
que não correspondem aos IDs do inventário atual. Re-arquiva por DOI e derruba
qualquer status 'tem_texto' que não tenha arquivo comprovado."""
import json, os, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TXT  = f"{ROOT}/text"
M    = json.load(open(f"{ROOT}/data/master.json"))
OLD  = json.load(open(f"{ROOT}/data/inventory.json"))

# 1) arquivos que o pipeline atual escreveu e cujo vínculo é confiável
autoritativos = {os.path.basename(r["text_path"])
                 for k, b in M.items() for r in b["citing"] if r.get("text_path")}

# 2) nome-de-arquivo-antigo -> DOI, a partir do inventário da primeira rodada
legacy_doi = {}
for key, blk in OLD.items():
    for it in blk["citing"]:
        if it.get("text_path") and it.get("doi"):
            legacy_doi[f"{key}_{it['n']:03d}.txt"] = it["doi"].lower()

# 3) DOI -> registro atual
by_doi = {}
for key, blk in M.items():
    for r in blk["citing"]:
        if r.get("doi"): by_doi.setdefault(r["doi"].lower(), r)

os.makedirs(f"{ROOT}/text_legacy", exist_ok=True)
recuperados = orfaos = 0
for fn in sorted(os.listdir(TXT)):
    if fn in autoritativos: continue
    doi = legacy_doi.get(fn)
    alvo = by_doi.get(doi) if doi else None
    if alvo and not alvo.get("text_path"):
        dest = f"{TXT}/{alvo['id']}.txt"
        if os.path.abspath(f"{TXT}/{fn}") != os.path.abspath(dest):
            shutil.copy(f"{TXT}/{fn}", dest)
        alvo["text_path"] = f"text/{alvo['id']}.txt"
        alvo["text_source"] = "rodada-1 (re-arquivado por DOI)"
        alvo["status"] = "tem_texto"
        recuperados += 1
    else:
        shutil.move(f"{TXT}/{fn}", f"{ROOT}/text_legacy/{fn}")   # tira do caminho
        orfaos += 1

# 4) nenhum registro pode alegar texto sem arquivo comprovado
rebaixados = 0
for key, blk in M.items():
    for r in blk["citing"]:
        p = r.get("text_path")
        if r["status"] == "tem_texto" and (not p or not os.path.exists(f"{ROOT}/{p}")):
            r.pop("text_path", None)
            r["status"] = "oa_bloqueado" if r.get("is_oa") else "fechado"
            rebaixados += 1

json.dump(M, open(f"{ROOT}/data/master.json","w"), ensure_ascii=False, indent=1)
import collections
c = collections.Counter(r["status"] for k,b in M.items() for r in b["citing"])
comtexto = sum(1 for k,b in M.items() for r in b["citing"]
               if r.get("text_path") and os.path.exists(f"{ROOT}/{r['text_path']}"))
print(f"re-arquivados por DOI ........ {recuperados}")
print(f"órfãos movidos p/ text_legacy  {orfaos}")
print(f"status 'tem_texto' rebaixado   {rebaixados}")
print(f"\ntextos com vínculo comprovado: {comtexto}")
for k,v in sorted(c.items(), key=lambda x:-x[1]): print(f"  {k:>22}: {v:>3}")
