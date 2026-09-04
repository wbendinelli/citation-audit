"""Etapa 63: adjudicação da codificação múltipla.

Recebe as codificações de c1 (v2 migrada), c2 (Opus) e c3 (Sonnet) por item_id,
compara eixo a eixo, decide por maioria de três e separa o que fica contestado
(três valores distintos, ou eixo em que só há dois codificadores). O contestado
vai ao colegiado; o resultado do colegiado entra por --panel.

Uso:
  audit_63_adjudicate.py --dir data/irr [--panel data/irr/panel.json] --out data/irr/adjudication.json
"""

import argparse
import collections
import glob
import json
import os


def _load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


AXES = ["presence", "depth", "stance", "accuracy", "distortion"]
SETS = ["reuse", "claim_ids"]


def load_coder(pattern):
    """Aceita lista de objetos com item_id ou dicionário {item_id: rótulos}."""
    out = {}
    for p in sorted(glob.glob(pattern)):
        data = _load_json(p)
        items = (
            [dict(v, item_id=k) for k, v in data.items()]
            if isinstance(data, dict)
            else data
        )
        for it in items:
            out[it["item_id"]] = it
    return out


def majority(vals):
    """Maioria simples entre os codificadores presentes.
    Devolve (achou, valor, n). `None` é valor legítimo (eixo não aplicável)."""
    c = collections.Counter(json.dumps(v, sort_keys=True) for v in vals)
    top, n = c.most_common(1)[0]
    if n >= 2 and n > len(vals) - n:
        return True, json.loads(top), n
    return False, None, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument(
        "--panel",
        default=None,
        help="JSON {item_id: {eixo: valor}} com as decisões do colegiado",
    )
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    key = _load_json(os.path.join(a.dir, "pack_key.json"))
    c1 = load_coder(os.path.join(a.dir, "irr_c1_from_v2.json"))
    c2 = load_coder(os.path.join(a.dir, "coder_c2_opus_batch*.json"))
    c3 = load_coder(os.path.join(a.dir, "coder_c3_sonnet_batch*.json"))
    panel = _load_json(a.panel) if a.panel and os.path.exists(a.panel) else {}
    print(f"c1={len(c1)} c2={len(c2)} c3={len(c3)} painel={len(panel)}")

    result, contested, stats = {}, [], collections.Counter()
    for item_id, k in sorted(key.items()):
        if k.get("duplicate_of"):
            continue  # a sonda intra-codificador não entra na decisão
        coders = {n: c.get(item_id) for n, c in (("c1", c1), ("c2", c2), ("c3", c3))}
        present = {n: v for n, v in coders.items() if v}
        final, how = {}, {}
        for ax in AXES + SETS:
            vals = []
            for n, v in present.items():
                # c1 (codificação original) nunca preencheu distortion nem claim_ids:
                # abstém-se nesses eixos em vez de contar como discordância.
                if n == "c1" and ax in ("distortion", "claim_ids"):
                    continue
                x = v.get(ax)
                vals.append(sorted(x) if isinstance(x, list) else x)
            if not vals:
                final[ax], how[ax] = None, "sem_codificador"
                continue
            if item_id in panel and ax in panel[item_id]:
                final[ax], how[ax] = panel[item_id][ax], "colegiado"
                stats[f"{ax}:colegiado"] += 1
                continue
            if len(vals) == 1:
                final[ax], how[ax] = vals[0], "unico"
                stats[f"{ax}:unico"] += 1
                continue
            achou, maj, n = majority(vals)
            if achou and n == len(vals):
                final[ax], how[ax] = maj, "unanime"
                stats[f"{ax}:unanime"] += 1
            elif achou:
                final[ax], how[ax] = maj, f"maioria{n}/{len(vals)}"
                stats[f"{ax}:maioria"] += 1
            else:
                final[ax], how[ax] = None, "contestado"
                stats[f"{ax}:contestado"] += 1
                contested.append(
                    {
                        "item_id": item_id,
                        "doi": k["doi"],
                        "paper": k["paper"],
                        "axis": ax,
                        "values": {n: (v.get(ax)) for n, v in present.items()},
                        "rationales": {
                            n: v.get("rationale")
                            for n, v in present.items()
                            if n != "c1"
                        },
                    }
                )
        # distortion é derivada da acurácia final: nula se accurate; senão, maioria entre
        # os codificadores que também marcaram não-accurate (c1 abstém).
        acc = final.get("accuracy")
        if acc == "accurate" or acc is None:
            if how.get("distortion") == "contestado":
                contested[:] = [
                    c
                    for c in contested
                    if not (c["item_id"] == item_id and c["axis"] == "distortion")
                ]
                stats["distortion:contestado"] -= 1
            final["distortion"], how["distortion"] = None, "derivado_de_accuracy"
            stats["distortion:derivado"] += 1
        elif how.get("distortion") == "contestado":
            vals = [
                v.get("distortion")
                for n, v in present.items()
                if n != "c1" and v.get("accuracy") == acc and v.get("distortion")
            ]
            achou, maj, n = majority(vals) if vals else (False, None, 0)
            if achou or len(vals) == 1:
                contested[:] = [
                    c
                    for c in contested
                    if not (c["item_id"] == item_id and c["axis"] == "distortion")
                ]
                stats["distortion:contestado"] -= 1
                final["distortion"], how["distortion"] = (
                    (maj if achou else vals[0]),
                    "maioria_condicional",
                )
                stats["distortion:maioria_condicional"] += 1
        # claim_ids: recall — união do que os cegos invocaram
        if how.get("claim_ids") == "contestado":
            contested[:] = [
                c
                for c in contested
                if not (c["item_id"] == item_id and c["axis"] == "claim_ids")
            ]
            stats["claim_ids:contestado"] -= 1
            uni = sorted(
                {
                    x
                    for n, v in present.items()
                    if n != "c1"
                    for x in (v.get("claim_ids") or [])
                }
            )
            final["claim_ids"], how["claim_ids"] = uni, "uniao"
            stats["claim_ids:uniao"] += 1
        result[item_id] = {
            "doi": k["doi"],
            "paper": k["paper"],
            "final": final,
            "how": how,
            "coders": {
                n: {ax: v.get(ax) for ax in AXES + SETS} for n, v in present.items()
            },
        }
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(
            {"items": result, "contested": contested, "stats": dict(stats)},
            fh,
            ensure_ascii=False,
            indent=1,
            sort_keys=True,
        )
    print("por eixo:", {k: v for k, v in sorted(stats.items())})
    print(
        f"contestados (vão ao colegiado): {len(contested)} em {len({c['item_id'] for c in contested})} itens"
    )
    for ax in AXES + SETS:
        n = sum(1 for c in contested if c["axis"] == ax)
        if n:
            print(f"   {ax:<10} {n}")


if __name__ == "__main__":
    main()
