Research complete. Here is the structured report.

---

# Methods for evaluating scholarly contribution via citing full texts

**Scope note.** Everything below is from published sources located this session; items I could not verify to a primary source are flagged inline and collected in §6. Where a figure comes from a secondary source (a review or survey quoting the original), I say so.

---

## 1. Citation function / citation context taxonomies

### 1.1 The canonical schemes

**Moravcsik, M. J. & Murugesan, P. (1975), "Some Results on the Function and Quality of Citations", *Social Studies of Science* 5(1), 86–92.** [DOI 10.1177/030631277500500106](https://journals.sagepub.com/doi/10.1177/030631277500500106)

Four *binary* dimensions, coded independently (not a single 8-way nominal scale):

| Dimension | Poles | Reads as |
|---|---|---|
| Conceptual / Operational | theory used vs. technique used | *what* is borrowed |
| Organic / Perfunctory | needed to understand the citing paper vs. general acknowledgement | **depth of dependence** |
| Evolutionary / Juxtapositional | citing work builds on it vs. offers an alternative | lineage vs. rivalry |
| Confirmative / Negational | findings accepted vs. disputed | **stance** |

Headline base rate: **41% of citations coded perfunctory**, which is the origin of the "citation counts overstate influence" argument. (Dimension list verified via Teufel et al. 2006 and the citation-function survey literature rather than the 1975 original, which is paywalled.)

**Teufel, S., Siddharthan, A. & Tidhar, D. (2006), "An annotation scheme for citation function", *Proc. 7th SIGdial Workshop*, 80–87.** [ACL W06-1312](https://aclanthology.org/W06-1312/) — and the companion **"Automatic classification of citation function", *EMNLP 2006*, 103–110.** [ACL W06-1613](https://aclanthology.org/W06-1613/)

12 mutually exclusive classes:

- `Weak` — weakness of the cited approach
- `CoCoGM` — contrast/comparison in goals or methods (neutral)
- `CoCo-` — citing author's work stated to be superior
- `CoCoR0` — contrast/comparison in results (neutral)
- `CoCoXY` — contrast between two *other* cited works
- `PBas` — cited work used as **basis or starting point**
- `PUse` — uses tools/algorithms/data/definitions
- `PModi` — adapts or modifies tools/algorithms/data
- `PMot` — positive about the approach; motivates the citing work
- `PSim` — citing and cited work are similar
- `PSup` — mutually compatible / supportive
- `Neut` — neutral description, or insufficient textual evidence

Collapsed polarity: Positive = {PMot, PUse, PBas, PModi, PSim, PSup}; Negative = {Weak, CoCo-}; Neutral = {CoCoGM, CoCoR0, CoCoXY, Neut}. **Human κ = 0.72**; **>60% of citations fall in `Neut`**; automatic 3-way (Weak/Positive/Neutral) classification reached κ = 0.58, accuracy 0.83. Corpus: 116 ACL Anthology articles.

**Jurgens, D., Kumar, S., Hoover, R., McFarland, D. & Jurafsky, D. (2018), "Measuring the Evolution of a Scientific Field through Citation Frames", *TACL* 6, 391–406.** [ACL Q18-1028](https://aclanthology.org/Q18-1028/) · [project page](https://jurgens.people.si.umich.edu/citation-function/) · [code/data](https://github.com/davidjurgens/citation-function)

Six "citation frames", a deliberate coarsening of Teufel: **Background, Motivation, Uses, Extension, Comparison or Contrast, Future Work.** The released ACL-ARC dataset is **1,941 citation instances from 186 papers**; they also republish Teufel (2010) data mapped into this scheme. Substantive finding: as NLP matured, authors shifted from *comparing* to merely *acknowledging as background*.

**Cohan, A., Ammar, W., van Zuylen, M. & Cady, F. (2019), "Structural Scaffolds for Citation Intent Classification in Scientific Publications", *NAACL-HLT 2019*, 3586–3596.** [ACL N19-1361](https://aclanthology.org/N19-1361/) · [arXiv:1904.01608](https://arxiv.org/abs/1904.01608) · [code](https://github.com/allenai/scicite) · [data](https://huggingface.co/datasets/allenai/scicite)

**SciCite**: three classes — **Background, Method, Result Comparison** — **11,020 instances**, multi-domain (computer science + medicine, from the Semantic Scholar corpus). Reported class distribution ≈ Background 58% / Method 29% / Result comparison 13%. Auxiliary "scaffold" tasks: section title prediction and citation-worthiness. This is the scheme behind Semantic Scholar's displayed citation intents.

**Valenzuela, M., Ha, P. & Etzioni, O. (2015), "Identifying Meaningful Citations", *AAAI-15 Workshop on Scholarly Big Data*.** [Semantic Scholar record](https://www.semanticscholar.org/paper/Identifying-Meaningful-Citations-Valenzuela-Escarcega-Ha/1c7be3fc28296a97607d426f9168ad4836407e4b)

The only genuinely **ordinal importance** scheme in this list. Annotated **465 ACL citation pairs**; modelled at two granularities — a coarse binary (*important* vs *incidental*) and a finer 4-level importance scale. Operational rule: citations that **use** or **extend** the cited work = important; citations in a related-work list or used only for comparison = incidental. **Only 14.6% coded important.** This classifier is the basis of Semantic Scholar's "**Highly Influential Citations**" flag (`isInfluential` in the API).

Related and useful if you want a second ordinal anchor: **Zhu, X., Turney, P., Lemire, D. & Vellino, A. (2015), "Measuring academic influence: Not all citations are equal", *JASIST* 66(2), 408–427.** [DOI 10.1002/asi.23179](https://asistdl.onlinelibrary.wiley.com/doi/10.1002/asi.23179) · [preprint](https://arxiv.org/pdf/1501.06587) — identifies the subset of references with central academic influence, validated against author self-report.

**Shotton, D. (2010), "CiTO, the Citation Typing Ontology", *Journal of Biomedical Semantics* 1(Suppl 1):S6.** [DOI 10.1186/2041-1480-1-S1-S6](https://jbiomedsem.biomedcentral.com/articles/10.1186/2041-1480-1-S1-S6) · [current spec](https://sparontologies.github.io/cito/current/cito.html) · [GitHub](https://github.com/SPAROntologies/cito)

An OWL ontology, not a coding scheme: one root property `cito:cites` with ~40 sub-properties, split into **factual** (what the citing paper did) and **rhetorical** (attitude). Current spec is **v2.9.0 (2026-09-03)**. Representative properties by stance:

- *Positive*: `citesAsAuthority`, `citesAsEvidence`, `citesAsDataSource`, `usesMethodIn`, `usesDataFrom`, `usesConclusionsFrom`, `extends`, `confirms`, `supports`, `givesSupportTo`, `obtainsSupportFrom`, `agreesWith`, `credits`
- *Neutral*: `citesAsRelated`, `citesForInformation`, `discusses`, `describes`, `includesQuotationFrom`, `containsAssertionFrom`, `qualifies`, `updates`, `speculatesOn`
- *Negative*: `disagreesWith`, `disputes`, `critiques`, `corrects`, `refutes`, `derides`, `ridicules`, `retracts`, `plagiarizes`

CiTO's value for you is as a **controlled vocabulary to publish your codes in**, not as a taxonomy to code with (it is too fine-grained and non-exclusive for reliable manual annotation).

**Stance at scale — the operational standard:** **Nicholson, J. M. et al. (2021), "scite: A smart citation index that displays the context of citations and classifies their intent using deep learning", *Quantitative Science Studies* 2(3), 882–898.** [DOI 10.1162/qss_a_00146](https://direct.mit.edu/qss/article/2/3/882/102990) — three-way **supporting / mentioning / contrasting** over 1.4B+ citation statements. Independent evaluation found a strong bias toward "mentioning": of 96 statements scite labelled *mentioning*, human assessors reclassified 40 as *supporting* and 17 as *contrasting*. Treat scite labels as a noisy prior, not ground truth.

**Sentiment corpus:** **Athar, A. (2011), "Sentiment Analysis of Citations using Sentence Structure-Based Features", *ACL 2011 Student Session*, 81–87.** [ACL P11-3015](https://aclanthology.org/P11-3015/) — 8,736 annotated citations; class balance in the test portion: **244 negative, 743 positive, 6,277 objective/neutral** (i.e. ~2.8% negative). See also Athar & Teufel (2012), "Context-Enhanced Citation Sentiment Detection", *NAACL 2012*. [PDF](https://aclanthology.org/anthology-files/pdf/N/N12/N12-1073.pdf)

### 1.2 The reviews

**Bornmann, L. & Daniel, H.-D. (2008), "What do citation counts measure? A review of studies on citing behavior", *Journal of Documentation* 64(1), 45–80.** [DOI 10.1108/00220410810844150](https://www.emerald.com/jd/article/64/1/45/222089/What-do-citation-counts-measure-A-review-of)
Narrative review of ~30 empirical studies of citing behaviour from the early 1960s to mid-2005. Conclusion: citing is not motivated solely by acknowledgement of intellectual influence; non-scientific factors are demonstrably present.

**Tahamtan, I. & Bornmann, L. (2019), "What do citation counts measure? An updated review of studies on citations in scientific documents published between 2006 and 2018", *Scientometrics* 121, 1635–1684.** [DOI 10.1007/s11192-019-03243-4](https://link.springer.com/article/10.1007/s11192-019-03243-4) · [arXiv:1906.04588](https://arxiv.org/abs/1906.04588) — 41 further studies; the natural companion for a modern methods section.

**Kunnath, S. N. et al. (2021), "A meta-analysis of semantic classification of citations", *Quantitative Science Studies* 2(4), 1170–1215.** [DOI 10.1162/qss_a_00159](https://direct.mit.edu/qss/article/2/4/1170/107610) · [open-access PDF](https://oro.open.ac.uk/79616/15/qss_a_00159.pdf) — the single best crosswalk between all the schemes above; cite this for your mapping table.

### 1.3 Which scheme is closest to your 7-level role scale + stance?

**None of them, and that is the important finding.** Your instrument is conflating three logically orthogonal axes that the literature keeps separate:

| Your construct | Axis type | Closest published anchor |
|---|---|---|
| drive-by → brief → real → supporting → foundational | **ordinal depth of dependence** | **Valenzuela et al. (2015)** ordinal importance (the only ordinal scale); backed by Moravcsik's **organic/perfunctory** and **evolutionary/juxtapositional** dimensions |
| supporting / contradictory / none | **nominal stance** | Moravcsik **confirmative/negational**; Teufel polarity collapse; scite supporting/contrasting/mentioning; CiTO rhetorical positives vs negatives |
| wrongly-interpreted | **accuracy / veridicality** | *Not in any citation-function scheme.* It lives in the quotation-error literature (§5) and in Greenberg's "invention" subtypes (§4) |

Recommended crosswalk if you want your results comparable to published base rates:

| Your level | Teufel 2006 | Jurgens 2018 | SciCite | Valenzuela | CiTO |
|---|---|---|---|---|---|
| drive-by (ghost-adjacent) | `Neut` | Background | Background | incidental (0) | `citesAsRelated`, `citesForInformation` |
| brief | `PMot`, `Neut` | Background / Motivation | Background | incidental (0–1) | `citesAsAuthority` |
| real (uses something) | `PUse` | Uses | Method | important (2) | `usesMethodIn`, `usesDataFrom`, `citesAsDataSource` |
| supporting (corroborates results) | `PSup`, `CoCoR0` | Comparison or Contrast | Result comparison | important (2) | `confirms`, `supports`, `citesAsEvidence` |
| foundational | `PBas`, `PModi` | Extension / Motivation | — | important (3) | `extends`, `obtainsBackgroundFrom` |
| wrongly-interpreted | — | — | — | — | (no property; see §4–5) |

**Practical consequences.** (a) Report the three axes separately and cross-tabulate; a single 7-value nominal variable will destroy ordinality and inflate the number of sparse cells in your agreement statistics. (b) Because your top levels are ordinal, use **Krippendorff's α (ordinal)** or **quadratic-weighted κ** for the role scale and plain Cohen's κ only for the stance and accuracy flags. (c) Publish the crosswalk table above so your rates can be compared against Teufel's >60% `Neut`, SciCite's 58% Background, Moravcsik's 41% perfunctory, and Valenzuela's 14.6% important.

**Computability from free sources.** Citation *function* requires the citing paper's full text, so it is **not** computable from OpenAlex or Crossref, which carry no citation contexts. Free routes: **Semantic Scholar Academic Graph API** (`/graph/v1/paper/{id}/citations?fields=contexts,intents,isInfluential`) gives you snippets plus SciCite intents plus the Valenzuela-derived influence flag for free with an API key — this is the only free source that hands you contexts + intents + an influence flag together. Otherwise you need full text from PubMed Central OA, arXiv, CORE, or Unpaywall PDFs. **For economics and transport journals this is the binding constraint**: OA full-text coverage is far worse than in biomedicine, so expect systematic non-random missingness in your ~104 passages (see §5 on why this contaminates a "ghost citation" rate).

---

## 2. Disruption vs consolidation: the CD / disruption index

### 2.1 Canonical references

- **Funk, R. J. & Owen-Smith, J. (2017), "A Dynamic Network Measure of Technological Change", *Management Science* 63(3), 791–817.** [DOI 10.1287/mnsc.2015.2366](https://pubsonline.informs.org/doi/10.1287/mnsc.2015.2366) · [author PDF](https://public.websites.umich.edu/~jdos/papers/A_Dynamic_Network_Measure_of_Technological_Change.pdf) — the CD index, on patents.
- **Wu, L., Wang, D. & Evans, J. A. (2019), "Large teams develop and small teams disrupt science and technology", *Nature* 566, 378–382.** [DOI 10.1038/s41586-019-0941-9](https://www.nature.com/articles/s41586-019-0941-9) — ports it to papers; 65M+ papers, patents and software, 1954–2014.
- **Park, M., Leahey, E. & Funk, R. J. (2023), "Papers and patents are becoming less disruptive over time", *Nature* 613, 138–144.** [DOI 10.1038/s41586-022-05543-x](https://www.nature.com/articles/s41586-022-05543-x) — 45M papers, 3.9M patents; uses **CD5** (5-year forward citation window).

### 2.2 The formula

Let $p$ be the focal paper, $R(p)$ its reference set, and $F_t(p)$ the set of works published within $t$ years of $p$ that cite $p$ and/or any $r \in R(p)$. Partition $F_t$:

- $n_i$ — cite $p$ **but not** any $r \in R(p)$ *(the focal work eclipses its own antecedents)*
- $n_j$ — cite $p$ **and** at least one $r \in R(p)$ *(the focal work is absorbed alongside its antecedents)*
- $n_k$ — cite at least one $r \in R(p)$ **but not** $p$ *(the antecedents live on independently)*

$$\mathrm{CD}_t \;=\; \frac{n_i - n_j}{\,n_i + n_j + n_k\,}$$

Funk & Owen-Smith's original weighted form is $\mathrm{CD}_t = \frac{1}{n}\sum_i \frac{-2 f_i b_i + f_i}{w_i}$, which reduces to the counting expression above when all weights $w_i = 1$.

**Interpretation on [−1, +1].** $+1$ = fully **disruptive/destabilising**: every subsequent work cites $p$ alone and ignores its predecessors. $-1$ = fully **consolidating/developing**: every subsequent work that touches this neighbourhood cites $p$ together with its references ($n_i = n_k = 0$). $0$ = neutral. In practice **$n_k$ dominates the denominator**, so empirical distributions are tightly compressed around 0 — this is the single biggest practical gotcha.

### 2.3 Variants you should report

| Variant | Definition | Source |
|---|---|---|
| **DI1 / CD** | as above; a single shared reference puts a citer in $n_j$ | Wu et al. (2019) |
| **DI5** | a citer counts toward $n_j$ only if it cites **≥ 5** of $p$'s references; otherwise it counts toward $n_i$. Reduces the randomness of weak bibliographic couplings and shows better convergent validity than DI1 | Bornmann, Devarakonda, Tekles & Chacko (2020), [DOI 10.1162/qss_a_00068](https://direct.mit.edu/qss/article/1/3/1242/96102) · [preprint arXiv:1911.08775](https://arxiv.org/abs/1911.08775) |
| **DI_nok / mCD** | drops $n_k$: $(n_i - n_j)/(n_i + n_j)$. Removes the compression toward zero | Wu, Q. & Yan, Z. (2019), "Solo citations, duet citations, and prelude citations", [arXiv:1905.03461](https://arxiv.org/abs/1905.03461) |
| **DEP** | a "dependency" indicator reported alongside DI5 in Bornmann et al. (2020) — **exact definition unverified, see §6** | ibid. |
| **CD5** | DI1 with a fixed 5-year forward citation window; the Park et al. (2023) workhorse | Park et al. (2023) |

### 2.4 Computing it from OpenAlex

Fully computable, and this is the free-source sweet spot.

1. Get $R(p)$ from the focal work's **`referenced_works`** array ([Work object docs](https://github.com/ourresearch/openalex-docs/blob/main/api-entities/works/work-object/README.md)).
2. Get citers of $p$ with **`?filter=cites:W<id>`**, which returns works having $p$ in their `referenced_works` ([filter docs](https://github.com/ourresearch/openalex-docs/blob/main/api-entities/works/filter-works.md)). Note OpenAlex warns that this count can exceed `cited_by_count` due to update lag.
3. For each citer, intersect its `referenced_works` with $R(p)$ → split into $n_i$ / $n_j$.
4. For $n_k$: run `cites:` for **each** $r \in R(p)$, union the results, subtract the citers of $p$. Then apply the publication-year window. This step is the expensive one; for a reference list of size $|R|$ with heavily-cited references it can be millions of records — use the OpenAlex snapshot rather than the API if $|R|$ is large or references are classics.
5. Window on `publication_year` (whole years, per the convention in the Park et al. line of work).

Caveats specific to OpenAlex: reference coverage is incomplete and non-random. OpenAlex's own help note ["The reference counts in OpenAlex seem off. Why is that?"](https://help.openalex.org/hc/en-us/articles/27810109633943-The-reference-counts-in-OpenAlex-seem-off-Why-is-that) lists un-indexed works, missing Crossref reference deposits, and DOI-less matching failures. Crossref reference availability depends on each member's deposit and open-reference settings, so Crossref-only reconstruction understates $R(p)$ for some publishers. See **Culbert, J. et al. (2025), "Reference coverage analysis of OpenAlex compared to Web of Science and Scopus", *Scientometrics*** [DOI 10.1007/s11192-025-05293-3](https://link.springer.com/article/10.1007/s11192-025-05293-3) · [arXiv:2401.16359](https://arxiv.org/abs/2401.16359).

### 2.5 Recommended citation window

- **Bornmann, L. & Tekles, A. (2019), "Disruption index depends on length of citation window", *El Profesional de la Información* 28(2), e280207.** [PDF](https://revista.profesionaldelainformacion.com/index.php/EPI/article/download/epi.2019.mar.07/43224/224664) — **minimum 3 years**, and even that may not suffice.
- Park et al. (2023) use **5 years (CD5)**, now the de facto standard.
- **Chen, Y. & Bornmann, L. (2026), "Dynamic disruption index across citation and cited references windows: Recommendations for thresholds in research evaluation", *JASIST*.** [DOI 10.1002/asi.70053](https://asistdl.onlinelibrary.wiley.com/doi/10.1002/asi.70053) · [arXiv:2504.07828](https://arxiv.org/abs/2504.07828) — a **10-year** window achieves >80% agreement with the unwindowed value; shorter windows are unstable. Also flags that the **cited-references window** matters, not just the forward window.

**For your case specifically:** with ~100 citations per paper, CD is computable but very noisy. Report CD1, CD5 and CD_nok side by side, bootstrap over citing works for a confidence interval, and do not interpret a single point estimate.

### 2.6 Criticisms — the ones a referee will raise

1. **Citation-window and small-$n$ instability.** Bornmann & Tekles (2019), above.
2. **$n_k$ swamps the denominator**, compressing values toward zero and making DI1 detect almost nothing as disruptive. Wu & Yan (2019); Bornmann & Tekles (2019).
3. **Weak convergent validity.** Bornmann, Devarakonda, Tekles & Chacko (2020), *QSS* 1(3), 1242–1259, [DOI 10.1162/qss_a_00068](https://direct.mit.edu/qss/article/1/3/1242/96102) — tested against F1000Prime "new finding" tags on 120,179 papers; DI1 performs poorly, DI5 better. And **Bornmann, L. & Tekles, A. (2021), "Convergent validity of several indicators measuring disruptiveness with milestone assignments to physics papers by experts", *Journal of Informetrics* 15(3)** [DOI link](https://www.sciencedirect.com/science/article/abs/pii/S1751157721000304) · [arXiv:2006.10606](https://arxiv.org/pdf/2006.10606).
4. **Database dependence.** **CrossDI (2025), "A comprehensive dataset crossing three databases for calculating disruption indexes", *Scientific Data*** [DOI 10.1038/s41597-025-06232-w](https://www.nature.com/articles/s41597-025-06232-w) — shows database coverage, time-window and discipline effects. Also **"Dimensions: Calculating disruption indices at scale", *QSS* 5(4), 975 (2024)** [DOI 10.1162/qss_a_00317](https://direct.mit.edu/qss/article/5/4/975/124268).
5. **Dataset artefacts / zero-reference works.** **Holst, V. T., Algaba, A., Tori, F., Wenmackers, S. & Ginis, V. (2024), "Dataset Artefacts are the Hidden Drivers of the Declining Disruptiveness in Science", [arXiv:2402.14583](https://arxiv.org/abs/2402.14583)** · [code](https://github.com/VincentHolst/reanalysis_declining_disruption) — argues a plotting error hid zero-reference database entries that were nonetheless kept in the analysis, and that the measured decline tracks the falling share of those entries. Published as **Holst et al. (2026), "Dataset artefacts can partially drive the measured decline in disruption", *Nature* 656, E7–E13** [link](https://www.nature.com/articles/s41586-026-10787-y), with **Park, Leahey & Funk (2026), "Reply to…", *Nature* 656, E14–E21** [link](https://www.nature.com/articles/s41586-026-10788-x), which reports that using Holst et al.'s own dataset, metric and method still yields large significant declines ($P<0.01$). Counterpoint: **"Robust Evidence for Declining Disruptiveness: Assessing the Role of Zero-Backward-Citation Works", [arXiv:2503.00184](https://arxiv.org/pdf/2503.00184)**. **The dispute is live — cite both sides.**
6. **Citation inflation.** **Petersen, A. M., Arroyave, F. & Pammolli, F. (2024/2025), "The disruption index is biased by citation inflation", *QSS* 5(4), 936** [DOI 10.1162/qss_a_00305](https://direct.mit.edu/qss/article/5/4/936/124788) · [arXiv:2306.01949](https://arxiv.org/abs/2306.01949); longer version [arXiv:2406.15311](https://arxiv.org/pdf/2406.15311). Also in *Journal of Informetrics* 18(3) (2024) [DOI link](https://www.sciencedirect.com/science/article/pii/S1751157724001172).
7. **Specification uncertainty / researcher degrees of freedom.** **Leibel, C. & Bornmann, L. (2024), "What do we know about the disruption index in scientometrics? An overview of the literature", *Scientometrics* 129, 601–639** [DOI 10.1007/s11192-023-04873-5](https://link.springer.com/article/10.1007/s11192-023-04873-5) · [arXiv:2308.02383](https://arxiv.org/pdf/2308.02383) — **this is your review citation.** Companion letter: **Leibel & Bornmann (2024), "Specification uncertainty: what the disruption index tells us about the (hidden) multiverse of bibliometric indicators", *Scientometrics*** [DOI 10.1007/s11192-024-05201-1](https://link.springer.com/article/10.1007/s11192-024-05201-1) — recommends multiverse-style reporting.
8. **Construct-validity attacks.** **"The Disruption Index measures displacement between a paper and its most cited reference", *QSS* (2025)** [DOI 10.1162/qss.a.409](https://doi.org/10.1162/QSS.a.409) · [arXiv:2504.04677](https://arxiv.org/pdf/2504.04677) — reduces CD to a two-node comparison. **Larregue, J. & Gingras, Y. (2026), "The disruption index does not measure scientific innovation", [arXiv:2606.07332](https://arxiv.org/pdf/2606.07332)** — argues the index reflects citation *practices*, not conceptual content, and that its proponents offer no theory of citing to justify the mapping. Given that your project *does* have citation-context data, you are unusually well placed to answer this critique empirically: cross-tabulate each citing work's $n_i$/$n_j$ status against your role and stance codes.
9. **Confounding with citation counts.** **"Breaking down the relationship between disruption scores and citation counts", *PLOS One* 19 (2024)** [DOI 10.1371/journal.pone.0313268](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0313268).

---

## 3. "Before/after the literature": did the paper unify two separate strands?

There is **no single off-the-shelf index** for "this paper reconciled strand A with strand B." You build it from four established primitives. All four are computable from OpenAlex `referenced_works` alone.

### 3.1 The primitives

**Kessler, M. M. (1963), "Bibliographic coupling between scientific papers", *American Documentation* 14(1), 10–25.** [DOI 10.1002/asi.5090140103](https://onlinelibrary.wiley.com/doi/10.1002/asi.5090140103)
Two documents are coupled if they **share references**; coupling strength = number of shared references. Fixed at publication time — it describes the *citing* paper's own intellectual inputs. Use it to ask: **does the focal paper itself draw on both strands?**

**Small, H. (1973), "Co-citation in the scientific literature: A new measure of the relationship between two documents", *JASIS* 24(4), 265–269.** [DOI 10.1002/asi.4630240406](https://asistdl.onlinelibrary.wiley.com/doi/10.1002/asi.4630240406)
Two documents are co-cited if a later document cites both. **Evolves over time**, because it is defined by the community's subsequent behaviour. Use it to ask: **did the field come to treat the two strands as one?** This is the only primitive that gives you a genuine before/after.

**Burt, R. S. (1992), *Structural Holes: The Social Structure of Competition*, Harvard University Press** [publisher](https://www.hup.harvard.edu/books/9780674843714); **Burt, R. S. (2004), "Structural Holes and Good Ideas", *American Journal of Sociology* 110(2), 349–399** [DOI 10.1086/421787](https://www.journals.uchicago.edu/doi/abs/10.1086/421787) · [PDF](https://www.bebr.ufl.edu/sites/default/files/Burt%20-%202004%20-%20Structural%20Holes%20and%20Good%20Ideas.pdf).
Brokerage across a structural hole between two otherwise disconnected clusters is the mechanism by which good ideas arise. Operationalised as **network constraint** (low constraint = spans holes) and **betweenness centrality**.

**Uzzi, B., Mukherjee, S., Stringer, M. & Jones, B. (2013), "Atypical Combinations and Scientific Impact", *Science* 342(6157), 468–472.** [DOI 10.1126/science.1240474](https://www.science.org/doi/10.1126/science.1240474)
For each pair of journals appearing in a paper's reference list, compute a **z-score** of observed vs expected co-occurrence frequency (expectation from a degree-preserving randomised citation network). Characterise the paper by the **median** z-score (conventionality) and the **10th-percentile** z-score (atypical tail). 17.9M WoS articles; the highest-impact papers combine a **high-conventionality core with an atypical tail**, and are ~2× as likely to be highly cited. This is exactly the profile of a paper that reconciles two established strands rather than inventing from nothing.

Two refinements of the same idea:
- **Lee, Y.-N., Walsh, J. P. & Wang, J. (2015), "Creativity in scientific teams: Unpacking novelty and impact", *Research Policy* 44(3), 684–697.** [DOI 10.1016/j.respol.2014.10.007](https://www.sciencedirect.com/science/article/abs/pii/S0048733314001826) — commonness of a journal pairing = observed/expected frequency.
- **Wang, J., Veugelers, R. & Stephan, P. (2017), "Bias against novelty in science: A cautionary tale for users of bibliometric indicators", *Research Policy* 46(8), 1416–1436.** [DOI 10.1016/j.respol.2017.06.006](https://ideas.repec.org/a/eee/respol/v46y2017i8p1416-1436.html) · [NBER w22180](https://www.nber.org/papers/w22180) — **first-time-ever journal combinations**, weighted by difficulty. Key result for you: novel papers are **published in lower-IF journals and under-cited in short windows**, with delayed recognition and higher citation variance. If your author's paper is a genuine strand-unifier, this predicts its citation count *understates* it — a defensible argument, with a citation.

### 3.2 The purpose-built "boundary spanning" measures

**Chen, C., Chen, Y., Horowitz, M., Hou, H., Liu, Z. & Pellegrino, D. (2009), "Towards an explanatory and computational theory of scientific discovery", *Journal of Informetrics* 3(3), 191–209.** [DOI 10.1016/j.joi.2009.03.004](https://www.sciencedirect.com/science/article/abs/pii/S1751157709000236) · [arXiv:0904.1439](https://arxiv.org/abs/0904.1439)
Extends Burt's structural holes to **co-citation networks**. Transformative-discovery score $\sigma = (\varphi + 1)^{\delta}$, where $\varphi$ = betweenness centrality in the co-citation network and $\delta$ = citation burstness. A paper with high co-citation betweenness "belongs to multiple story sets" — i.e. it is being used by the field as a bridge. Validated on peptic ulcer / *H. pylori*, gene targeting, and string theory.

**Chen, C. (2012), "Predictive effects of structural variation on citation counts", *JASIST* 63(3), 431–449.** [DOI 10.1002/asi.21694](https://onlinelibrary.wiley.com/doi/abs/10.1002/asi.21694) · [author PDF](http://cluster.ischool.drexel.edu/~cchen/papers/2012/jasist2012-predictive.pdf) · [method notes](https://sites.google.com/site/citespace101/11-advanced-topics/11-3structural-variation-analysis-sva)
**This is the closest thing in the literature to a direct "did this paper unify two strands?" measure.** Structural Variation Analysis builds a *baseline* co-citation network from the literature **as it stood before the focal paper**, then measures the novel boundary-spanning links the focal paper's reference list introduces into it, via three metrics:
- **Modularity change rate (ΔM)** — how much the focal paper's new links reduce the network's modular separation
- **Cluster linkage (CL)** — number/weight of links the paper creates *between* previously distinct clusters
- **Centrality divergence (CKL)** — how much the paper redistributes betweenness

Weighted cluster linkage was the strongest predictor of eventual citation counts, ahead of number of coauthors. Implemented in CiteSpace.

**Diversity-and-coherence framing:** **Rafols, I. & Meyer, M. (2010), "Diversity and network coherence as indicators of interdisciplinarity: case studies in bionanoscience", *Scientometrics* 82(2), 263–287.** [record](https://ideas.repec.org/a/spr/scient/v82y2010i2d10.1007_s11192-009-0041-y.html); the Rao–Stirling framework is decomposed into variety/balance/disparity in **Leydesdorff, Wagner & Bornmann (2018/2019), "Interdisciplinarity as diversity in citation patterns among journals"** [DOI 10.1016/j.joi.2019.03.001](https://www.sciencedirect.com/science/article/pii/S1751157718303535) · [arXiv:1807.04115](https://arxiv.org/pdf/1807.04115). Rao–Stirling diversity on the reference list measures *integration*; coherence measures whether the integrated pieces actually hang together.

### 3.3 The design I would actually run for "congestion-internalization vs competition-quality"

This is a **co-citation difference-in-differences with a brokerage share**, and it is the only construction that supports the causal-sounding claim "this paper reconciled two strands."

1. **Define the strands.** Seed strand A (congestion internalization: Pigou/Vickrey/Arnott–de Palma–Lindsey lineage) and strand B (competition and service quality) with 10–30 hand-picked papers each. Expand each seed set by bibliographic coupling (Kessler) and direct-citation clustering over OpenAlex `referenced_works`. Freeze the two sets. **Pre-register or at minimum report the seed lists and the expansion rule** — cluster definition is the biggest researcher degree of freedom here, and Leibel & Bornmann's multiverse critique (§2.6) applies with full force.
2. **Baseline (pre-period).** Over all documents published before year $t_0$ (focal paper's year), compute the A–B co-citation count and the **observed/expected ratio** with a degree-preserving null (Uzzi's z-score machinery). This establishes that the strands were in fact separate — which is the claim you actually need to defend, and the one that is easiest to falsify.
3. **Post-period, decomposed.** For documents published after $t_0$, split A–B co-citing documents into those that **also cite the focal paper** and those that do not. Report the **brokerage share**: the fraction of new A–B co-citation ties that pass through documents citing the focal paper. This is the direct quantitative expression of "reconciled the two strands."
4. **Counterfactual.** Difference-in-differences against matched cluster pairs (similar size, age, field, pre-period co-citation density) that had no comparable focal paper. Without this, you cannot separate the focal paper's effect from a general trend toward integration in transport economics.
5. **Paper-level corroboration.** (a) Uzzi z-score profile of the focal paper's own reference list — does it make a rare A×B journal pairing? (b) Wang–Veugelers–Stephan first-time-ever combination check. (c) Chen (2012) SVA metrics — ΔM, cluster linkage, centrality divergence — against the pre-$t_0$ baseline network. (d) Betweenness/Burt constraint of the focal paper in the post-period co-citation network (Chen et al. 2009).
6. **Full-text confirmation.** Your ~104 coded passages are the qualitative complement: count how many citing passages explicitly invoke the focal paper *as* the reconciliation (i.e. cite it in a sentence that mentions both strands). This is the mixed-methods move that answers Larregue & Gingras's objection to purely structural indices.

**Which primitive proves what.** Bibliographic coupling proves the focal paper *drew on* both strands (a property of the author). Co-citation before/after proves the *field changed how it reads them* (a property of the community) — **only co-citation can demonstrate a before/after effect**, so it is the load-bearing method. Uzzi/Wang measures prove the combination was *rare*, not that it was *unifying*. Burt/Chen betweenness proves the paper *sits* in the bridge position, which is necessary but not sufficient (a paper can occupy a hole without anyone routing through it).

**Known limitation.** Co-citation is a lagging indicator that needs a substantial post-period citation stock; with ~100 citations your A–B co-citation cell counts will be small. Use exact/permutation tests, not asymptotic ones.

---

## 4. Claim-level validation: tracking a specific finding through its citations

### 4.1 Foundations

**Small, H. (1982), "Citation context analysis", in B. J. Dervin & M. J. Voight (eds), *Progress in Communication Sciences*, Vol. 3, 287–310, Ablex, Norwood NJ.** (Book chapter, no DOI; verified bibliographically, full text not retrieved.) The methodological origin of reading citation contexts as data. See also **Small, H. (1978), "Cited documents as concept symbols", *Social Studies of Science* 8(3), 327–340** — the argument that a heavily cited paper becomes a compressed *symbol* for a claim, which is precisely the mechanism you are trying to measure. And **Small, H. (1986), "The synthesis of specialty narratives from co-citation clusters", *JASIS* 37(3), 97–110** [DOI link](https://asistdl.onlinelibrary.wiley.com/doi/abs/10.1002/(SICI)1097-4571(198605)37:3%3C97::AID-ASI1%3E3.0.CO;2-K) — the bridge between §3 and §4.

**Bornmann & Daniel (2008)** and **Tahamtan & Bornmann (2019)**, as in §1.2, are the reviews that situate citation context analysis in the citing-behaviour literature.

**Anderson, M. H. & Lemken, R. K. (2023), "Citation Context Analysis as a Method for Conducting Rigorous and Impactful Literature Reviews", *Organizational Research Methods* 26(1), 77–106.** [DOI 10.1177/1094428120969905](https://journals.sagepub.com/doi/10.1177/1094428120969905) · [open repository copy](https://dr.lib.iastate.edu/server/api/core/bitstreams/d3fd49bf-5872-4c62-8741-e0e3c3cf2f5c/content)
**This is the methods citation you want.** It is the modern, social-science-facing protocol: what questions CCA can answer, sampling of citing works, coding-scheme construction, reliability, and how to assess "how theories are used, empirically tested, and critiqued by subsequent citing authors." It is written for management/organizational research, so it will read as native to an economics audience in a way that the NLP papers will not.

### 4.2 Tracking a claim's fate — the canonical study

**Greenberg, S. A. (2009), "How citation distortions create unfounded authority: analysis of a citation network", *BMJ* 339, b2680.** [DOI 10.1136/bmj.b2680](https://www.bmj.com/content/339/bmj.b2680) · [open access PMC2714656](https://pmc.ncbi.nlm.nih.gov/articles/PMC2714656/)

Method: build a **claim-specific citation network** — every paper addressing one belief (β-amyloid is produced by and injures skeletal muscle in inclusion body myositis), every citation among them, coded for whether it supports, refutes, or is neutral toward *that specific claim*. Analysed with social-network and graph theory. **242 papers, 675 citations, 220,553 citation paths.**

The taxonomy of distortion mechanisms — directly reusable as your "wrongly-interpreted" sub-codes:

- **Citation bias** — systematically ignoring papers whose content conflicts with the claim. Measured: supportive primary data received **94%** of citations vs **6%** for critical data ($P = 0.01$); for model justification, **31 of 32 citations (97%)** went to supportive data.
- **Amplification** — expansion of the belief system by papers presenting **no data** bearing on it. Between 1996 and 2007 supportive citations grew ~7-fold while critical citations grew to only 21.
- **Invention**, with five subtypes:
  - *Citation diversion* — citing content while claiming it means something different
  - *Citation transmutation* — converting a hypothesis into a fact through citation alone
  - *Back-door invention* — repeatedly citing conference abstracts as if peer-reviewed papers
  - *Dead-end citation* — supporting a claim with a paper containing no relevant content
  - *Title invention* — a title reporting results the paper does not contain

Your 4/104 "misattribution" rate maps most cleanly onto *citation diversion* + *citation transmutation* + *dead-end citation*. Adopting Greenberg's vocabulary makes the finding legible and comparable.

### 4.3 Recent computational work on claim-level citation fidelity

- **Meng, X., Varol, O. & Barabási, A.-L. (2024), "Hidden citations obscure true impact in science", *PNAS Nexus* 3(5), pgae155.** [DOI 10.1093/pnasnexus/pgae155](https://academic.oup.com/pnasnexus/article/3/5/pgae155/7664049) — "hidden citations" = unambiguous allusions to a body of knowledge with **no explicit citation** to the originating paper, detected by LDA over full-text contexts (catchphrase ↔ foundational paper matching). For four physics topics, hidden citations were **34.6%–65.8% of detectable credit**; mean hidden:explicit ratio **0.98:1**; scaling $h \sim c^{0.763}$; strong negative correlation ($\rho \approx -0.611$) between how often a concept is mentioned and how often it is formally cited. **Directly relevant to you:** the more a claim becomes canonical, the *less* it is cited — so a low citation count on a foundational claim is evidence *for*, not against, foundational status.
- **"The Noisy Path from Source to Citation: Measuring How Scholars Engage with Past Research", [arXiv:2502.20581](https://arxiv.org/html/2502.20581v1)** — flagged as relevant; I could not extract its numbers (PDF/HTML fetch failed). Worth chasing.
- **"SemanticCite: Citation Verification with AI-Powered Full-Text Analysis and Evidence-Based Reasoning", [arXiv:2511.16198](https://arxiv.org/pdf/2511.16198)** and **"Reading Between the Citations: A Typed Claim Network for Scientific Literature", [arXiv:2605.30966](https://arxiv.org/pdf/2605.30966)** — recent LLM-based claim-to-source verification; not read in depth.
- For claim/evidence matching as a supervised task, the standard benchmark is **SciFact** (Wadden et al., EMNLP 2020) — **not verified this session**.

### 4.4 LLM-based citation classification and agreement thresholds

**Landis, J. R. & Koch, G. G. (1977), "The measurement of observer agreement for categorical data", *Biometrics* 33(1), 159–174.** [PubMed 843571](https://pubmed.ncbi.nlm.nih.gov/843571/)
Benchmarks: **<0.00 poor · 0.00–0.20 slight · 0.21–0.40 fair · 0.41–0.60 moderate · 0.61–0.80 substantial · 0.81–1.00 almost perfect.** These are explicitly **arbitrary conventions**, and the standard criticism is that κ is sensitive to marginal distributions and prevalence (the "kappa paradoxes"). With a rare category — and *wrongly-interpreted* at 4/104 and *contradictory* stance at a likely ~2–3% base rate will both be rare — κ can be near zero despite ~97% raw agreement. **Report raw agreement, prevalence, and prevalence-adjusted bias-adjusted kappa (PABAK) alongside κ**, and use ordinal Krippendorff's α for the role scale.

**What the field actually achieves — your realistic target:**
- Teufel et al. (2006): human–human **κ = 0.72** on 12 classes.
- **"Large Language Models for Citation Function Classification" (2026), [arXiv:2607.17738](https://arxiv.org/html/2607.17738)** — evaluates Mistral 7B, Orca 2-7B, LLaMA 3.1-8B, Falcon 7B and SciBERT on ACL-ARC (1,941 citations, 6 classes) plus a **new 7-class scheme, AC3** (530 citations, 9 arXiv domains) that deliberately separates *neutral acknowledgement* (Basis, Use, Substantiating) from *opinion-oriented* citations (Criticizing, Compliment, Contradiction, Comparison). **AC3's 7 classes are structurally the closest published analogue to your 7-level scale.** Human agreement: **52% initially, rising to Cohen's κ = 0.71 after iterative guideline refinement and adjudication.** Fine-tuned Falcon 7B reached 73.3% macro-F1; zero-/few-shot LLM performance was poor, and **all models underperformed badly on the rare opinion-oriented classes** — which are exactly your *contradictory* and *wrongly-interpreted* categories.
- **"Scientific Software Citation Intent Classification Using Large Language Models" (2024), Springer** [DOI 10.1007/978-3-031-65794-8_6](https://link.springer.com/chapter/10.1007/978-3-031-65794-8_6) — >80% accuracy when fine-tuned.

**Two design recommendations that follow directly:**
1. **Report the iteration.** The 2026 paper's 52% → 0.71 trajectory is now the norm; publishing your pre- and post-adjudication agreement is more credible than a single number.
2. **If most of your 104 labels are LLM-generated, do not compute confidence intervals as if they were human.** Use **prediction-powered inference**: **Angelopoulos, A. N., Bates, S., Fannjiang, C., Jordan, M. I. & Zrnic, T. (2023), "Prediction-powered inference", *Science* 382(6671), 669–674** [DOI 10.1126/science.adi6000](https://www.science.org/doi/10.1126/science.adi6000) · [arXiv:2301.09633](https://arxiv.org/abs/2301.09633) — human-label a random subsample, use it to debias the LLM-labelled remainder, and obtain provably valid CIs without assuming anything about the classifier. This is the cleanest available answer to "your rates come from an LLM, why should I believe them?"

**Computability:** claim-level work needs full text of citing papers plus manual or LLM reading. Nothing in OpenAlex, Crossref, or the Semantic Scholar API gives you claim-level mapping; S2's `contexts` field gives you the snippets to read.

---

## 5. Ghost and inaccurate citations: base rates for calibration

### 5.1 "Ghost" citations — reference-list-only

**Boyack, K. W., van Eck, N. J., Colavizza, G. & Waltman, L. (2018), "Characterizing in-text citations in scientific articles: A large-scale analysis", *Journal of Informetrics* 12(1), 59–73.** [DOI 10.1016/j.joi.2017.11.005](https://www.sciencedirect.com/science/article/abs/pii/S1751157717303516) · [arXiv:1710.03094](https://arxiv.org/abs/1710.03094)

>5 million full-text articles from PubMed Central OA and Elsevier. **In the Elsevier corpus, 1.4% of references were not mentioned anywhere in the body text** (i.e. ~98.6% appeared at least once). **71.5% (PMCOA) / 69.5% (ELS) of references are mentioned exactly once.** This is the closest thing to a published base rate for your "ghost" category — with an important caveat below.

Related but distinct phenomena, worth distinguishing in your write-up:
- **Hidden citations** — the inverse: the idea is discussed in text with no reference at all. Meng, Varol & Barabási (2024), §4.3; **34.6%–65.8%** of detectable credit.
- **Phantom / hallucinated references** — bibliography entries that resolve to nothing. **"Phantom References: Hallucinated Citations That Survive Peer Review at Top-Tier Conferences" (2026), [arXiv:2607.00738](https://arxiv.org/abs/2607.00738)** — reference-level hallucination rates usually **<1%**, but roughly **1 in 20** NeurIPS/USENIX Security 2025 papers contains ≥2 likely hallucinated references. Also the well-documented case where a non-existent reference accumulated ~400 citations: **Harzing, A.-W., "The mystery of the phantom reference"** [white paper](https://harzing.com/publications/white-papers/the-mystery-of-the-phantom-reference) · [Retraction Watch](https://retractionwatch.com/2017/11/14/phantom-reference-made-article-got-almost-400-citations/).

**Interpreting your 13/104 = 12.5% ghost rate.** This is roughly **9× the 1.4% Elsevier base rate**, which demands explanation. Three candidate explanations, and you should rule out the first two before claiming the third:

1. **Measurement artefact — most likely.** Boyack et al. used publisher-supplied structured XML with reliable reference↔in-text-marker linking. If your pipeline works from PDFs, or if you could not obtain full text for some citing papers, then "no in-text passage found" conflates (a) genuine reference-list-only citations, (b) full-text unavailable, and (c) extraction/matching failure. **Report these three separately.** For economics and transport, where OA full text is sparse, (b) alone could account for most of the 13.
2. **Numbered-citation and citation-bundle effects.** A reference cited only inside a bundle like "[3–17]" or "(see, e.g., …)" is a *real* in-text mention that naive matchers miss and that human coders may legitimately code as ghost. Decide and document which convention you use.
3. **A genuine field effect.** Economics has long reference lists, extensive referee-requested additions, and heavy introduction/related-work citation. If (1) and (2) are ruled out, an elevated reference-list-only rate is a substantive and publishable finding — but it needs a comparison sample of similar papers from the same journals, coded the same way, before it means anything.

**Better comparators for "drive-by" than for "ghost":** Moravcsik & Murugesan's **41% perfunctory**, Valenzuela et al.'s **85.4% incidental**, SciCite's **58% background**, Teufel's **>60% Neut**. If your "drive-by" level is running in the 40–60% range, you are exactly where the literature says you should be.

### 5.2 Misattribution / quotation errors

**Jergas, H. & Baethge, C. (2015), "Quotation accuracy in medical journal articles — a systematic review and meta-analysis", *PeerJ* 3:e1364.** [DOI 10.7717/peerj.1364](https://peerj.com/articles/1364/) · [PDF](https://peerj.com/articles/1364.pdf)
Synthesis of **28 studies**. **Total quotation error rate 25.4%**; **minor errors 8.5%**. Quotation accuracy defined as whether the cited reference actually supports or accords with the citing authors' statement.

Published base rates for comparison:

| Study | Field | Total quotation error rate | n |
|---|---|---|---|
| Jergas & Baethge (2015), *PeerJ* | medicine (meta-analysis, 28 studies) | **25.4%** (minor 8.5%) | — |
| [Systematic review & meta-analysis of quotation inaccuracy in medicine (2025), *Research Integrity and Peer Review*](https://link.springer.com/article/10.1186/s41073-025-00173-z) | medicine | **14.5%** (per secondary citation) | — |
| [Smith, N. & Cumberledge, A. (2020), *Proc. R. Soc. A* 476:20200538](https://royalsocietypublishing.org/doi/abs/10.1098/rspa.2020.0538) | general science (high-IF) | **25%** | 250 citations |
| [Mogull, S. A. (2017), *PLOS One* 12(9):e0184727](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0184727) | medicine (methodology re-analysis) | recalculated rates | — |
| [Quotation accuracy in educational research articles (2022), *Educational Research Review*](https://www.sciencedirect.com/science/article/pii/S1747938X21000531) | education | **15%** | 500 citations, 2016–2020 |
| [Quotation errors in high-IF orthopaedic and sports medicine journals (2021), PMC8386904](https://ncbi.nlm.nih.gov/pmc/articles/PMC8386904) | orthopaedics | **13.6%** (2.8% completely unsubstantiated) | — |
| [Wakeling, S. et al. (2025), *JASIST*](https://asistdl.onlinelibrary.wiley.com/doi/10.1002/asi.70000) | cross-disciplinary author survey, 2,648 responses | **16.6%** implied; range **13.1%** (physical/environmental sciences) to **20.4%** (engineering/technology/applied) | 2,648 |

**Interpreting your 4/104 = 3.8% misattribution rate.** This is **far below** every published base rate (13–25%). Two readings, and you should say which:

1. **Definitional.** Quotation-error studies count *any* proposition not substantiated by the cited source, including minor ones (Jergas & Baethge's "minor" bucket alone is 8.5%). If you counted only clear misstatements of the paper's actual claim, you have measured something closer to their *major* error category, and 3.8% is plausible and comparable to the "2.8% completely unsubstantiated" figure from the orthopaedics study. **State your threshold explicitly and, if feasible, re-code with a minor/major split** so your number is comparable to the literature.
2. **Substantive.** The papers are cited accurately. Defensible — but only after (1) is addressed.

The 16.6% survey figure from Wakeling et al. is the most directly comparable number if you ever want the *authors'* own view of how their work is cited, which is essentially what your project is doing from the outside.

**No economics- or transport-specific citation-accuracy study surfaced.** See §6.

### 5.3 Citation copying and the Matthew effect

**Simkin, M. V. & Roychowdhury, V. P. (2003), "Read Before You Cite!", *Complex Systems* 14(3), 269–274.** [journal](https://www.complex-systems.com/abstracts/v14_i03_a05/) · [PDF](https://wpmedia.wolfram.com/sites/13/2018/02/14-3-5.pdf) · [arXiv:cond-mat/0212043]
Method: track **repeated misprints** in citations to twelve high-profile papers. Misprint repetition frequencies follow **Zipf's law**; a stochastic model of the citation process implies **~70–90% (headline figure ~80%) of scientific citations are copied from other papers' reference lists**, i.e. only ~20% of citers read the original. Follow-ups: **Simkin & Roychowdhury, "A mathematical theory of citing"** [arXiv:physics/0504094](https://arxiv.org/pdf/physics/0504094) and **"An introduction to the theory of citing"** [arXiv:math/0701086](https://arxiv.org/pdf/math/0701086); popular treatment in *Significance* (2006) [DOI 10.1111/j.1740-9713.2006.00202.x](https://rss.onlinelibrary.wiley.com/doi/full/10.1111/j.1740-9713.2006.00202.x).

The 80% copying estimate is the mechanistic explanation for both your ghost rate and your misattribution rate: a copied citation is by construction one where the citer never engaged with the source, so it lands in the reference list with no substantive in-text use, and any error in the upstream characterisation propagates. **Note the standard criticism**: the estimate depends heavily on the assumed stochastic model, and alternative models yield much lower copying rates. Present it as an upper-bound-ish illustration, not a measured quantity.

### 5.4 Negative/contradictory stance base rate

**Catalini, C., Lacetera, N. & Oettl, A. (2015), "The incidence and role of negative citations in science", *PNAS* 112(45), 13823–13826.** [DOI 10.1073/pnas.1502280112](https://www.pnas.org/doi/10.1073/pnas.1502280112)
Immunology; training set of 15,000 citations manually reviewed by immunology PhDs. **Negative citations are 2.40% of all citations** (2.44% in the sub-sample with full bibliographic data). Negative = inability to replicate, disagreement, or inconsistency with prior results/theory. Athar's (2011) corpus gives a comparable **~2.8% negative**.

**Use this to calibrate your stance axis.** If your "contradictory" count is near zero out of 104, that is the expected result, not a failure of coding — and it is worth saying so with a citation, because a naive reader will read "no contradictory citations" as either uncritical acceptance or a broken instrument.

### 5.5 The framework paper for this whole section

**Bornmann, L. & Leibel, C. (2025/2026), "Citation accuracy, citation noise, and citation bias: A foundation of citation analysis", [arXiv:2508.12735](https://arxiv.org/abs/2508.12735)** (submitted Aug 2025, revised Jul 2026; also on [MetaROR](https://metaror.org/article/citation-accuracy-citation-noise-and-citation-bias-a-foundation-of-citation-analysis/)). Distinguishes **citation accuracy** (do citations represent genuine intellectual input?), **citation bias** (systematic directional distortion), and **citation noise** (undesirable *variance* in citation decisions, split into citation-level and citation-pattern noise). Argues noise is systematically under-studied relative to bias. **This gives you the vocabulary to frame ghost + misattribution as two distinct constructs** — ghosts are noise, misattributions are accuracy failures — rather than lumping them as "bad citations."

---

## 6. Flags: what I could not verify

| Item | Status |
|---|---|
| Moravcsik & Murugesan (1975) four dimensions and the 41% perfunctory figure | Verified only via **secondary sources** (Teufel et al. 2006; citation-function surveys). The 1975 original is paywalled and I did not read it. |
| Teufel et al. (2006) corpus size beyond "116 documents"; the figure "2,829 citations" | **Not verified.** κ = 0.72 and ">60% Neut" are from secondary sources quoting the paper; the PDF fetch returned binary. |
| Jurgens et al. (2018) inter-annotator agreement (κ) | **Not found.** Dataset size (~1,941 instances / 186 papers) verified via secondary sources. Category *definitions* above are paraphrases from secondary sources, not the paper's own wording. |
| Cohan et al. (2019) SciCite: number of annotators and Cohen's κ | **Not verified.** The 11,020 size and 58/29/13% class split come from a secondary source. |
| Valenzuela et al. (2015): the exact labels of the four ordinal importance levels | **Not verified.** Confirmed: binary important/incidental, 465 pairs, 14.6% important, and the rule that *uses*/*extends* = important while *related work*/*comparison* = incidental. The four-level label wording is not confirmed. |
| CiTO property → positive/neutral/negative stance grouping | The property names are from the [official v2.9.0 spec](https://sparontologies.github.io/cito/current/cito.html). The **stance grouping shown is a derived organisation**, not necessarily an official CiTO axis. Verify against Shotton (2010) §"rhetorical properties" before publishing it as CiTO's own classification. |
| **DEP** (dependency indicator) exact definition, Bornmann et al. (2020) | **Not verified.** I could not open the QSS article (403) or extract the arXiv PDF. Get it from [arXiv:1911.08775](https://arxiv.org/abs/1911.08775) before citing. |
| Funk & Owen-Smith (2017) original weighted formula $\frac{1}{n}\sum \frac{-2f_ib_i+f_i}{w_i}$ | Stated from prior knowledge, **not re-verified against the paper this session**. The counting form $(n_i-n_j)/(n_i+n_j+n_k)$ **is** verified. |
| Jergas & Baethge major-error rate | Only **total 25.4%** and **minor 8.5%** verified. The major-error figure is not confirmed; do not infer it by subtraction without checking. |
| The 14.5% figure from the 2025 *Research Integrity and Peer Review* meta-analysis | From a **secondary citation**, not the paper itself. |
| Boyack et al. (2018) "1.4% of references not mentioned in text" | From a **single search snippet**, not the full text. This number is load-bearing for your ghost-rate comparison — **verify it in the [arXiv preprint](https://arxiv.org/pdf/1710.03094) before publishing.** Also check whether unmatched references were excluded upstream rather than counted. |
| Any citation-accuracy or quotation-error study in **economics** or **transport** | **None found.** Nearest disciplinary analogues located: education (15%), library & information science in Taiwan (13.67%), orthopaedics/sports medicine (13.6%), general science (25%), and the cross-disciplinary author survey (Wakeling et al. 2025) which reports 13.1%–20.4% across broad fields. If a referee asks for an economics base rate, the honest answer is that none exists and you are establishing one. |
| SciFact (Wadden et al. 2020) as the claim-verification benchmark | Stated from prior knowledge; **not searched this session**. |
| "The Noisy Path from Source to Citation" ([arXiv:2502.20581](https://arxiv.org/html/2502.20581v1)) | Identified as relevant; **content not extracted** (fetch failed). |
| Small (1982) chapter content | Bibliographic details verified; **full text not retrieved**. |

---

## Sources

[Teufel et al. 2006 — annotation scheme](https://aclanthology.org/W06-1312/) · [Teufel et al. 2006 — automatic classification](https://aclanthology.org/W06-1613/) · [Jurgens et al. 2018 TACL](https://aclanthology.org/Q18-1028/) · [Jurgens project page](https://jurgens.people.si.umich.edu/citation-function/) · [Cohan et al. 2019 NAACL](https://aclanthology.org/N19-1361/) · [arXiv:1904.01608](https://arxiv.org/abs/1904.01608) · [SciCite data](https://huggingface.co/datasets/allenai/scicite) · [Valenzuela et al. 2015](https://www.semanticscholar.org/paper/Identifying-Meaningful-Citations-Valenzuela-Escarcega-Ha/1c7be3fc28296a97607d426f9168ad4836407e4b) · [Zhu et al. 2015 JASIST](https://asistdl.onlinelibrary.wiley.com/doi/10.1002/asi.23179) · [Moravcsik & Murugesan 1975](https://journals.sagepub.com/doi/10.1177/030631277500500106) · [Shotton 2010 CiTO](https://jbiomedsem.biomedcentral.com/articles/10.1186/2041-1480-1-S1-S6) · [CiTO current spec](https://sparontologies.github.io/cito/current/cito.html) · [Nicholson et al. 2021 scite](https://direct.mit.edu/qss/article/2/3/882/102990) · [Athar 2011](https://aclanthology.org/P11-3015/) · [Bornmann & Daniel 2008](https://www.emerald.com/jd/article/64/1/45/222089/What-do-citation-counts-measure-A-review-of) · [Tahamtan & Bornmann 2019](https://link.springer.com/article/10.1007/s11192-019-03243-4) · [Kunnath et al. 2021 meta-analysis](https://direct.mit.edu/qss/article/2/4/1170/107610) · [Funk & Owen-Smith 2017](https://pubsonline.informs.org/doi/10.1287/mnsc.2015.2366) · [Wu, Wang & Evans 2019](https://www.nature.com/articles/s41586-019-0941-9) · [Park, Leahey & Funk 2023](https://www.nature.com/articles/s41586-022-05543-x) · [Bornmann et al. 2020 QSS](https://direct.mit.edu/qss/article/1/3/1242/96102) · [arXiv:1911.08775](https://arxiv.org/abs/1911.08775) · [Wu & Yan 2019](https://arxiv.org/abs/1905.03461) · [Bornmann & Tekles 2019 EPI](https://revista.profesionaldelainformacion.com/index.php/EPI/article/download/epi.2019.mar.07/43224/224664) · [Chen & Bornmann 2026 JASIST](https://asistdl.onlinelibrary.wiley.com/doi/10.1002/asi.70053) · [Leibel & Bornmann 2024 review](https://link.springer.com/article/10.1007/s11192-023-04873-5) · [Leibel & Bornmann 2024 multiverse letter](https://link.springer.com/article/10.1007/s11192-024-05201-1) · [Holst et al. arXiv:2402.14583](https://arxiv.org/abs/2402.14583) · [Holst et al. Nature 2026](https://www.nature.com/articles/s41586-026-10787-y) · [Park et al. Reply Nature 2026](https://www.nature.com/articles/s41586-026-10788-x) · [Petersen et al. QSS citation inflation](https://direct.mit.edu/qss/article/5/4/936/124788) · [CrossDI Scientific Data 2025](https://www.nature.com/articles/s41597-025-06232-w) · [Larregue & Gingras 2026](https://arxiv.org/pdf/2606.07332) · [QSS displacement critique](https://doi.org/10.1162/QSS.a.409) · [OpenAlex filter docs](https://github.com/ourresearch/openalex-docs/blob/main/api-entities/works/filter-works.md) · [OpenAlex reference-count caveat](https://help.openalex.org/hc/en-us/articles/27810109633943-The-reference-counts-in-OpenAlex-seem-off-Why-is-that) · [Culbert et al. 2025 reference coverage](https://link.springer.com/article/10.1007/s11192-025-05293-3) · [Kessler 1963](https://onlinelibrary.wiley.com/doi/10.1002/asi.5090140103) · [Small 1973](https://asistdl.onlinelibrary.wiley.com/doi/10.1002/asi.4630240406) · [Burt 2004 AJS](https://www.journals.uchicago.edu/doi/abs/10.1086/421787) · [Uzzi et al. 2013](https://www.science.org/doi/10.1126/science.1240474) · [Lee, Walsh & Wang 2015](https://www.sciencedirect.com/science/article/abs/pii/S0048733314001826) · [Wang, Veugelers & Stephan 2017](https://www.nber.org/papers/w22180) · [Chen et al. 2009](https://arxiv.org/abs/0904.1439) · [Chen 2012 SVA](https://onlinelibrary.wiley.com/doi/abs/10.1002/asi.21694) · [Rafols & Meyer 2010](https://ideas.repec.org/a/spr/scient/v82y2010i2d10.1007_s11192-009-0041-y.html) · [Anderson & Lemken 2023](https://journals.sagepub.com/doi/10.1177/1094428120969905) · [Greenberg 2009 BMJ](https://pmc.ncbi.nlm.nih.gov/articles/PMC2714656/) · [Meng, Varol & Barabási 2024](https://academic.oup.com/pnasnexus/article/3/5/pgae155/7664049) · [Landis & Koch 1977](https://pubmed.ncbi.nlm.nih.gov/843571/) · [LLMs for citation function 2026](https://arxiv.org/html/2607.17738) · [Angelopoulos et al. 2023](https://www.science.org/doi/10.1126/science.adi6000) · [Boyack et al. 2018](https://arxiv.org/abs/1710.03094) · [Jergas & Baethge 2015](https://peerj.com/articles/1364/) · [Smith & Cumberledge 2020](https://royalsocietypublishing.org/doi/abs/10.1098/rspa.2020.0538) · [Wakeling et al. 2025 JASIST](https://asistdl.onlinelibrary.wiley.com/doi/10.1002/asi.70000) · [Simkin & Roychowdhury 2003](https://www.complex-systems.com/abstracts/v14_i03_a05/) · [Catalini, Lacetera & Oettl 2015](https://www.pnas.org/doi/10.1073/pnas.1502280112) · [Bornmann & Leibel arXiv:2508.12735](https://arxiv.org/abs/2508.12735) · [Phantom references arXiv:2607.00738](https://arxiv.org/abs/2607.00738)

---

**Two things I'd flag as the highest-leverage next steps.** First, verify the Boyack et al. 1.4% figure in the preprint — your entire ghost-rate interpretation hinges on it, and you need to know whether their pipeline *counted* or *dropped* unmatched references. Second, decide now whether your 104 passages will be reported on one 7-level scale or on three orthogonal axes (depth / stance / accuracy); the agreement statistics, the base-rate comparisons, and the crosswalk to published schemes all work far better under the three-axis design, and retrofitting it later means re-coding.
