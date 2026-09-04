"""Invariantes dos dados. Sai com código 1 e uma mensagem por violação;
código 0 com um resumo de uma linha se tudo estiver ok.

Uso:
  python3 tools/check_data.py            invariantes de data/*.json (rápido, sem tocar text/)
  python3 tools/check_data.py --local    + invariantes contra text/*.txt em disco (mais lento)
"""
import collections
import hashlib
import sys

import auditlib

LOCAL = "--local" in sys.argv[1:]
PROV_KEYS = {"codebook", "coded_at", "coded_by", "evidence_kind", "evidence_sha256_16", "source"}

erros = []
avisos = []

master = auditlib.load_master()
classify = auditlib.classify_entries(auditlib.load_classify())
orfas = auditlib.classify_entries(auditlib.load_classify_orfas())
sources = auditlib.journal_sources(auditlib.load_journals())
decisoes = auditlib.load_decisoes_scimago()
recs = list(auditlib.iter_records(master))

# (1) tem_texto <=> text_path setado, relaxado para os dois outros status
# que também guardam arquivo em disco por desenho (audit_30 Regra 2 e
# audit_32 não desvinculam text_path de texto_parcial/evidencia_insuficiente
# -- só Regra 1, de texto_incorreto, desvincula). Sem a folga, 11 registros
# legítimos (10 texto_parcial + 1 evidencia_insuficiente) apareceriam como
# violação; com ela, a checagem bate 100% com o desenho real dos dados.
COM_ARQUIVO = {"tem_texto", "texto_parcial", "evidencia_insuficiente"}
for key, r in recs:
    tem_texto, tem_path = r["status"] == "tem_texto", bool(r.get("text_path"))
    if tem_texto and not tem_path:
        erros.append(f"(1) {r['id']}: status=tem_texto sem text_path")
    if tem_path and r["status"] not in COM_ARQUIVO:
        erros.append(f"(1) {r['id']}: text_path setado com status={r['status']!r} "
                     f"(fora de {sorted(COM_ARQUIVO)})")

# (2) text_path => text_source
for key, r in recs:
    if r.get("text_path") and not r.get("text_source"):
        erros.append(f"(2) {r['id']}: text_path setado sem text_source")

# (3) status em auditlib.STATUS
for key, r in recs:
    if r["status"] not in auditlib.STATUS:
        erros.append(f"(3) {r['id']}: status {r['status']!r} fora do vocabulário STATUS")

# (4) taxonomia + prov + hash de evidência, em classify.json E classify_orfas.json
hash_mismatches = []
for nome, entries in (("classify.json", classify), ("classify_orfas.json", orfas)):
    for doi, e in entries.items():
        if e.get("role") not in auditlib.TAXONOMIA["role"]:
            erros.append(f"(4) {nome}:{doi}: role {e.get('role')!r} fora de TAXONOMIA['role']")
        if e.get("stance") not in auditlib.TAXONOMIA["stance"]:
            erros.append(f"(4) {nome}:{doi}: stance {e.get('stance')!r} fora de TAXONOMIA['stance']")
        for t in (e.get("reuse") or []):
            if t not in auditlib.TAXONOMIA["reuse"]:
                erros.append(f"(4) {nome}:{doi}: reuse {t!r} fora de TAXONOMIA['reuse']")
        flag = e.get("flag")
        if flag is not None and flag not in auditlib.TAXONOMIA["flag"]:
            erros.append(f"(4) {nome}:{doi}: flag {flag!r} fora de TAXONOMIA['flag']")
        prov = e.get("prov") or {}
        if set(prov.keys()) != PROV_KEYS:
            faltam, sobram = PROV_KEYS - set(prov.keys()), set(prov.keys()) - PROV_KEYS
            erros.append(f"(4) {nome}:{doi}: prov com chaves erradas "
                         f"(faltam {sorted(faltam)}, sobram {sorted(sobram)})")
        passages = e.get("passages") or []
        if passages:
            want = hashlib.sha256("\n".join(passages).encode("utf-8")).hexdigest()[:16]
            got = prov.get("evidence_sha256_16")
            if got != want:
                hash_mismatches.append(f"{nome}:{doi} (gravado={got!r}, calculado={want!r})")
if hash_mismatches:
    avisos.append(f"(4) evidence_sha256_16 não bate com sha256(passages) em "
                  f"{len(hash_mismatches)} entrada(s) -- não falha, só reporta: " +
                  "; ".join(hash_mismatches))

# (5) toda chave de classify.json resolve a um DOI de master.json (zero órfãos;
# o 1 órfão conhecido mora em classify_orfas.json, fora desta checagem)
master_dois = {r["doi"].lower() for k, r in recs if r.get("doi")}
for doi in classify:
    if doi not in master_dois:
        erros.append(f"(5) classify.json:{doi}: não resolve a nenhum DOI de master.json "
                     f"(órfão deveria estar em classify_orfas.json)")

# (6) journals: tier/tier_base coerentes com a regra de audit_41_scimago
for msg in auditlib.tier_erros(sources):
    erros.append(f"(6) {msg}")

# (7) decisoes_scimago.json == registros com DOI sem quartil Scimago real
sem_quartil_ids = {r["id"] for k, r in recs if r.get("doi") and auditlib.quartil_scimago(r, sources) is None}
decisoes_ids = set(decisoes)
so_em_decisoes = sorted(decisoes_ids - sem_quartil_ids)
so_em_sem_quartil = sorted(sem_quartil_ids - decisoes_ids)
if so_em_decisoes:
    erros.append(f"(7) decisoes_scimago.json tem {len(so_em_decisoes)} id(s) que não são mais "
                 f"'sem quartil': {so_em_decisoes}")
if so_em_sem_quartil:
    erros.append(f"(7) {len(so_em_sem_quartil)} registro(s) com DOI sem quartil sem veredito em "
                 f"decisoes_scimago.json: {so_em_sem_quartil}")

# (8) --local: text/*.txt vs text_path referenciado
if LOCAL:
    text_files = sorted(p.name for p in auditlib.TEXT.glob("*.txt"))
    referenciados = set()
    for key, r in recs:
        p = r.get("text_path")
        if not p: continue
        referenciados.add(p.rsplit("/", 1)[-1])
        full = auditlib.ROOT / p
        if not full.exists():
            erros.append(f"(8) {r['id']}: text_path={p} não existe em disco")
            continue
        titulo = auditlib.norm_title(r.get("title"))[:38]
        corpo = auditlib.norm_title(full.read_text(encoding="utf-8", errors="ignore"))
        if titulo and titulo not in corpo:
            erros.append(f"(8) {r['id']}: {p} não contém o título do registro")

    orfaos = sorted(set(text_files) - referenciados)
    if orfaos:
        avisos.append(f"(8) {len(orfaos)} arquivo(s) em text/ não referenciados por nenhum "
                      f"text_path (órfãos): {orfaos}")

    hashes = collections.defaultdict(list)
    for fn in text_files:
        h = hashlib.sha256((auditlib.TEXT / fn).read_bytes()).hexdigest()
        hashes[h].append(fn)
    grupos = [v for v in hashes.values() if len(v) > 1]
    if grupos:
        avisos.append(f"(8) {len(grupos)} grupo(s) de arquivos byte-idênticos em text/: {grupos}")

for a in avisos:
    print(f"AVISO: {a}")

if erros:
    for e in erros:
        print(f"FALHA: {e}")
    print(f"\n{len(erros)} violação(ões) de invariante, {len(avisos)} aviso(s) ({'--local' if LOCAL else 'padrão'})")
    sys.exit(1)

print(f"ok ({'--local' if LOCAL else 'padrão'}): {len(recs)} registros, {len(classify)} classificados "
      f"(+1 órfão), {len(sources)} periódicos, {len(decisoes)} vereditos sem-quartil, "
      f"{len(avisos)} aviso(s), 0 violações")
