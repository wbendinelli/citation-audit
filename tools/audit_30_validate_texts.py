"""Etapa 30: portão de integridade dos textos.

Regra 1 — o texto tem de conter o próprio título do registro. Se não contém,
o arquivo é de outro artigo: desvincula.
Regra 2 — texto curto sem o sobrenome citado é página de rosto/abstract,
não texto completo: marca como parcial e não conta como lido.
"""
import collections

import auditlib

CFG = auditlib.load_config()
SUR = CFG["author_surname"]
MIN_FULLTEXT = 15000

master = auditlib.load_master()
desvinc = parcial = ok = 0
for key, r in auditlib.iter_records(master):
    p = r.get("text_path")
    if not p or not (auditlib.ROOT / p).exists(): continue
    t = (auditlib.ROOT / p).read_text(encoding="utf-8", errors="ignore")
    tn, titulo = auditlib.norm_title(t), auditlib.norm_title(r.get("title"))
    # Regra 1: o texto precisa conter o título do próprio registro
    chave = titulo[:38]
    if chave and chave not in tn:
        r.pop("text_path", None); r.pop("text_source", None); r.pop("passages_auto", None)
        r["citation_status_auto"] = None
        r["status"] = "texto_incorreto"
        r["nota_integridade"] = "arquivo baixado não corresponde ao título do registro"
        desvinc += 1
        continue
    # Regra 2: curto e sem o sobrenome = página de rosto, não texto completo
    if SUR not in t and len(t) < MIN_FULLTEXT:
        r["status"] = "texto_parcial"
        r["nota_integridade"] = f"apenas página de rosto/abstract ({len(t)} chars)"
        r.pop("passages_auto", None); r["citation_status_auto"] = None
        parcial += 1
        continue
    r["status"] = "tem_texto"; ok += 1

auditlib.save_master(master)
c = collections.Counter(r["status"] for k, r in auditlib.iter_records(master))
print(f"desvinculados (arquivo de outro artigo) .. {desvinc}")
print(f"rebaixados a texto parcial ............... {parcial}")
print(f"texto completo validado .................. {ok}")
print()
for k,v in sorted(c.items(), key=lambda x:-x[1]): print(f"  {k:>22}: {v:>3}")
