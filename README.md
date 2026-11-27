# README: Mikhail feedback

Owner: Mikhail Oet. Last updated: July 22, 2026.

This folder holds the current corrective deliverables for Dang's Paper 2
wavelet-coherence pipeline. Superseded versions live in `Archive\`.

## Current files (use these)

| File | What it is |
|---|---|
| `Technical_Note_Wavelet_Pipeline_Audit_for_Dang_v5.pdf` (and `.docx`) | The technical audit note, version 5: fourteen registered defects (D1 to D14), the quantitative reconciliation against the Paper 1 headline (Section 4.1), the three-family aggregation design (Section 5), and the measurement validation protocol (Appendix A). Read this first. |
| `wavelet_pipeline_corrected_v3.py` | The corrected analysis pipeline. Computes COI-valid AWC, PASC, and CP on a 2 to 256 trading-day grid, builds the three construct families (liquidity, risk, volume), runs the channel, horizon, and firm-type tests with FDR correction, and writes the hypothesis verdict table. Replaces the metric and verdict layers of `aggregated_wavelet_coherence.ipynb`. |
| `family_measurement_diagnostics_v2.py` | The Appendix A validation tests: Cronbach's alpha per family, Horn's parallel analysis, varimax-rotated factor loadings, and HTMT discriminant validity. Run this on the pipeline's output before quoting any family-level verdict. |

## How to run

Dependencies (one-time):

```
pip install numpy pandas scipy statsmodels PyWavelets openpyxl
```

Step 1. Run the pipeline from the folder that contains `final_daily_data.csv`
and `firm_classification.csv` (currently `..\Upload 07 15 2026\`), or edit the
paths at the bottom of the script:

```
python wavelet_pipeline_corrected_v3.py
```

This writes `statistics_tables_corrected_v3\` with per-segment firm metrics
(including the family-average rows), the descriptive Paper 1 continuity table,
and `hypothesis_evidence_summary_corrected.csv`. For a fast first pass, open
the script and set `compute_pasc_cp=False` in the `__main__` block; the AR(1)
surrogates for PASC and CP are the slow part.

Step 2. Run the measurement diagnostics on the full-sample firm metrics:

```
python family_measurement_diagnostics_v2.py statistics_tables_corrected_v3\firm_metrics_full.csv
```

Read the output against the decision rules in Appendix A.6 of the note.

## About `__pycache__` (now deleted)

A `__pycache__` folder briefly appeared here and caused confusion. It was NOT
source code: Python automatically creates a folder with that name, containing
compiled bytecode copies (`.pyc` files), whenever a `.py` file is imported or
run. It is machine-generated, safe to delete at any time, and Python will
recreate it next to the scripts on the next run. If one reappears after
running the code above, ignore it or delete it; the deliverables are only the
plainly named `.py`, `.docx`, and `.pdf` files listed in this README.

## Archive contents

`Archive\` holds superseded material, kept for the record: technical note
versions 1 through 4, pipeline versions 1 and 2, diagnostics version 1, and
the independent parallel review's H1 handoff
(`H1_Code_Logic_Technical_Handoff_2026-07-22.md` / `.docx`), whose findings
are incorporated into note v5 as register items D11 to D14 and Section 4.1.

## Version history (one line each)

1. v1 (July 21): defects D1 to D10; corrected COI-valid metric layer.
2. v2 (July 22): H1 estimand items D11 to D13; family aggregation; Paper 1 continuity table.
3. v3 (July 22): reflective measurement-model framing; Appendix A protocol; diagnostics module.
4. v4 (July 22): three-family map (volume family with three log-transformed indicators).
5. v5 (July 22): quantitative reconciliation (sub-4 percent reconstructions versus the 24.5 percent headline); D14 parallel-pipeline finding; full incorporation of the independent review's handoff.
