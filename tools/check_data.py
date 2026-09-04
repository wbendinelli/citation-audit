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
# prov de uma entrada v2 (METHOD.md §16): as 9 chaves do v1 + as 3 que a
# migração acrescenta sempre; depth_basis só aparece quando a regra R3
# (wrongly_interpreted) se aplicou -- por isso é opcional, não exigida.
PROV_KEYS_V2 = {
    "codebook",
    "coded_at",
    "coded_by",
    "evidence_kind",
    "evidence_sha256_16",
    "source",
    "migrated_from_v1",
    "migration_rules",
    "adjudicated",
}
PROV_KEYS_V2_OPCIONAIS = {
    "depth_basis",
    # proveniência da adjudicação (METHOD §17–§18)
    "adjudicated_at",
    "coders",
    "decision",
    "irr_item_id",
    "labels_c1",
    "labels_c2",
    "labels_c3",
    "passage_source_in_pack",
    "panel_rationale",
    "coherence_note",
}

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
COM_ARQUIVO = {
    "tem_texto",
    "texto_parcial",
    "evidencia_insuficiente",
    "aresta_falsa",
}  # aresta_falsa: texto completo verificado que NÃO cita o artigo
for key, r in recs:
    tem_texto, tem_path = r["status"] == "tem_texto", bool(r.get("text_path"))
    if tem_texto and not tem_path:
        erros.append(f"(1) {r['id']}: status=tem_texto sem text_path")
    if tem_path and r["status"] not in COM_ARQUIVO:
        erros.append(
            f"(1) {r['id']}: text_path setado com status={r['status']!r} "
            f"(fora de {sorted(COM_ARQUIVO)})"
        )

# (2) text_path => text_source
for key, r in recs:
    if r.get("text_path") and not r.get("text_source"):
        erros.append(f"(2) {r['id']}: text_path setado sem text_source")

# (3) status em auditlib.STATUS
for key, r in recs:
    if r["status"] not in auditlib.STATUS:
        erros.append(
            f"(3) {r['id']}: status {r['status']!r} fora do vocabulário STATUS"
        )

# (4) taxonomia v2 + prov + hash de evidência, em classify.json E classify_orfas.json
# (4a) TAXONOMIA_V2 (auditlib, inline) bate com data/taxonomy_v2.json (fonte
# gerada por audit_60_taxonomy_v2.py) -- os dois vocabulários não podem
# divergir silenciosamente.
_tax_v2_json = auditlib.load_taxonomy_v2_json()
for eixo, info in _tax_v2_json["axes"].items():
    if eixo == "claims":
        continue
    want_axis = {"values": info["values"], "ranks": info.get("ranks")}
    got_axis = auditlib.TAXONOMIA_V2.get(eixo)
    if got_axis != want_axis:
        erros.append(
            f"(4) auditlib.TAXONOMIA_V2[{eixo!r}] diverge de data/taxonomy_v2.json: "
            f"auditlib={got_axis!r} json={want_axis!r}"
        )

# (4b) cada entrada: vocabulário por eixo, consistência presence/depth/accuracy/
# distortion, e prov com as chaves da migração (ver PROV_KEYS_V2 acima)
hash_mismatches = []
for nome, entries in (("classify.json", classify), ("classify_orfas.json", orfas)):
    for doi, e in entries.items():
        if "role" in e or "flag" in e:
            erros.append(
                f"(4) {nome}:{doi}: entrada ainda tem role/flag no topo (v1) -- "
                f"deveria estar só em prov.migrated_from_v1"
            )
        presence = e.get("presence")
        if presence not in auditlib.TAXONOMIA_V2["presence"]["values"]:
            erros.append(
                f"(4) {nome}:{doi}: presence {presence!r} fora de TAXONOMIA_V2['presence']"
            )
        in_text = presence == "in_text"
        depth = e.get("depth")
        if depth is not None and depth not in auditlib.TAXONOMIA_V2["depth"]["values"]:
            erros.append(
                f"(4) {nome}:{doi}: depth {depth!r} fora de TAXONOMIA_V2['depth']"
            )
        if (depth is not None) != in_text:
            erros.append(
                f"(4) {nome}:{doi}: depth {depth!r} inconsistente com presence {presence!r} "
                f"(depth é null sse presence != in_text)"
            )
        accuracy = e.get("accuracy")
        if (
            accuracy is not None
            and accuracy not in auditlib.TAXONOMIA_V2["accuracy"]["values"]
        ):
            erros.append(
                f"(4) {nome}:{doi}: accuracy {accuracy!r} fora de TAXONOMIA_V2['accuracy']"
            )
        if (accuracy is not None) != in_text:
            erros.append(
                f"(4) {nome}:{doi}: accuracy {accuracy!r} inconsistente com presence {presence!r} "
                f"(accuracy é null sse presence != in_text)"
            )
        distortion = e.get("distortion")
        if distortion is not None:
            if distortion not in auditlib.TAXONOMIA_V2["distortion"]["values"]:
                erros.append(
                    f"(4) {nome}:{doi}: distortion {distortion!r} fora de TAXONOMIA_V2['distortion']"
                )
            if accuracy == "accurate":
                erros.append(
                    f"(4) {nome}:{doi}: distortion {distortion!r} setado com accuracy=accurate"
                )
        relation = e.get("relation")
        if relation not in auditlib.TAXONOMIA_V2["relation"]["values"]:
            erros.append(
                f"(4) {nome}:{doi}: relation {relation!r} fora de TAXONOMIA_V2['relation']"
            )
        for f in e.get("record_flags") or []:
            if f not in auditlib.TAXONOMIA_V2["record_flags"]["values"]:
                erros.append(
                    f"(4) {nome}:{doi}: record_flags {f!r} fora de TAXONOMIA_V2['record_flags']"
                )
        highlight = e.get("highlight")
        if highlight not in auditlib.TAXONOMIA_V2["highlight"]["values"]:
            erros.append(
                f"(4) {nome}:{doi}: highlight {highlight!r} fora de TAXONOMIA_V2['highlight']"
            )
        stance = e.get("stance")
        if stance not in auditlib.TAXONOMIA_V2["stance"]["values"]:
            erros.append(
                f"(4) {nome}:{doi}: stance {stance!r} fora de TAXONOMIA_V2['stance']"
            )
        for t in e.get("reuse") or []:
            if t not in auditlib.TAXONOMIA_V2["reuse"]["values"]:
                erros.append(
                    f"(4) {nome}:{doi}: reuse {t!r} fora de TAXONOMIA_V2['reuse']"
                )
        prov = e.get("prov") or {}
        prov_keys = set(prov.keys())
        if not PROV_KEYS_V2.issubset(prov_keys):
            erros.append(
                f"(4) {nome}:{doi}: prov sem as chaves "
                f"{sorted(PROV_KEYS_V2 - prov_keys)}"
            )
        sobram = prov_keys - PROV_KEYS_V2 - PROV_KEYS_V2_OPCIONAIS
        if sobram:
            erros.append(
                f"(4) {nome}:{doi}: prov com chaves inesperadas {sorted(sobram)}"
            )
        passages = e.get("passages") or []
        if passages:
            want = hashlib.sha256("\n".join(passages).encode("utf-8")).hexdigest()[:16]
            got = prov.get("evidence_sha256_16")
            if got != want:
                hash_mismatches.append(
                    f"{nome}:{doi} (gravado={got!r}, calculado={want!r})"
                )
if hash_mismatches:
    avisos.append(
        f"(4) evidence_sha256_16 não bate com sha256(passages) em "
        f"{len(hash_mismatches)} entrada(s) -- não falha, só reporta: "
        + "; ".join(hash_mismatches)
    )

# (5) toda chave de classify.json resolve a um DOI de master.json (zero órfãos;
# o 1 órfão conhecido mora em classify_orfas.json, fora desta checagem)
master_dois = {r["doi"].lower() for k, r in recs if r.get("doi")}
for doi in classify:
    if doi not in master_dois:
        erros.append(
            f"(5) classify.json:{doi}: não resolve a nenhum DOI de master.json "
            f"(órfão deveria estar em classify_orfas.json)"
        )

# (6) journals: tier/tier_base coerentes com a regra de audit_41_scimago
for msg in auditlib.tier_erros(sources):
    erros.append(f"(6) {msg}")

# (7) decisoes_scimago.json == registros com DOI sem quartil Scimago real
sem_quartil_ids = {
    r["id"]
    for k, r in recs
    if r.get("doi") and auditlib.quartil_scimago(r, sources) is None
}
decisoes_ids = set(decisoes)
so_em_decisoes = sorted(decisoes_ids - sem_quartil_ids)
so_em_sem_quartil = sorted(sem_quartil_ids - decisoes_ids)
if so_em_decisoes:
    erros.append(
        f"(7) decisoes_scimago.json tem {len(so_em_decisoes)} id(s) que não são mais "
        f"'sem quartil': {so_em_decisoes}"
    )
if so_em_sem_quartil:
    erros.append(
        f"(7) {len(so_em_sem_quartil)} registro(s) com DOI sem quartil sem veredito em "
        f"decisoes_scimago.json: {so_em_sem_quartil}"
    )

# (8) --local: text/*.txt vs text_path referenciado
if LOCAL:
    text_files = sorted(p.name for p in auditlib.TEXT.glob("*.txt"))
    referenciados = set()
    for key, r in recs:
        p = r.get("text_path")
        if not p:
            continue
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
        avisos.append(
            f"(8) {len(orfaos)} arquivo(s) em text/ não referenciados por nenhum "
            f"text_path (órfãos): {orfaos}"
        )

    hashes = collections.defaultdict(list)
    for fn in text_files:
        h = hashlib.sha256((auditlib.TEXT / fn).read_bytes()).hexdigest()
        hashes[h].append(fn)
    grupos = [v for v in hashes.values() if len(v) > 1]
    if grupos:
        avisos.append(
            f"(8) {len(grupos)} grupo(s) de arquivos byte-idênticos em text/: {grupos}"
        )

for a in avisos:
    print(f"AVISO: {a}")

if erros:
    for e in erros:
        print(f"FALHA: {e}")
    print(
        f"\n{len(erros)} violação(ões) de invariante, {len(avisos)} aviso(s) ({'--local' if LOCAL else 'padrão'})"
    )
    sys.exit(1)

print(
    f"ok ({'--local' if LOCAL else 'padrão'}): {len(recs)} registros, {len(classify)} classificados "
    f"(+1 órfão), {len(sources)} periódicos, {len(decisoes)} vereditos sem-quartil, "
    f"{len(avisos)} aviso(s), 0 violações"
)
