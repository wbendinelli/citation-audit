# Relatório técnico — inventário do impacto de dois artigos

Compilação (da raiz do repositório; as fontes vendorizadas são obrigatórias — sem
`--font-path` o Typst cai em outra família e a paginação muda):

```bash
typst compile --root . --font-path tools/fonts reports/01-impacto/main.typ reports/01-impacto/relatorio-impacto.pdf
```

Sequência de verificação antes de compilar:

```bash
python3 tools/audit_70_numbers.py --check      # dados.json e numeros.txt batem com data/
python3 tools/audit_81_figures.py --check      # PNGs byte-idênticos (venv 3.12, matplotlib pinado)
python3 tools/check_numbers.py --prose reports/01-impacto/main.typ --exempt reports/01-impacto/check_numbers_exempt.txt
```

O último comando tem de terminar em `MISS/SEM-PONTEIRO 0`: todo número da prosa aponta
`audit_70 §chave` para a seção de `numeros.txt` que o imprime. `check_numbers_exempt.txt`
vazio é resultado, não omissão.

Diagramas de mecanismo (`figuras.typ`) são Typst nativo, sem número dentro; figuras de
medida (`figuras/*.png`) saem de `tools/audit_81_figures.py` lendo só `dados.json`.
