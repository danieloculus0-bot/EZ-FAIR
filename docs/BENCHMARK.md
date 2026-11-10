# Local extraction benchmark

The synthetic CI example measures the **benchmark machinery**, not customer drawing
accuracy. No real, proprietary or uncleared drawings may be committed, uploaded
as CI artifacts, logged, or used in public PR discussion.

1. Create a private local folder with cleared or synthetic PDF drawings.
2. Make a JSON file matching `docs/examples/demo_benchmark.json`; enter
   each ground-truth characteristic after human review. Keys are `page`
   (1-based), `type`, `nominal`, optional `abs_tol` and
   `source_contains`. Every PDF must have at least one expected entry.
3. Run `python tools/evaluate_extraction.py --manifest PATH_TO_LABELS.json
   --output LOCAL_REPORT.json` from the repository root.
4. On a genuinely representative held-out set, compare precision, recall,
   and source-rectangle traceability. Add thresholds with
   `--min-precision`, `--min-recall`, and `--min-traceability` only
   after the acceptance criteria are agreed.

Precision is correctly matched candidates / all extracted candidates;
recall is correctly matched candidates / all manually labeled expected
characteristics. Matching currently uses page, characteristic type, nominal
and optional source substring. It is not a GD&T semantic correctness metric.
Source-rectangle traceability only verifies a finite rectangle on a source
page with nonempty provenance. **It does not prove correct balloon placement,
tolerance resolution, drawing interpretation, or actual inspection results.**

Compare the same frozen dataset after every parser change. Keep difficult
vector-only, scanned, fractional, weld, thread and GD&T cases separate in the
private dataset so error classes can be examined. Humans must review outputs.
