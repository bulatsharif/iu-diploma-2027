# Initial bachelor's thesis draft

**Performance Optimization of Large Language Model Inference on GPUs**  
Bulat Sharipov · Innopolis University · 2027  
Draft date: 13 October 2026

## Contents

The six chapters are Introduction, Literature Review, Methodology,
Implementation, Evaluation and Discussion, and Conclusion. The package also
includes the abstract, references, complete baseline tables and an evidence
checklist. Formatting follows the supplied extreport thesis template: A4,
14-point Tempora, the original body margins, line spacing and chapter layout.
The cover is centered on the physical page and imported without the vmargin
offset shift. The supervisor remains to be confirmed.

Only the archived target-only Qwen3-8B results are treated as measurements.
All optimization results, quality checks, repeated trials and final research
conclusions remain explicitly marked `[Pending: ...]`. Draft text is not a
claim that these experiments have been performed.

## Build

Use a current full TeX Live or MacTeX installation with `latexmk`, `biber`,
Tempora, biblatex-ieee and the packages loaded by the provided template.
From this directory:

```bash
pdflatex -interaction=nonstopmode -halt-on-error title.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error thesis.tex
```

The included `title.pdf` is already compiled. Edit `title.tex` and rebuild it
when changing the author, supervisor or title. `thesis.tex` is the main file.
The small `IfDocumentMetadata` compatibility definitions support older LaTeX
installations; they do nothing when those commands already exist.

## Update the measurements

Primary repository: https://github.com/bulatsharif/iu-diploma-2027

Reviewed snapshot: `3bd7f18d184cdad8101fff41fdf53125a0fe085f`.
Baseline archive: `reports/baseline_20261013_092255/`.
Experiment code: `db899801ab688ea7c2183785430fa5430bb46a93` plus the archived
`launch-fix.patch`. See `data/provenance.json` for source-file checksums.

The source ZIP contains derived measurements and plotting/table scripts, not
model weights, private runtime files or another copy of the experiment repo.
To rebuild the numerical tables from a separate checkout:

```bash
python scripts/build_results.py --repo /path/to/iu-diploma-2027
python scripts/plot_results.py
```

The extraction script uses only Python's standard library. Plotting requires
Matplotlib (the supplied plots were built with version 3.10.8). Generated
CSV, tables and figures are already included, so Python is not required to
compile the manuscript. Baseline counts and hashes are validated against
the reviewed archive; intentionally revise those checks if replacing it.

The runner's exported token-throughput metric is retained directly. No
aggregate latency quantiles or confidence intervals have been fabricated.
Cancellations are reported separately, and latency distributions cover
completed requests. The unusually low throughput for EN/500/concurrency=1
is preserved and flagged for investigation.

## Where to edit

- `chapters/chapter3.tex`: experimental design, controls and metrics.
- `chapters/chapter4.tex`: implemented software and integration details.
- `chapters/chapter5.tex`: measured results, new comparisons and discussion.
- `chapters/chapter6.tex`: final answers once the experiments are complete.
- `chapters/appex.tex`: full measurements and the remaining-evidence checklist.
- `ref.bib`: all literature and repository citations.

Search for `\pending{` to locate unfinished work. Preserve the distinction
between a prepared launcher and a completed experiment. Add repeated trials,
quality evaluation and matched controls before claiming final acceleration.
