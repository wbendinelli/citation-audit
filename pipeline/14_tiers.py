"""Etapa 14: atribui tier aos periódicos e marca tipo de documento citante.

O tier usa `2yr_mean_citedness` do OpenAlex (proxy de fator de impacto). NÃO é
quartil Scimago/JCR — o Scimago bloqueia coleta automatizada. Os cortes estão
declarados abaixo e a métrica bruta fica gravada, de modo que trocar por quartil
oficial depois é substituir uma coluna.
"""
import json, os, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M  = json.load(open(f"{ROOT}/data/master.json"))
JR = json.load(open(f"{ROOT}/data/journals.json"))
CL = json.load(open(f"{ROOT}/data/classify.json"))

CORTES = [(6.0,"T1"),(3.5,"T2"),(2.0,"T3"),(0.0,"T4")]
def tier(c):
    if c is None: return None
    for lim,t in CORTES:
        if c >= lim: return t
    return "T4"

for m in JR.values():
    m["tier_proxy"] = tier(m.get("citedness_2a"))
    m["tier_base"]  = "openalex 2yr_mean_citedness"
json.dump(JR, open(f"{ROOT}/data/journals.json","w"), ensure_ascii=False, indent=1)

# tipo de documento citante, do OpenAlex
tipos = collections.Counter()
for k,b in M.items():
    for r in b["citing"]:
        tipos[r.get("work_type") or ("sem DOI" if not r.get("doi") else "?")] += 1
print("=== TIPO DE DOCUMENTO CITANTE (OpenAlex) ===")
for t,n in tipos.most_common(): print(f"  {n:>4}  {t}")

print("\n=== DISTRIBUIÇÃO DE TIER (proxy) ===")
byt = collections.Counter(m["tier_proxy"] for m in JR.values() if m["tier_proxy"])
for t in ("T1","T2","T3","T4"):
    if byt.get(t): print(f"  {t}: {byt[t]:>3} periódicos")

print("\n=== ONDE ESTÃO AS CITAÇÕES CLASSIFICADAS, POR TIER ===")
for key in ("airline","grains"):
    c = collections.Counter()
    for r in M[key]["citing"]:
        if not CL.get((r.get("doi") or "").lower()): continue
        m = JR.get(r.get("source_id") or "")
        c[(m or {}).get("tier_proxy") or "sem métrica"] += 1
    print(f"  {key:>8}: " + "  ".join(f"{t}={c[t]}" for t in ("T1","T2","T3","T4","sem métrica") if c.get(t)))

print("\n=== TOP 12 PERIÓDICOS QUE MAIS CITAM, COM MÉTRICA ===")
cnt = collections.Counter()
for k,b in M.items():
    for r in b["citing"]:
        if r.get("source_id"): cnt[r["source_id"]] += 1
print(f"  {'n':>3}  {'tier':<5}{'cit2a':>7}{'h':>6}  periódico")
for sid,n in cnt.most_common(12):
    m = JR.get(sid, {})
    print(f"  {n:>3}  {str(m.get('tier_proxy')):<5}{m.get('citedness_2a',0):>7.2f}{m.get('h_index',0):>6}  "
          f"{(m.get('nome') or '?')[:44]}  [{(m.get('editora') or '?')[:20]}]")
