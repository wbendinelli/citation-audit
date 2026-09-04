"""Etapa 15: importa o ranking Scimago e substitui o tier proxy por quartil oficial.

Uso: baixar o CSV em https://www.scimagojr.com/journalrank.php?out=xls e deixar
em data/ (qualquer nome contendo 'scimago'). O arquivo é delimitado por ';' e usa
vírgula como separador decimal.

Casamento por ISSN. O Scimago grava ISSN sem hífen e em lista separada por vírgula;
o OpenAlex grava com hífen. A normalização remove tudo que não for dígito ou X.
"""
import csv, glob, json, os, re, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JR   = json.load(open(f"{ROOT}/data/journals.json"))

cands = [p for p in glob.glob(f"{ROOT}/data/*") if "scimago" in os.path.basename(p).lower()]
if not cands:
    raise SystemExit("CSV do Scimago não encontrado em data/ — baixe de "
                     "https://www.scimagojr.com/journalrank.php?out=xls")
path = max(cands, key=os.path.getmtime)
print(f"lendo {os.path.basename(path)}")

def norm_issn(s):
    return {re.sub(r"[^0-9X]", "", x.upper()) for x in re.split(r"[,\s]+", s or "") if x.strip()}

def num(s):
    s = (s or "").strip().replace(",", ".")
    try: return float(s)
    except ValueError: return None

# 1) índice ISSN -> linha do Scimago
idx, linhas = {}, 0
with open(path, encoding="utf-8-sig", errors="replace") as f:
    for row in csv.DictReader(f, delimiter=";"):
        linhas += 1
        for i in norm_issn(row.get("Issn")):
            if len(i) == 8: idx.setdefault(i, row)
print(f"{linhas} periódicos no Scimago, {len(idx)} ISSNs indexados")

# 2) casa com nossos periódicos
casou = 0
for sid, m in JR.items():
    issns = norm_issn(m.get("issn_l") or "") | norm_issn(" ".join(m.get("issn") or []))
    row = next((idx[i] for i in issns if i in idx), None)
    if not row:
        m["scimago"] = None
        continue
    casou += 1
    cats = row.get("Categories") or ""
    m["scimago"] = {
        "titulo": row.get("Title"),
        "sjr": num(row.get("SJR")),
        "quartil": (row.get("SJR Best Quartile") or "").strip() or None,
        "h_index": num(row.get("H index")),
        "areas": (row.get("Areas") or "").strip(),
        "categorias": cats.strip(),
        "editora": (row.get("Publisher") or "").strip(),
        "pais": (row.get("Country") or "").strip(),
        "rank": num(row.get("Rank")),
    }
    m["tier"] = m["scimago"]["quartil"]        # tier oficial passa a valer
    m["tier_base"] = "Scimago SJR Best Quartile"

for m in JR.values():
    m.setdefault("tier", None)
    if m.get("tier") is None:                   # sem correspondência: mantém o proxy, marcado
        m["tier"] = m.get("tier_proxy")
        m["tier_base"] = "proxy OpenAlex (sem correspondência no Scimago)"

json.dump(JR, open(f"{ROOT}/data/journals.json","w"), ensure_ascii=False, indent=1)
print(f"\ncasaram {casou}/{len(JR)} periódicos com o Scimago")
q = collections.Counter(m.get("scimago",{}).get("quartil") for m in JR.values() if m.get("scimago"))
print("quartis:", dict(sorted(q.items(), key=lambda x: str(x[0]))))
falt = [m["nome"] for m in JR.values() if not m.get("scimago")]
print(f"\nsem correspondência ({len(falt)}) — conferir se são repositório ou periódico novo:")
for n in falt[:20]: print(f"   {n}")
