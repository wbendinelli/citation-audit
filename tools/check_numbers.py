#!/usr/bin/env python3
"""check_numbers.py — teste de aceitação da regra dura do repositório:

    "Todo número citado na prosa é impresso por um script versionado."

Um número sem script que o imprima é bug: ou o número passa a ser gerado
(e cai em `reports/01-impacto/numeros.txt`), ou sai da prosa. Este script
varre um arquivo de prosa (o relatório em si, `reports/01-impacto/*.typ`)
atrás de tokens numéricos e verifica se cada um aparece no "palheiro" —
`reports/01-impacto/numeros.txt`, um arquivo de texto gerado e commitado,
dividido em seções.

Adaptação de `tools/check_numbers.py` do repositório `interpretable-ml-
-lectures`: lá o palheiro eram as saídas de célula de caderno Jupyter,
organizadas por módulo (`modules/NN-slug/notebooks/*.ipynb`) e apontadas
na prosa por "módulo 0N". Aqui não há cadernos — o pipeline
(`tools/audit_NN_*.py`) é script puro — então o palheiro é um único
arquivo de texto, `numeros.txt`, dividido em seções por uma linha

    == audit_NN §chave ==

Toda linha entre uma seção e a próxima pertence a ela. Uma seção nomeia o
script que a gerou (`audit_NN`, o mesmo prefixo de `tools/audit_NN_*.py`)
e uma chave livre (`§chave`) para quando um script imprime mais de um
grupo de números — ex. `audit_32 §funil` e `audit_41 §scimago`.

Ponteiro na prosa: um número só é conferido contra as seções que a prosa
aponta a até 2 linhas de distância, no mesmo formato da seção:

    #footnote[audit_32 §funil: contagem do portão 2]

Sem ponteiro por perto, o número não é procurado em lugar nenhum — é
SEM-PONTEIRO, não MISS: exigir o ponteiro impede que um valor que por
acaso bate com a seção errada passe como se fosse evidência. Com ponteiro
mas sem casar em nenhuma das seções apontadas, é MISS.

Vereditos: OK (casou numa seção apontada) · EXEMPT (token listado no
arquivo de isenções) · MISS (ponteiro presente, número ausente da seção)
· SEM-PONTEIRO (nenhum ponteiro a até 2 linhas). A linha-resumo final:

    prosa: N tokens, ok K, exempt E, MISS/SEM-PONTEIRO M

Formato do arquivo de isenções (uma decisão por linha, tabulação entre
campos, comentários com "#"):

    <token-cru><TAB><motivo>

Extração do palheiro: as mesmas duas convenções do repositório de origem
— inglês (ponto decimal, vírgula de milhar) e português (vírgula decimal,
ponto de milhar) — lidas ao mesmo tempo por `_core_readings()` /
`_iter_haystack_tokens()`, sem exigir que `numeros.txt` escolha uma.

Expansão de razão: um token `a/b` (dois inteiros separados por "/", sem
ser parte de uma data DD/MM/AAAA) também gera, como leitura adicional do
palheiro, o percentual `100*a/b` — não arredondado; é `match()` quem
arredonda para o que a prosa citar. Isso deixa "73/98 candidatos" no
palheiro cobrir tanto "74%" quanto "74,5%" na prosa, sem duplicar o
número em `numeros.txt` já formatado de duas maneiras.

O que este script NÃO cobre: inteiros soltos <= 12, anos 1900-2100, `§N`,
datas, URLs, código e matemática continuam excluídos da extração de
prosa (ver `extract_prose_tokens`), como no repositório de origem. Esses
números pequenos são responsabilidade de `tools/check_data.py`
(invariantes sobre `data/*.json`) e das tabelas geradas por
`reports/01-impacto/numeros.typ` — não deste checador de prosa, que
existe para números que só apareceriam impressos em texto corrido.

Uso:
    python3 tools/check_numbers.py --prose reports/01-impacto/main.typ \\
        --exempt reports/01-impacto/check_numbers_exempt.txt
    python3 tools/check_numbers.py --prose FILE [FILE ...] \\
        --haystack reports/01-impacto/numeros.txt
    python3 tools/check_numbers.py --self-test

Só stdlib, Python 3.10+. Rodado à mão — não é hook de pre-commit.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

# --------------------------------------------------------------------------
# Extração de tokens da prosa (.md / .typ) — INALTERADO em relação ao
# repositório de origem.
# --------------------------------------------------------------------------

# Token numérico em PT-BR: milhar separado por '.', decimal por ',' opcional.
_TOKEN_RE = re.compile(r"(?<![\w.,])(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d+))?")

_ISO_DATE_RE = re.compile(r"\b20\d\d-\d\d-\d\d\b")
_DMY_DATE_RE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")
_FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
_URL_RE = re.compile(r"https?://\S+")
_DISPLAY_MATH_RE = re.compile(r"\$\$.*?\$\$", re.DOTALL)
_INLINE_MATH_RE = re.compile(r"\$[^$\n]+\$")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
# Abreviação de intervalo de anos, ex. "2023–24": apaga o trecho INTEIRO
# (ano-prefixo + traço + sufixo de 2 dígitos) antes de tokenizar. Apagar só
# o ano-prefixo (casando pelo sufixo isolado, como _YEAR_RANGE_SUFFIX_RE
# fazia sozinho) deixaria o "24" solto, e a regex principal o pegaria como
# uma citação numérica espúria.
_YEAR_RANGE_RE = re.compile(r"\b(?:19|20)\d\d[–-]\d\d\b")
_YEAR_RANGE_SUFFIX_RE = re.compile(r"^[–-]\d\d(?!\d)")
_SECTION_MARK_RE = re.compile(r"§\s*\d+")
_CAP_MARK_RE = re.compile(r"\bcap\.\s*\d+", re.IGNORECASE)
_MIN_SUFFIX_RE = re.compile(r"^\s*min\b", re.IGNORECASE)


def _strip_noise(text: str) -> str:
    """Remove código (cercado/inline), URLs, matemática, comentários HTML e
    datas ISO/DMY antes de tokenizar. A numeração de heading é tratada por
    linha (ver _strip_heading_numbering) porque o resto do heading ainda
    deve ser varrido."""
    text = _FENCED_CODE_RE.sub(lambda m: " " * len(m.group(0)), text)
    text = _INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), text)
    text = _HTML_COMMENT_RE.sub(lambda m: " " * len(m.group(0)), text)
    text = _DISPLAY_MATH_RE.sub(lambda m: " " * len(m.group(0)), text)
    text = _INLINE_MATH_RE.sub(lambda m: " " * len(m.group(0)), text)
    text = _URL_RE.sub(lambda m: " " * len(m.group(0)), text)
    text = _ISO_DATE_RE.sub(lambda m: " " * len(m.group(0)), text)
    text = _DMY_DATE_RE.sub(lambda m: " " * len(m.group(0)), text)
    text = _YEAR_RANGE_RE.sub(lambda m: " " * len(m.group(0)), text)
    return text


@dataclass
class ProseToken:
    raw: str
    value: float
    decimals: int
    line_no: int  # 1-based
    line_text: str
    # Não usados nesta adaptação (existiam para o passe consultivo de
    # células markdown do repositório de origem, que não existe aqui) —
    # mantidos para que extract_prose_tokens permaneça byte-idêntica.
    near_module00_pointer: bool = False
    pointed: set = field(default_factory=set)


def _strip_heading_numbering(line: str) -> str:
    """Em linhas '^#{1,6} ', apaga só os dígitos de numeração de seção no
    início do texto do heading (ex.: '## 3.2 Foo' -> '## Foo'), mantendo
    o resto do heading intacto."""
    m = _HEADING_RE.match(line)
    if not m:
        return line
    hashes, rest = m.group(1), m.group(2)
    num_m = re.match(r"^[\d.\)]+(\s+)", rest)
    if num_m:
        rest = " " * len(num_m.group(0)) + rest[len(num_m.group(0)) :]
    return f"{hashes} {rest}"


def extract_prose_tokens(text: str) -> list[ProseToken]:
    """Extrai tokens numéricos em formato PT-BR do texto de prosa,
    aplicando as regras de exclusão (anos, inteiros pequenos, abreviação de
    intervalo de anos, marcadores de seção/capítulo, contagens de minuto)."""
    tokens: list[ProseToken] = []
    cleaned = _strip_noise(text)
    lines = cleaned.split("\n")
    for line_idx, line in enumerate(lines, start=1):
        proc_line = _strip_heading_numbering(line)
        for m in _TOKEN_RE.finditer(proc_line):
            raw = m.group(0)
            int_part = m.group(1)
            dec_part = m.group(2)

            # Pula tokens dentro de marcadores §N / cap. N.
            span_start, span_end = m.start(), m.end()
            skip = False
            for marker_re in (_SECTION_MARK_RE, _CAP_MARK_RE):
                for mm in marker_re.finditer(proc_line):
                    if mm.start() <= span_start < mm.end():
                        skip = True
                        break
                if skip:
                    break
            if skip:
                continue

            # Pula "\d+ min" (contagens de minuto, tipo tempo-percentual).
            after = proc_line[span_end:]
            if dec_part is None and _MIN_SUFFIX_RE.match(after):
                continue

            # Pula abreviação de intervalo de anos (token seguido de –NN
            # ou -NN, ex. 2023–24).
            if _YEAR_RANGE_SUFFIX_RE.match(after):
                continue

            # Normaliza o valor.
            int_clean = int_part.replace(".", "")
            if dec_part is not None:
                value = float(f"{int_clean}.{dec_part}")
                decimals = len(dec_part)
            else:
                value = float(int_clean)
                decimals = 0

            # Pula anos soltos 1900-2100 (só quando o token inteiro, sem
            # parte decimal, é um ano de 4 dígitos).
            if (
                dec_part is None
                and re.fullmatch(r"\d{4}", int_part)
                and 1900 <= value <= 2100
            ):
                continue

            # Pula inteiros soltos <= 12 (contagens de capítulo/seção) —
            # só se aplica a inteiros sem separador de milhar/decimal.
            if dec_part is None and "." not in int_part and value <= 12:
                continue

            tokens.append(ProseToken(raw, value, decimals, line_idx, line.rstrip("\n")))
    return tokens


# --------------------------------------------------------------------------
# Palheiro: números em reports/01-impacto/numeros.txt — INALTERADO em
# relação ao repositório de origem no núcleo de extração (_CORE_RE.. até
# _iter_haystack_tokens); o que muda é a fonte (um .txt seccionado, não
# saídas de célula de caderno) e mora mais abaixo, em load_haystack().
# --------------------------------------------------------------------------

# Núcleo de um token numérico: grupos de dígitos separados por '.' ou ',',
# em qualquer combinação — cobre tanto "1.282.970" / "0,7644" (PT) quanto
# "1,282,970" / "0.7644" (EN) no mesmo regex; a convenção é decidida
# depois, token a token, em _core_readings().
_CORE_RE = re.compile(r"-?\d+(?:[.,]\d+)*")
#  Usadas só com .match(text, pos) para casar exatamente a partir de uma
#  posição no meio da string — sem "^", que em modo não-MULTILINE âncora
#  no início absoluto da string (posição 0), não em `pos`.
_SCI_E_RE = re.compile(r"[eE][-+]?\d+")
_SUPERSCRIPT_TRANS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")
_SCI_UNI_RE = re.compile(r"\s*[×xX]\s*10\s*([⁻⁺⁰¹²³⁴⁵⁶⁷⁸⁹]+)")
_PERCENT_RE = re.compile(r"\s*%")


def _core_readings(core: str) -> list[float]:
    """Todas as leituras plausíveis de um núcleo "dígitos e separadores"
    (sem sinal, sem expoente, sem %), tentando as duas convenções:

        EN: vírgula de milhar, ponto decimal.
        PT: ponto de milhar, vírgula decimal.

    Um grupo de milhar tem SEMPRE 3 dígitos; é isso que desambigua "1.234"
    (um separador, grupo de 3 -> pode ser decimal OU milhar: as duas
    leituras voltam) de "0,7644" (um separador, grupo de 4 -> só decimal)
    e de "1.282.970" / "1,282,970" (2+ grupos, todos de 3 -> só milhar).
    "1.234,5" (separadores mistos, milhar seguido de decimal final) casa
    inequivocamente com 1234.5."""
    segs = re.split(r"([.,])", core)
    groups = segs[0::2]
    seps = segs[1::2]

    if not seps:
        return [float(core)]

    if len(seps) == 1:
        left, right = groups
        if len(right) == 3 and not left.lstrip("-").startswith("0"):
            # Ambíguo: decimal (leitura literal) ou grupo único de milhar.
            # "0,004" / "0.004" não é milhar de ninguém: só a leitura decimal.
            return [float(f"{left}.{right}"), float(left + right)]
        return [float(f"{left}.{right}")]

    # 2+ separadores.
    if len(set(seps)) == 1 and all(len(g) == 3 for g in groups[1:]):
        # Separador uniforme, todo grupo depois do primeiro com 3 dígitos:
        # milhar sem ambiguidade (PT ponto-milhar ou EN vírgula-milhar).
        return [float("".join(groups))]

    if (
        all(len(g) == 3 for g in groups[1:-1])
        and seps[:-1].count(seps[0]) == len(seps) - 1
    ):
        # Separadores mistos: grupos de milhar (3 dígitos) seguidos de um
        # grupo decimal final de tamanho livre, ex. "1.234,5" / "1,234.5".
        int_part = "".join(groups[:-1])
        return [float(f"{int_part}.{groups[-1]}")]

    # Não deveria ocorrer em texto bem formado; melhor esforço, tratando
    # todo separador como marca de milhar.
    return [float("".join(groups))]


@dataclass
class HaystackValue:
    value: float
    source: str  # evidência a exibir: "numeros.txt [§chave]"


def _iter_haystack_tokens(text: str):
    """Varre `text` da esquerda pra direita e gera (raw, [valores]) para
    cada token numérico — inclusive as leituras derivadas (mantissa de
    notação científica, leitura em fração de percentual, leitura em milhar
    de um grupo ambíguo). Consome o sufixo científico/percentual junto do
    núcleo para não deixar seus dígitos (o "10" do "×10⁻⁵", o "05" do
    "e-05") serem recasados como tokens à parte."""
    pos = 0
    for m in _CORE_RE.finditer(text):
        if m.start() < pos:
            continue
        core = m.group(0)
        end = m.end()
        raw_end = end

        sign = -1.0 if core.startswith("-") else 1.0
        body = core.removeprefix("-")
        readings = [sign * r for r in _core_readings(body)]

        exp = None
        sci_uni_m = _SCI_UNI_RE.match(text, end)
        if sci_uni_m:
            try:
                exp = int(sci_uni_m.group(1).translate(_SUPERSCRIPT_TRANS))
            except ValueError:
                exp = None
            else:
                raw_end = sci_uni_m.end()
        else:
            sci_e_m = _SCI_E_RE.match(text, end)
            if sci_e_m:
                exp = int(sci_e_m.group(0)[1:])
                raw_end = sci_e_m.end()

        is_percent = False
        pct_m = _PERCENT_RE.match(text, raw_end)
        if pct_m:
            is_percent = True
            raw_end = pct_m.end()

        values: list[float] = []
        if exp is not None:
            values.extend(r * (10.0**exp) for r in readings)
            values.extend(readings)  # mantissa preservada como leitura própria
        elif is_percent:
            for r in readings:
                values.append(r)
                values.append(r / 100.0)
        else:
            values.extend(readings)

        pos = raw_end
        yield text[m.start() : raw_end], values


# Razão inteira "a/b" (ex. "73/98"): reconhecida só quando não faz parte de
# uma data DD/MM/AAAA (que teria um segundo "/" colado — "12/05/2024" tem
# "/" logo depois de "05" e logo antes dele em "05/2024", o que os dois
# lookarounds abaixo recusam).
_RATIO_RE = re.compile(r"(?<![\d/])(\d{1,6})/(\d{1,6})(?![\d/])")


def _iter_ratio_tokens(text: str):
    """Gera (raw "a/b", leitura_percentual) para cada razão inteira a/b em
    `text`. A leitura devolvida é o percentual cru `100*a/b`, sem
    arredondar — quem arredonda é `match()`, para o número de casas que a
    prosa citar. Assim um único "73/98" em numeros.txt cobre tanto "74%"
    quanto "74,5%" na prosa, sem numeros.txt precisar imprimir as duas."""
    for m in _RATIO_RE.finditer(text):
        a, b = int(m.group(1)), int(m.group(2))
        if b == 0:
            continue
        yield m.group(0), 100.0 * a / b


# Uma seção do palheiro: "== audit_NN §chave ==", mesma gramática do
# ponteiro de prosa (_POINTER_RE, mais abaixo) fechada por "==" dos dois
# lados.
_SECTION_RE = re.compile(r"^==\s*(audit_\d\d)\s*§\s*([a-z][\w-]*)\s*==$")


def load_haystack(path: Path) -> dict[tuple[str, str], list[HaystackValue]]:
    """Lê `numeros.txt` e devolve {(audit_NN, chave): [HaystackValue, ...]}.

    Toda linha entre uma seção e a próxima alimenta a seção corrente: cada
    token numérico (via _iter_haystack_tokens) e cada razão a/b (via
    _iter_ratio_tokens) viram um HaystackValue com a mesma evidência,
    `numeros.txt [§chave]` — quem gerou o número (audit_NN) fica implícito
    no ponteiro que a prosa usou para chegar até aqui, não repetido na
    evidência. Linhas antes da primeira seção são ignoradas (comentário de
    cabeçalho do arquivo)."""
    haystack: dict[tuple[str, str], list[HaystackValue]] = {}
    if not path.exists():
        return haystack
    current: tuple[str, str] | None = None
    for line in path.read_text(encoding="utf-8").split("\n"):
        m = _SECTION_RE.match(line.strip())
        if m:
            current = (m.group(1), m.group(2))
            haystack.setdefault(current, [])
            continue
        if current is None:
            continue
        evidence = f"numeros.txt [§{current[1]}]"
        for _raw, readings in _iter_haystack_tokens(line):
            for v in readings:
                haystack[current].append(HaystackValue(abs(v), evidence))
        for _raw, pct_value in _iter_ratio_tokens(line):
            haystack[current].append(HaystackValue(pct_value, evidence))
    return haystack


# --------------------------------------------------------------------------
# Casamento — INALTERADO em relação ao repositório de origem.
# --------------------------------------------------------------------------


def _quantize_eq(o: float, v: float, d: int) -> bool:
    try:
        q = Decimal(str(o)).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP)
    except (ArithmeticError, ValueError):
        return False
    return q == Decimal(str(v))


def match(v: float, d: int, haystack: list[HaystackValue]) -> HaystackValue | None:
    """Devolve o primeiro valor do palheiro que casa com o token de prosa
    (v, d) sob alguma das regras 7-10, ou None."""
    for hv in haystack:
        o = hv.value
        # Regra 7: casamento por arredondamento.
        if _quantize_eq(o, v, d):
            return hv
        # Regra 8: idem com o*100 (prosa em %, célula em fração).
        if _quantize_eq(o * 100, v, d):
            return hv
        # Regra 9: folga de representação em ponto flutuante.
        if abs(o - v) <= 0.6 * (10**-d):
            return hv
        if abs(o * 100 - v) <= 0.6 * (10**-d):
            return hv
        # Regra 10: para d == 0, também casa por conversão para inteiro.
        if d == 0:
            try:
                if int(o) == int(v):
                    return hv
            except (ValueError, OverflowError):
                pass
            try:
                if int(o * 100) == int(v):
                    return hv
            except (ValueError, OverflowError):
                pass
    return None


# --------------------------------------------------------------------------
# Arquivo de isenções — INALTERADO em relação ao repositório de origem.
# --------------------------------------------------------------------------


def load_exemptions(path: Path) -> dict[str, str]:
    exemptions: dict[str, str] = {}
    if not path.exists():
        return exemptions
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t", 1)
        if len(parts) == 2:
            raw, reason = parts
        else:
            raw, reason = parts[0].strip(), ""
        exemptions[raw.strip()] = reason.strip()
    return exemptions


# --------------------------------------------------------------------------
# Ponteiro "audit_NN §chave" na prosa (substitui o "módulo 0N" da origem)
# --------------------------------------------------------------------------

_POINTER_RE = re.compile(r"\b(audit_\d\d)\s*§\s*([a-z][\w-]*)")


def pointed_sections(all_lines: list[str], line_no: int) -> set[tuple[str, str]]:
    """Pares (audit_NN, chave) apontados a +-2 linhas de line_no (1-based).
    Mesma janela do "módulo 0N" da origem (pointed_modules); a diferença é
    que aqui o ponteiro já nomeia a seção inteira, não só o módulo, então
    não há um segundo estágio de busca por módulo-inteiro."""
    lo = max(1, line_no - 2)
    hi = min(len(all_lines), line_no + 2)
    found: set[tuple[str, str]] = set()
    for i in range(lo, hi + 1):
        found.update(
            (mm.group(1), mm.group(2)) for mm in _POINTER_RE.finditer(all_lines[i - 1])
        )
    return found


def match_pointed(
    v: float,
    d: int,
    pointed: set[tuple[str, str]],
    haystack: dict[tuple[str, str], list[HaystackValue]],
) -> HaystackValue | None:
    """Busca só nas seções apontadas (ordem determinística por sort), nunca
    no palheiro inteiro — é isso que torna SEM-PONTEIRO possível: um valor
    que bate em alguma OUTRA seção não pontuada não conta como OK."""
    for key in sorted(pointed):
        hit = match(v, d, haystack.get(key, []))
        if hit is not None:
            return hit
    return None


# --------------------------------------------------------------------------
# .typ: tirar código de layout antes de tokenizar
# --------------------------------------------------------------------------

_TYP_NOISE = [
    re.compile(r"^\s*#(let|set|show|import|include)\b.*$", re.MULTILINE),
    re.compile(r'image\(\s*"[^"]*"[^)]*\)'),
    # json("...") — chamadas de carregamento de dados (numeros.typ:
    # `#let D = json("/reports/01-impacto/dados.json")`); o caminho entre
    # aspas pode conter dígitos (ex. "01-impacto") que não são prosa.
    re.compile(r'json\(\s*"[^"]*"[^)]*\)'),
    re.compile(
        r"\b(width|height|inset|gutter|columns|rows|size|stroke|radius|weight|"
        r"spacing|leading|above|below|x|y|dx|dy|scale|page|numbering)\s*:\s*[^,\])\n]+"
    ),
    re.compile(r"@[A-Za-z0-9_:.-]+"),  # citações e rótulos
    re.compile(r"<[A-Za-z0-9_:.-]+>"),  # labels
    # D.campo.sub_campo — acessos ao dicionário de dados carregado por
    # numeros.typ (`#let D = json(...)`), com uma eventual chamada final
    # tipo `.at(...)`. Sem isto, um nome de campo com dígito colado
    # (ex. `D.funil.top10`) não escaparia sozinho — a regra de "número
    # colado a letra" de _TOKEN_RE já cobre esse caso — mas um índice como
    # `D.funil.etapas.at(15)` escaparia, e este strip cobre os dois.
    re.compile(r"\bD(?:\.[A-Za-z_][\w-]*)+(?:\([^)]*\))?"),
]


def _strip_typ(text: str) -> str:
    """Tira do .typ o que é código, não prosa: chamadas de layout, argumentos
    numéricos (width: 100%), imagens, cargas de dados, citações, labels e
    acessos a D.campo.sub_campo."""
    for rx in _TYP_NOISE:
        text = rx.sub(" ", text)
    return text


# --------------------------------------------------------------------------
# Condutor
# --------------------------------------------------------------------------


@dataclass
class Row:
    line: int
    raw: str
    verdict: str
    evidence: str


def run_prose(files: list[Path], exempt_file: Path | None, haystack_path: Path) -> int:
    """Confere a prosa do relatório: cada token precisa de um ponteiro
    'audit_NN §chave' a até duas linhas, e só é buscado nas seções que esse
    ponteiro nomeia, dentro de `haystack_path` (reports/01-impacto/numeros.
    txt)."""
    exemptions = load_exemptions(exempt_file) if exempt_file else {}
    haystack = load_haystack(haystack_path)
    total = miss = ok = ex = 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".typ":
            text = _strip_typ(text)
        all_lines = text.split("\n")
        rows: list[Row] = []
        for tok in extract_prose_tokens(text):
            total += 1
            if tok.raw in exemptions:
                rows.append(Row(tok.line_no, tok.raw, "EXEMPT", exemptions[tok.raw]))
                ex += 1
                continue
            pointed = pointed_sections(all_lines, tok.line_no)
            hit = (
                match_pointed(tok.value, tok.decimals, pointed, haystack)
                if pointed
                else None
            )
            if hit is not None:
                rows.append(Row(tok.line_no, tok.raw, "OK", hit.source))
                ok += 1
            else:
                verdict = "MISS" if pointed else "SEM-PONTEIRO"
                rows.append(Row(tok.line_no, tok.raw, verdict, ""))
                miss += 1
        print(f"== {path} ==")
        print(f"{'line':>5}  {'raw':<12} {'verdict':<14} evidence")
        for r in rows:
            if r.verdict != "OK":
                print(f"{r.line:>5}  {r.raw:<12} {r.verdict:<14} {r.evidence}")
    print(f"\nprosa: {total} tokens, ok {ok}, exempt {ex}, MISS/SEM-PONTEIRO {miss}")
    return 1 if miss > 0 else 0


# --------------------------------------------------------------------------
# --self-test: casos unitários embutidos, sem infraestrutura de testes
# --------------------------------------------------------------------------


def _self_test() -> int:
    checks = 0

    def check(cond: bool, msg: str) -> None:
        nonlocal checks
        assert cond, f"self-test falhou: {msg}"
        checks += 1

    # -- _core_readings: as duas convenções, ponto a ponto com o docstring --
    check(_core_readings("1.282.970") == [1282970.0], "milhar PT (2+ grupos de ponto)")
    check(
        _core_readings("1,282,970") == [1282970.0], "milhar EN (2+ grupos de vírgula)"
    )
    check(_core_readings("0,7644") == [0.7644], "decimal PT (vírgula, grupo != 3)")
    check(_core_readings("0.7644") == [0.7644], "decimal EN (ponto, grupo != 3)")
    check(_core_readings("1.234,5") == [1234.5], "PT completo: milhar + decimal")
    check(_core_readings("1,234.5") == [1234.5], "EN completo: milhar + decimal")
    check(
        set(_core_readings("1.234")) == {1.234, 1234.0},
        "grupo único ambíguo de 3 dígitos gera as duas leituras",
    )

    # -- _iter_haystack_tokens: percentual e notação científica --
    tokens = dict(_iter_haystack_tokens("taxa 37,3% de acerto"))
    check("37,3%" in tokens, "token percentual capturado por inteiro (com o %)")
    check(
        37.3 in tokens["37,3%"]
        and abs(0.373 - min(tokens["37,3%"], key=lambda x: abs(x - 0.373))) < 1e-9,
        "percentual guarda o valor citado e a fração (/100)",
    )
    sci_uni = dict(_iter_haystack_tokens("p-valor 1,05×10⁻⁵ significativo"))
    check(
        "1,05×10⁻⁵" in sci_uni, "notação científica unicode consumida como um só token"
    )

    # -- expansão de razão a/b --
    ratio_tokens = dict(_iter_ratio_tokens("Conversão: 73/98 candidatos."))
    check("73/98" in ratio_tokens, "razão a/b reconhecida como token do palheiro")
    check(
        abs(ratio_tokens["73/98"] - (100.0 * 73 / 98)) < 1e-9,
        "73/98 gera a leitura percentual 74,4897...%",
    )
    check(
        not dict(_iter_ratio_tokens("Internado em 12/05/2024, teve alta.")),
        "data DD/MM/AAAA não vira razão (dois separadores '/' consecutivos)",
    )

    import contextlib
    import io
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)

        haystack_path = tdp / "numeros.txt"
        haystack_path.write_text(
            "== audit_70 §funil ==\n"
            "73 candidatos avançaram de um total de 98 (73/98).\n"
            "\n"
            "== audit_71 §outra ==\n"
            "Nada relevante aqui: 5000.\n",
            encoding="utf-8",
        )
        haystack = load_haystack(haystack_path)
        check(("audit_70", "funil") in haystack, "seção audit_70 §funil carregada")
        check(("audit_71", "outra") in haystack, "segunda seção carregada")
        check(
            any(abs(hv.value - 73.0) < 1e-9 for hv in haystack[("audit_70", "funil")]),
            "73 está entre os valores da seção funil",
        )

        # -- OK: número citado perto de #footnote[audit_70 §funil: ...] --
        prose_ok = (
            "Texto de exemplo.\n"
            "Conforme #footnote[audit_70 §funil: metodologia] apurado, "
            "73 candidatos avançaram.\n"
        )
        prose_ok_lines = prose_ok.split("\n")
        tok73 = next(t for t in extract_prose_tokens(prose_ok) if t.raw == "73")
        pointed_73 = pointed_sections(prose_ok_lines, tok73.line_no)
        check(
            ("audit_70", "funil") in pointed_73,
            "ponteiro 'audit_70 §funil' reconhecido a +-2 linhas do número",
        )
        hit_73 = match_pointed(tok73.value, tok73.decimals, pointed_73, haystack)
        check(hit_73 is not None, "OK: 73 casa com a seção apontada")
        check(
            hit_73.source == "numeros.txt [§funil]",
            "evidência no formato numeros.txt [§chave]",
        )

        # -- MISS: mesmo ponteiro, número ausente da seção apontada --
        prose_miss = (
            "Conforme #footnote[audit_70 §funil: metodologia] apurado, "
            "999 candidatos avançaram.\n"
        )
        tok999 = next(t for t in extract_prose_tokens(prose_miss) if t.raw == "999")
        pointed_999 = pointed_sections(prose_miss.split("\n"), tok999.line_no)
        hit_999 = match_pointed(tok999.value, tok999.decimals, pointed_999, haystack)
        check(
            bool(pointed_999) and hit_999 is None,
            "MISS: 999 tem ponteiro mas não casa em nenhuma seção apontada",
        )

        # -- SEM-PONTEIRO: número sem nenhum ponteiro por perto --
        prose_semponteiro = (
            "Um total de 4200 candidatos, sem ponteiro nas redondezas.\n"
        )
        tok4200 = next(
            t for t in extract_prose_tokens(prose_semponteiro) if t.raw == "4200"
        )
        pointed_4200 = pointed_sections(prose_semponteiro.split("\n"), tok4200.line_no)
        check(not pointed_4200, "SEM-PONTEIRO: nenhum 'audit_NN §chave' a +-2 linhas")

        # -- DOI em crase não tokeniza (via _strip_noise / _INLINE_CODE_RE) --
        prose_doi = "O DOI é `10.1234/abcd.5678`, não um número de prosa.\n"
        check(
            not extract_prose_tokens(prose_doi),
            "DOI dentro de crase não gera token (inline code stripado)",
        )

        # -- D.campo.sub_campo não tokeniza depois de _strip_typ --
        prose_d = "Conforme D.funil.airline, revisamos o funil inteiro.\n"
        check(
            not extract_prose_tokens(_strip_typ(prose_d)),
            "D.funil.airline não tokeniza depois de _strip_typ",
        )
        prose_d_idx = "Olhe D.funil.etapas.at(15) para o detalhe do portão.\n"
        check(
            not extract_prose_tokens(_strip_typ(prose_d_idx)),
            "D.funil.etapas.at(15) (índice) também não tokeniza",
        )

        # -- json("...") não tokeniza mesmo com dígitos no caminho --
        prose_json = '#let D = json("/reports/01-impacto/dados_9401.json")\n'
        check(
            not extract_prose_tokens(_strip_typ(prose_json)),
            'json("...") não tokeniza mesmo com dígitos no caminho',
        )

        # -- expansão de razão, fim a fim: "74%" na prosa bate com "73/98" --
        prose_ratio = (
            "A conversão #footnote[audit_70 §funil: ver detalhe] foi de 74%.\n"
        )
        tok74 = next(t for t in extract_prose_tokens(prose_ratio) if t.raw == "74")
        pointed_74 = pointed_sections(prose_ratio.split("\n"), tok74.line_no)
        hit_74 = match_pointed(tok74.value, tok74.decimals, pointed_74, haystack)
        check(hit_74 is not None, "74% casa com a leitura percentual de 73/98")
        check(
            abs(hit_74.value - (100.0 * 73 / 98)) < 1e-9,
            "o valor batido é mesmo a leitura percentual da razão 73/98",
        )

        # -- load_exemptions: formato <token>\t<motivo> --
        exempt_path = tdp / "exempt.txt"
        exempt_path.write_text(
            "# comentário ignorado\n4200\tvalor de configuração, decidido alhures\n",
            encoding="utf-8",
        )
        exemptions = load_exemptions(exempt_path)
        check(
            exemptions.get("4200") == "valor de configuração, decidido alhures",
            "load_exemptions lê <token>\\t<motivo> e ignora comentários",
        )

        # -- fim a fim via run_prose(): tabela + linha-resumo. Parágrafos
        # separados por linha em branco de propósito: a janela de +-2
        # linhas do ponteiro não pode alcançar o parágrafo do "8100" (a
        # linha do ponteiro mais próxima fica a 3 linhas de distância),
        # ou o SEM-PONTEIRO desta fixture viraria MISS por acidente.
        prose_path = tdp / "main_selftest.typ"
        prose_path.write_text(
            "Conforme #footnote[audit_70 §funil: contagem] apurado, 73 candidatos\n"
            "avançaram, uma conversão de 74%.\n"
            "\n"
            "O mesmo #footnote[audit_70 §funil: não bate] ponteiro também cobre 999,\n"
            "que a seção não contém.\n"
            "\n"
            "Um total de 8100 candidatos aparece bem longe de qualquer ponteiro,\n"
            "sem nenhum apontamento nas redondezas deste parágrafo.\n",
            encoding="utf-8",
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = run_prose([prose_path], exempt_path, haystack_path)
        out = buf.getvalue()
        check(rc == 1, "run_prose sai com código 1 quando há MISS ou SEM-PONTEIRO")
        check("MISS" in out, "MISS aparece na tabela impressa")
        check("SEM-PONTEIRO" in out, "SEM-PONTEIRO aparece na tabela impressa")
        check(
            "prosa: 4 tokens, ok 2, exempt 0, MISS/SEM-PONTEIRO 2" in out,
            "linha-resumo no formato 'prosa: N tokens, ok K, exempt E, MISS/SEM-PONTEIRO M'",
        )

    # -- extract_prose_tokens: regras de exclusão continuam valendo --
    toks = extract_prose_tokens("Em 2024 o capítulo 3 media 0,7644 e ainda 2023–24.")
    raws = {t.raw for t in toks}
    check("2024" not in raws, "ano solto continua excluído")
    check("3" not in raws, "inteiro <= 12 continua excluído")
    check("0,7644" in raws, "decimal PT continua extraído")
    check("24" not in raws, "sufixo de intervalo de anos continua excluído")

    print(f"self-test: {checks} verificações passaram")
    return 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--prose",
        nargs="+",
        type=Path,
        default=None,
        help="arquivo(s) de prosa do relatório (.typ/.md): todo número precisa de "
        "um ponteiro 'audit_NN §chave' por perto e é conferido só contra as "
        "seções apontadas em --haystack",
    )
    parser.add_argument(
        "--exempt",
        type=Path,
        default=None,
        help="arquivo de isenções, formato '<token>\\t<motivo>' por linha",
    )
    parser.add_argument(
        "--haystack",
        type=Path,
        default=Path("reports/01-impacto/numeros.txt"),
        help="palheiro seccionado (default: reports/01-impacto/numeros.txt)",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv[1:])

    if args.self_test:
        return _self_test()

    if not args.prose:
        print(
            "error: informe --prose FILE [FILE ...] (ou use --self-test)",
            file=sys.stderr,
        )
        return 2

    return run_prose(args.prose, args.exempt, args.haystack)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
