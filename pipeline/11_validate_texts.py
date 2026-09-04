"""Etapa 11: portão de integridade dos textos.

Regra 1 — o texto tem de conter o próprio título do registro. Se não contém,
o arquivo é de outro artigo: desvincula.
Regra 2 — texto curto sem o sobrenome citado é página de rosto/abstract,
não texto completo: marca como parcial e não conta como lido.
"""
import json, os, re, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG  = json.load(open(f"{ROOT}/config.json")); SUR = CFG["author_surname"]
M    = json.load(open(f"{ROOT}/data/master.json"))
MIN_FULLTEXT = 15000

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()

desvinc = parcial = ok = 0
for key, blk in M.items():
    for r in blk["citing"]:
        p = r.get("text_path")
        if not p or not os.path.exists(f"{ROOT}/{p}"): continue
        t = open(f"{ROOT}/{p}", encoding="utf-8", errors="ignore").read()
        tn, titulo = norm(t), norm(r.get("title"))
        # Regra 1: o texto precisa conter o título do próprio registro
        chave = titulo[:38]
        if chave and chave not in tn:
            r.pop("text_path", None); r.pop("passages", None)
            r["citation_status"] = None
            r["status"] = "texto_incorreto"
            r["nota_integridade"] = "arquivo baixado não corresponde ao título do registro"
            desvinc += 1
            continue
        # Regra 2: curto e sem o sobrenome = página de rosto, não texto completo
        if SUR not in t and len(t) < MIN_FULLTEXT:
            r["status"] = "texto_parcial"
            r["nota_integridade"] = f"apenas página de rosto/abstract ({len(t)} chars)"
            r.pop("passages", None); r["citation_status"] = None
            parcial += 1
            continue
        r["status"] = "tem_texto"; ok += 1

json.dump(M, open(f"{ROOT}/data/master.json","w"), ensure_ascii=False, indent=1)
import collections
c = collections.Counter(r["status"] for k,b in M.items() for r in b["citing"])
print(f"desvinculados (arquivo de outro artigo) .. {desvinc}")
print(f"rebaixados a texto parcial ............... {parcial}")
print(f"texto completo validado .................. {ok}")
print()
for k,v in sorted(c.items(), key=lambda x:-x[1]): print(f"  {k:>22}: {v:>3}")
