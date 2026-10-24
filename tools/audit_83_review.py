"""Gera a revisão da atualização, com contagens correntes e anteriores rastreáveis."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/01-impacto/revisao-atualizacao.md"


def render():
    d = json.loads((OUT.parent / "dados.json").read_text())
    old = d["atualizacao"]["anterior"]
    e, c = d["eixos"]["pooled"], d["cobertura_quartil"]["total"]
    eo, co = old["eixos"]["pooled"], old["cobertura_quartil"]["total"]
    rows = [
        (
            "Registros do inventário",
            old["inventario"]["total"],
            d["inventario"]["total"],
        ),
        (
            "Com DOI",
            old["inventario"]["com_doi"]["total"],
            d["inventario"]["com_doi"]["total"],
        ),
        ("População do estudo", old["populacao"]["total"], d["populacao"]["total"]),
        (
            "Classificações com passagem",
            old["meta"]["n_classificados"],
            d["meta"]["n_classificados"],
        ),
        (
            "Classificadas na população",
            old["populacao"]["classificados_dentro_da_populacao"]["total"],
            d["populacao"]["classificados_dentro_da_populacao"]["total"],
        ),
        (
            "Menções no corpo",
            eo["presence"]["in_text"]["n"],
            e["presence"]["in_text"]["n"],
        ),
        (
            "Má atribuição",
            eo["accuracy"]["misrepresented"]["n"],
            e["accuracy"]["misrepresented"]["n"],
        ),
        ("Trecho literal entre registros com quartil", co["trecho"], c["trecho"]),
        ("Pendentes entre registros com quartil", co["pendente"], c["pendente"]),
    ]
    for paper in ("airline", "grains"):
        before = old["cd"][paper]["cd_index"]["windows"]["5"]
        after = d["cd"][paper]["cd_index"]["windows"]["5"]
        rows.extend(
            [
                (f"CD5 ({paper})", f"{before['CD']:.6f}", f"{after['CD']:.6f}"),
                (
                    f"DI5 ({paper})",
                    f"{before['DI5']['value']:.6f}",
                    f"{after['DI5']['value']:.6f}",
                ),
            ]
        )
    before = old["cocitacao"]["periods"]["main"]
    after = d["cocitacao"]["periods"]["main"]
    rows.append(
        (
            "Co-citação posterior (share AB)",
            f"{before['post']['share_AB']:.6f}",
            f"{after['post']['share_AB']:.6f}",
        )
    )
    table = "\n".join(
        f"| {name} | {before} | {after} |" for name, before, after in rows
    )
    sources = "\n".join(
        f"| {paper} | {name} | {source['status']} | {source.get('records', 'indisponível')} |"
        for paper, block in d["meta"]["coleta"]["papers"].items()
        for name, source in block["sources"].items()
    )
    graphs = "\n".join(
        f"- `{paper}`: snapshot {json.loads((ROOT / 'data/cd' / f'cd_{paper}.json').read_text()).get('snapshot_date', 'não informado')}."
        for paper in ("airline", "grains")
    )
    return f"""<!-- Gerado por tools/audit_83_review.py; não editar contagens à mão. -->
# Revisão da atualização — {d["meta"]["gerado_em"]}

A coleta pública foi repetida e a análise refeita. A população conserva o critério
registrado em [METHOD.md](../../METHOD.md). Valores anteriores abaixo ficam
**corrigidos na apresentação corrente**, preservados como snapshot histórico.

| Medida | Snapshot anterior | Atual |
|---|---:|---:|
{table}

Fonte: `audit_70 §atualizacao`, `§inventario`, `§populacao`, `§cobertura` e `§eixos`;
[dados gerados](dados.json). As contagens da edição anterior estão preservadas em
[data/baselines](../../data/baselines/2026-09-04.json).

## Coleta e deduplicação

| Artigo | Base | Resposta | Registros retornados |
|---|---|---|---:|
{sources}

As APIs não acrescentaram obras após a deduplicação. Elas completaram metadados
e documentaram DOIs alternativos. O cruzamento com a lista local do Scholar
recuperou um título ausente, ainda sem DOI nem passagem. A lista do Scholar
continua sendo uma entrada manual; não houve nova consulta autenticada ao Scholar.
A duplicata deliberadamente arquivada não foi reintroduzida.

## Leitura adicional e seu limite

`grains_007`, revisão em *Advances in Agriculture*, recebeu classificação a partir
da tabela de perdas qualitativas na [página integral da editora](https://onlinelibrary.wiley.com/doi/10.1155/aia/3910210).
A linha atribuída ao artigo auditado descreve preço por dano em hortaliças;
o artigo-fonte modela determinantes macroeconômicos de perdas quantitativas de grãos.
A atribuição foi codificada como `misrepresented` / `dead_end`, com passagem,
origem e hash em [classify.json](../../data/classify.json). A profundidade é
`supporting` porque o citante o emprega como evidência da síntese; não foi presumido
reuso metodológico nem de dados. Esta leitura ainda requer revisão independente.
O HTML completo da editora não foi persistido; a passagem curta e sua origem
foram preservadas. Isso não foi transformado em alegação de texto completo em disco.

A IRR continua referente ao pacote cego original. Seus coeficientes não devem
ser apresentados como validação das classificações adicionais.

## Resultados correntes

Má atribuição: {e["accuracy"]["misrepresented"]["ratio"]}, {e["accuracy"]["misrepresented"]["pct"]}.
Citação perfunctória: {e["perfunctorio"]["ratio"]}, {e["perfunctorio"]["pct"]}.
Trecho recuperado entre registros com quartil: {c["pct_trecho"]["ratio"]}, {c["pct_trecho"]["pct"]}.
Não se deve inferir qualidade de citação a partir do quartil: cobertura e acesso
continuam desiguais. Comparadores da literatura ainda assinalados como pendentes
não foram promovidos a evidência verificada.

## Grafos de disrupção e co-citação

{graphs}

Os arquivos de grafo preservam backend, pedidos de rede, falhas e referências
sem mapeamento. O método, as janelas e as sementes foram mantidos. CD e DI usam
variantes diferentes: discordância de sinal não sustenta veredito causal.

## Correções de engenharia

- Coleta incremental: preserva IDs, passagens, status terminal e registros antigos,
  inclusive quando uma base falha ou retorna menos resultados.
- Candidatos de múltiplas fontes são unidos antes do cruzamento com o inventário;
  títulos e DOI não são comparados antes de completar os metadados disponíveis.
- A triagem preserva IDs e arestas falsas; periódicos já conhecidos sobrevivem
  à indisponibilidade de endpoints.
- Resolução de DOI rejeita respostas sem título ou sem correspondência suficiente, evitando converter uma tese em projeto de pesquisa.
- IDs exclusivos do Scholar avançam a partir dos já usados; a derivação é idempotente.
- A data do relatório pertence ao snapshot, impedindo que o CI falhe só porque
  o verificador rodou em outro dia.
- O casamento Scimago prioriza ISSN-L e ordena os demais ISSNs: a ordem de um conjunto não pode mudar o quartil entre execuções.
- Os campos de sensibilidade e cruzamento do CD são exportados com seus nomes reais.

## Apresentação VITA

Figuras, diagramas do README, painel HTML e composição do PDF compartilham os
[tokens locais](../../tools/vita_tokens.json), fotografados do design global VITA.
Branco, cinza e preto organizam a leitura; rótulos, intensidade e marcadores
preservam as distinções. Terracota fica reservado a ações reais. Inter e JetBrains
Mono, sob OFL, mantêm a reprodução aberta; Optimistic VF não foi redistribuída.

## Pendências que permanecem

- Validar as afirmações dos artigos com o autor e concluir a codificação humana.
- Obter corpos integrais das leituras institucionais não persistidas.
- Verificar comparadores nas fontes primárias.
- Resolver referências sem correspondência entre bases e atualizar a lista manual
  do Scholar quando houver nova exportação.
"""


def render_readme(d):
    e = d["eixos"]["pooled"]
    c = d["cobertura_quartil"]["total"]
    pop = d["populacao"]
    cd = {p: d["cd"][p]["cd_index"]["windows"]["5"] for p in ("airline", "grains")}
    cm = d["cocitacao"]["periods"]["main"]

    def dec(v):
        return f"{v:.3f}".replace(".", ",")

    return f"""## §2 — Os achados

<!-- Gerado por tools/audit_83_review.py a partir de audit_70; não editar contagens à mão. -->
Cada número abaixo é impresso por `tools/audit_70_numbers.py`; o ponteiro indica
sua seção em `reports/01-impacto/numeros.txt`.

- **Inventário.** {d["inventario"]["total"]} registros, dos quais {d["inventario"]["com_doi"]["total"]} com DOI; {d["meta"]["n_classificados"]} têm classificação com passagem (`audit_70 §inventario`).
- **População.** {pop["total"]} citações: {pop["airline"]} de aviação e {pop["grains"]} de grãos; {pop["classificados_dentro_da_populacao"]["total"]} classificadas (`audit_70 §populacao`).
- **Cobertura.** Entre {c["total"]} registros com quartil oficial, {c["trecho"]} têm trecho literal, {c["fantasma"]} são só-bibliografia sob a classificação documentada, {c["aresta_falsa"]} é aresta falsa e {c["pendente"]} seguem sem evidência (`audit_70 §cobertura`). A auditoria de corpos em disco é mais estrita que essa classificação histórica.
- **Presença e profundidade.** Das {d["meta"]["n_classificados"]} leituras, {e["presence"]["in_text"]["n"]} mencionam o artigo no corpo; {e["perfunctorio"]["n"]} dessas menções são perfunctórias ({e["perfunctorio"]["pct"]}). Outras {e["depth"]["foundational"]["n"]} são fundacionais e {e["depth"]["supporting"]["n"]} sustentam argumento ou desenho (`audit_70 §eixos`).
- **Exatidão.** {e["accuracy"]["accurate"]["n"]} menções fiéis, {e["accuracy"]["imprecise"]["n"]} imprecisas e {e["accuracy"]["misrepresented"]["n"]} com má atribuição; estas representam {e["accuracy"]["misrepresented"]["pct"]} das menções no corpo (`audit_70 §eixos`).
- **Teste cego.** O κ de exatidão entre os codificadores cegos permanece em 0,60, contra 0,14 e 0,15 nos pares com o original (`audit_70 §irr`). É resultado da coorte original; não valida automaticamente a leitura adicional. O contraste sugere dependência do instrumento, mas não isola um efeito causal.
- **Afirmações.** O registro contém {d["alegacoes"]["total"]} afirmações verificáveis; {d["alegacoes"]["sustentadas"]} aparecem em citações mapeadas (`audit_70 §alegacoes`).
- **Antes e depois.** CD5: {dec(cd["airline"]["CD"])} em aviação e {dec(cd["grains"]["CD"])} em grãos; DI5: {dec(cd["airline"]["DI5"]["value"])} e {dec(cd["grains"]["DI5"]["value"])}, respectivamente (`audit_70 §cd`). A co-citação passa de {dec(cm["pre"]["share_AB"])} a {dec(cm["post"]["share_AB"])} entre os períodos do estudo (`audit_70 §cocitacao`). São medidas descritivas, sem atribuição causal ao artigo.

A [revisão da atualização](reports/01-impacto/revisao-atualizacao.md) registra
coleta, leitura adicional, valores anteriores corrigidos e limites da análise.
Os comparadores publicados continuam pendentes de verificação primária.

"""


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    output = render()
    d = json.loads((OUT.parent / "dados.json").read_text())
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text()
    start, end = readme.index("## §2 —"), readme.index("## §3 —")
    updated_readme = readme[:start] + render_readme(d) + readme[end:]
    if args.check:
        if not OUT.exists() or OUT.read_text() != output or readme != updated_readme:
            raise SystemExit("DRIFT: regenere audit_83_review.py")
        print("ok: revisão da atualização idêntica à gerada")
    else:
        OUT.write_text(output)
        readme_path.write_text(updated_readme)
        print(f"-> {OUT}")


if __name__ == "__main__":
    main()
