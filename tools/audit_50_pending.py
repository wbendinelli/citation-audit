"""Etapa 50: pendências. Deriva de master/classify/journals/decisoes_scimago
dois CSVs de trabalho:

  data/derived/pendencias.csv    todo registro com DOI e sem classificação
  data/derived/sem_quartil.csv   todo registro com DOI cujo periódico não
                                  tem quartil Scimago oficial, cruzado com
                                  o veredito manual (data/decisoes_scimago.json)

Uso:
  python3 tools/audit_50_pending.py           grava os dois CSVs
  python3 tools/audit_50_pending.py --check   renderiza em memória e compara
                                               byte a byte com os arquivos commitados
"""

import csv
import io
import json
import sys

import auditlib

CFG = auditlib.load_config()
GRANDES = CFG["editoras_estabelecidas"]

O_QUE_FAZER = {
    "oa_baixavel": "baixar: rota OA conhecida ainda não capturada (audit_20/21)",
    "oa_sem_pdf_direto": "abrir a landing page OA e extrair o texto manualmente",
    "oa_bloqueado": "sem rota OA automática — tentar acesso institucional ou pedir ao autor",
    "oa_antibot": "bloqueado por anti-bot — baixar manualmente e salvar em pdf/",
    "fechado": "sem via OA conhecida — acesso institucional, biblioteca ou pedido ao autor",
    "texto_parcial": "só página de rosto/abstract — buscar o texto completo por outra rota",
    "texto_incorreto": "arquivo não bate com o título do registro — buscar de novo",
    "evidencia_insuficiente": "corpo não comprovado — reconferir com o texto completo em mãos",
    "aresta_falsa": "aresta falsa confirmada — nada a baixar, só registrar",
    "tem_texto": "texto em mãos — falta ler a passagem e classificar em data/classify.json",
}

FIELDNAMES = [
    "id",
    "artigo",
    "doi",
    "link",
    "titulo",
    "veiculo",
    "ano",
    "editora",
    "editora_estabelecida",
    "quartil",
    "status",
    "o_que_fazer",
    "arquivo_destino",
]


def linha(key, r, sources):
    doi = r["doi"]
    m = sources.get(r.get("source_id") or "") or {}
    editora = m.get("editora") or r.get("publisher") or ""
    quartil = auditlib.quartil_scimago(r, sources)
    return {
        "id": r["id"],
        "artigo": key,
        "doi": doi,
        "link": f"https://doi.org/{doi}",
        "titulo": r.get("title") or "",
        "veiculo": r.get("venue") or "",
        "ano": r.get("year") or "",
        "editora": editora,
        "editora_estabelecida": auditlib.doi_prefix(doi) in GRANDES,
        "quartil": quartil or "-",
        "status": r["status"],
        "o_que_fazer": O_QUE_FAZER.get(r["status"], ""),
        "arquivo_destino": f"pdf/{r['id']}.pdf",
    }


def ordenar(rows):
    return sorted(
        rows, key=lambda l: (l["artigo"], l["status"], l["veiculo"] or "", l["id"])
    )


def render_csv(rows, fieldnames):
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    w.writeheader()
    for row in rows:
        w.writerow(row)
    return buf.getvalue()


def gerar():
    master = auditlib.load_master()
    classify = auditlib.classify_entries(auditlib.load_classify())
    sources = auditlib.journal_sources(auditlib.load_journals())
    with open(auditlib.DATA / "decisoes_scimago.json", encoding="utf-8") as f:
        decisoes = json.load(f)

    pendencias, sem_quartil = [], []
    for key, r in auditlib.iter_records(master):
        if not r.get("doi"):
            continue
        l = linha(key, r, sources)
        if not classify.get(r["doi"].lower()):
            pendencias.append(l)
        if auditlib.quartil_scimago(r, sources) is None:
            l2 = dict(l)
            dec = decisoes.get(r["id"], {})
            l2["veredito"] = dec.get("veredito", "")
            l2["razao"] = dec.get("razao", "")
            sem_quartil.append(l2)

    pendencias_csv = render_csv(ordenar(pendencias), FIELDNAMES)
    sem_quartil_csv = render_csv(
        ordenar(sem_quartil), FIELDNAMES + ["veredito", "razao"]
    )
    return (
        pendencias_csv,
        sem_quartil_csv,
        len(pendencias),
        len(sem_quartil),
        len(decisoes),
    )


pendencias_csv, sem_quartil_csv, n_pend, n_sq, n_dec = gerar()
OUT_PEND = auditlib.DATA / "derived" / "pendencias.csv"
OUT_SQ = auditlib.DATA / "derived" / "sem_quartil.csv"

if "--check" in sys.argv[1:]:
    erros = []
    for path, gerado, nome in (
        (OUT_PEND, pendencias_csv, "pendencias.csv"),
        (OUT_SQ, sem_quartil_csv, "sem_quartil.csv"),
    ):
        atual = path.read_text(encoding="utf-8") if path.exists() else None
        if atual != gerado:
            erros.append(nome)
            print(
                f"DRIFT: data/derived/{nome} gerado difere do commitado "
                f"({len(gerado)} chars gerados vs {len(atual) if atual is not None else 0} commitados)"
            )
    if erros:
        sys.exit(1)
    print(
        f"ok: pendencias.csv ({n_pend} linhas) e sem_quartil.csv ({n_sq} linhas, "
        f"{n_dec} vereditos) idênticos aos gerados"
    )
else:
    OUT_PEND.parent.mkdir(parents=True, exist_ok=True)
    OUT_PEND.write_text(pendencias_csv, encoding="utf-8")
    OUT_SQ.write_text(sem_quartil_csv, encoding="utf-8")
    print(
        f"-> data/derived/pendencias.csv: {n_pend} registros com DOI e sem classificação"
    )
    print(
        f"-> data/derived/sem_quartil.csv: {n_sq} registros com DOI sem quartil Scimago "
        f"({n_dec} com veredito manual em decisoes_scimago.json)"
    )
