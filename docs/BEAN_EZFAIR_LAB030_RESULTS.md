# BEAN × EZ-FAIR Lab 030: 3,000-case dimension/tolerance experiment

**Status:** research-only, experimental branch. Current production-facing extraction behavior is unchanged. No customer drawings, neural training, deployed Q-policy, or model-generated extractor code.

## Actual experiment

- Source revision: `35f3c30452a298e04723192a8d90bacd55c97836`.
- [Full Linux + Windows GitHub Actions run](https://github.com/danieloculus0-bot/EZ-FAIR/actions/runs/39542242747): **both jobs passed** on Python 3.12.
- Calls the actual `extractor_engine.extract_pdf_dimensions` on 3,000 newly generated individual pages across 30 synthetic vector PDFs. This tests text extraction and tolerance association, **not** rotated fonts, OCR, photographed prints, real-world title-block resolution, or balloon positioning.
- Nine synthetic callout types: paired asymmetrical tolerances, single asymmetric, symmetric shorthand, default 2- and 3-decimal tolerances, administrative metadata, reference dimensions, an unresolved note, bare radius and unlabeled dimensions.
- 2,000 training cases with online Q-value updates, followed by a frozen, value-shifted 1,000-case holdout. No oracle truth is passed into the learner before its decision.
- BEAN's experimental policy is **tabular one-step Q-learning** selecting among existing EZ-FAIR extraction, a separate scoped parser, or human review. It does not train an LLM, fine-tune a neural model, or invent extraction code.

## Frozen holdout results (same on Linux and Windows)

| Strategy | Exactly correct cases | Extra balloons | Missing/wrong limits | Reviews | Reward |
|---|---:|---:|---:|---:|---:|
| Existing EZ-FAIR extractor | 444/1000 | 1223 | 223 | 0 | -2561 |
| Scoped parser alone | 778/1000 | 0 | 333 | 111 | 2224 |
| Review everything | 333/1000 | 0 | 1000 | 1000 | -1512.1 |
| BEAN Q-policy selection | **1000/1000** | **0** | **0** | **111** | **3778** |

The dataset uses repeated structural patterns and independently generated numerical values. The policy learns routing for eight observed input-feature signatures. **A perfect result here does not demonstrate generalized intelligence, geometric drawing interpretation, or expected real-customer accuracy.** There is no independently authenticated real-world drawing truth in this experiment.

## Persistent compact ledger and retrieval

[Open all source-linked receipts](../research/bean_ezfair_lab030/35f3c30452a298e04723192a8d90bacd55c97836/README.txt) for the recorded source snapshot. The research records live at `research/bean_ezfair_lab030/35f3c30452a298e04723192a8d90bacd55c97836/` on this branch:

- `events.jsonl.gz`: **all 3,000** full per-case records (including false balloons, missing limits, source line, gold, all three candidate predictions, selected strategy, reward, input features, pre-decision scoreboard, and post-reward Q values). Compressed size about 230 KB.
- `scoreboard.json`: training/holdout breakdown, exact source type, seed, archive/content SHA-256, frozen holdout metrics and Q state count.
- `q-policy.json.gz`: small recoverable terminal learned Q scoreboard, with SHA-256 in the report.

The `--verify` script independently regenerates the fixture truth, re-evaluates all stored strategy outcomes, reconstructs and compares each pre-decision scoreboard and Q-value transition, and re-aggregates every score. Replay passed on both operating systems. The original PDF pages are regenerated from deterministic source text; they are not themselves stored as copies. For long-term reproduction, retain the experiment source revision as well as the ledger.

**Important limitation:** This experiment is in EZ-FAIR's research branch; it is not yet a BEAN Core runtime neural policy or an integrated production extraction selection engine. The next step is blind layout variants, rotated/stacked tolerances, GD&T, unique real drawing cases with permissible data, and full balloon-placement accuracy before considering integration.
