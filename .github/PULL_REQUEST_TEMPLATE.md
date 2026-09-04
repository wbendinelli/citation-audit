## O que este PR muda

<!-- Uma ou duas frases. -->

## Tipo

<!-- Um de: correção / classificação nova / réplica / documentação / infra -->

## De onde vêm os números

<!-- Obrigatório quando um número em prosa muda: para cada número alterado,
     o script que o imprime. O condicionamento (amostra, escopo, data) vai
     na própria prosa. Apague esta seção se nenhum número muda. -->

## Checklist

- [ ] Rodei o bloco B (derivação offline, `tools/README.md#como-rodar`) antes de commitar, se toquei `tools/` ou `data/`
- [ ] `pre-commit run --all-files` passou
- [ ] Toda classificação nova em `data/classify.json` carrega passagem literal + `prov` completo
- [ ] Se um valor foi corrigido, o valor antigo fica registrado na nota, não apagado
- [ ] Nenhum arquivo de `text/` ou `pdf/` foi commitado
- [ ] Links resolvem

---

*Se este PR corrige uma citação mal classificada, diga isso no título — é a contribuição que mais vale.*
