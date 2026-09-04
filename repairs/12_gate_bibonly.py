"""Etapa 12: portão para o veredito 'só na bibliografia'.

Páginas de rosto de publisher (Springer, Wiley, etc.) exibem a lista de referências
completa sem o corpo do artigo. Nesses documentos, encontrar o sobrenome apenas na
bibliografia NÃO prova citação-fantasma — prova apenas que não temos o corpo.
Só é fantasma quem tem corpo comprovado e mesmo assim não menciona no texto.
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG  = json.load(open(f"{ROOT}/config.json")); SUR = CFG["author_surname"]
M    = json.load(open(f"{ROOT}/data/master.json"))
CL   = json.load(open(f"{ROOT}/data/classify.json"))

def eh_pagina_de_rosto(t):
    """Muitos marcadores por-referência e nenhum sinal de corpo = página de rosto."""
    marcadores = t.count("Google Scholar") + t.count("CrossRef") + t.count("PubMed")
    corpo = re.search(r"(?is)\b(introduction|introdu[cç][aã]o|1\.\s*Introduction)\b", t)
    if not corpo: return marcadores >= 8
    # há cabeçalho de introdução: exige prosa substancial antes das referências
    ref = re.search(r"(?im)^\s*(references|bibliography|refer[eê]ncias)\s*$", t)
    prosa = (ref.start() if ref else len(t)) - corpo.start()
    return prosa < 4000 and marcadores >= 8

rebaixados, confirmados = [], []
for key, blk in M.items():
    for r in blk["citing"]:
        if r.get("citation_status") != "bibliography_only": continue
        p = r.get("text_path")
        if not p or not os.path.exists(f"{ROOT}/{p}"): continue
        t = open(f"{ROOT}/{p}", encoding="utf-8", errors="ignore").read()
        if eh_pagina_de_rosto(t):
            r["status"] = "evidencia_insuficiente"
            r["citation_status"] = None
            r["nota_integridade"] = "página de rosto do publisher: lista de referências sem o corpo"
            rebaixados.append(r["id"])
        else:
            confirmados.append(r["id"])

# revalida as classificações 'bibliography_only' já registradas
revistas = []
for key, blk in M.items():
    for r in blk["citing"]:
        c = CL.get((r.get("doi") or "").lower())
        if not c or c.get("role") != "bibliography_only": continue
        p = r.get("text_path")
        if not p or not os.path.exists(f"{ROOT}/{p}"):
            revistas.append((r["id"], "sem arquivo para reconferir")); continue
        t = open(f"{ROOT}/{p}", encoding="utf-8", errors="ignore").read()
        if eh_pagina_de_rosto(t): revistas.append((r["id"], "era página de rosto"))

json.dump(M, open(f"{ROOT}/data/master.json","w"), ensure_ascii=False, indent=1)
print(f"rebaixados a evidência insuficiente: {len(rebaixados)}")
for x in rebaixados: print(f"   {x}")
print(f"\nfantasma confirmado (corpo presente, sem menção): {len(confirmados)}")
for x in confirmados: print(f"   {x}")
print(f"\nclassificações 'bibliography_only' a rever: {len(revistas)}")
for a,b in revistas: print(f"   {a}: {b}")
