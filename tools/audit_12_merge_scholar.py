"""Etapa 12: cruza as listas do Google Scholar com o inventário multi-fonte.

Os títulos do Scholar vêm truncados (~76 chars), então o casamento é por prefixo
normalizado, com verificação de similaridade.
"""

from difflib import SequenceMatcher

import auditlib

master = auditlib.load_master()

JUNK = {
    "my blog",
    "programa da disciplina",
    "kata pengantar",
    "scholar commons",
    "scientific communication",
    "innovation and green development",
    "journal of agriculture forestry research",
    "transportation research interdisciplinary perspectives",
}

report = {}
for key, fname in (("airline", "airline.txt"), ("grains", "grains.txt")):
    with open(auditlib.DATA / "scholar" / fname) as fh:
        lines = [l.rstrip("\n") for l in fh if l.strip()]
    scholar = []
    for l in lines:
        t, _, y = l.rpartition("|")
        scholar.append(
            {"title": t.strip(), "year": y.strip() or None, "n": auditlib.norm_title(t)}
        )

    have = [
        (auditlib.norm_title(r.get("title") or ""), r)
        for r in master["papers"][key]["citing"]
    ]
    matched, novos, junk = 0, [], 0
    for s in scholar:
        if s["n"] in JUNK or len(s["n"]) < 12:
            junk += 1
            continue
        hit = None
        for hn, r in have:
            if not hn:
                continue
            if hn.startswith(s["n"][:60]) or s["n"].startswith(hn[:60]):
                hit = r
                break
            if (
                len(s["n"]) > 30
                and SequenceMatcher(None, s["n"][:76], hn[:76]).ratio() > 0.90
            ):
                hit = r
                break
        if hit:
            matched += 1
            hit["src"] = sorted(set(hit.get("src", [])) | {"scholar"})
        else:
            novos.append(s)

    base = len(master["papers"][key]["citing"])
    for i, s in enumerate(novos, 1):
        master["papers"][key]["citing"].append(
            {
                "id": f"{key}_s{i:03d}",
                "doi": None,
                "title": s["title"],
                "year": s["year"],
                "venue": None,
                "oa_status": None,
                "is_oa": None,
                "src": ["scholar"],
                "status": "so_scholar",
                "nota_integridade": "título truncado pelo Scholar; sem DOI conhecido",
            }
        )
    report[key] = {
        "scholar": len(scholar),
        "junk": junk,
        "casados": matched,
        "novos": len(novos),
        "antes": base,
        "depois": len(master["papers"][key]["citing"]),
    }

auditlib.save_master(master)

print(
    f"{'':>9}{'Scholar':>9}{'ruido':>7}{'casados':>9}{'novos':>7}{'antes':>7}{'depois':>8}"
)
for k, r in report.items():
    print(
        f"{k:>9}{r['scholar']:>9}{r['junk']:>7}{r['casados']:>9}{r['novos']:>7}{r['antes']:>7}{r['depois']:>8}"
    )
tot = lambda f: sum(r[f] for r in report.values())
print(
    f"{'TOTAL':>9}{tot('scholar'):>9}{tot('junk'):>7}{tot('casados'):>9}{tot('novos'):>7}{tot('antes'):>7}{tot('depois'):>8}"
)
