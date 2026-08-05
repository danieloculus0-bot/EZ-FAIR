# EZ FAIR Tolerance Extraction Redesign

## Purpose

This document defines an independently designed, clean-room tolerance extraction pipeline for engineering drawings. The goal is not to claim perfect automatic interpretation. The goal is to produce structured candidates with traceable evidence, calibrated confidence, and fast human verification.

## Current failure modes

The current implementation recognizes a narrow explicit pattern equivalent to `+value / -value` and otherwise applies title-block defaults according to decimal places. This causes predictable failures:

1. `1.250 ±.005` is not parsed as an explicit tolerance.
2. `1.250 +.010/-.005` may work only when PDF text remains on one logical line and in the expected order.
3. Stacked tolerances, where `+.010` and `-.005` are separate spans above and below the nominal, are not spatially associated.
4. Unilateral forms such as `1.250 +.010/-.000`, `1.250 +.000/-.005`, `1.250 +.010`, and `1.250 -.005` are incomplete or unsupported.
5. Limit dimensions such as `1.245–1.255`, stacked `1.255` over `1.245`, or `MAX` / `MIN` requirements are unsupported.
6. A tolerance found anywhere in a reconstructed line can be applied to every numerical candidate on that line.
7. Default tolerances are global mutable values rather than versioned drawing rules.
8. The parser loses semantic distinctions among nominal, basic, reference, stock size, quantity, datum, note number, surface finish, thread callout, and inspection characteristic.
9. OCR is activated only when vector extraction returns zero characteristics. A mixed or malformed vector PDF can therefore suppress OCR even when many requirements were missed.
10. Raw token geometry is not preserved deeply enough to reconstruct stacked or rotated annotations reliably.

## Design principle

Separate the work into four stages:

1. **Detection**: locate text, symbols, lines, frames, and candidate annotation regions.
2. **Association**: determine which tokens belong to the same requirement.
3. **Interpretation**: parse the associated tokens into a typed requirement.
4. **Resolution**: apply explicit, note-defined, title-block, standard, or user-defined tolerance rules according to precedence.

Do not combine these stages into a single regular expression.

## Source token model

Every extracted text item must be stored before normalization.

```python
SourceToken(
    id: UUID,
    page_index: int,
    text_raw: str,
    text_normalized: str,
    bbox: Rect,
    baseline_angle: float,
    font_name: str | None,
    font_size: float | None,
    source: Literal["pdf_word", "pdf_span", "ocr"],
    confidence: float | None,
)
```

OCR and vector tokens should be merged rather than treated as mutually exclusive sources. Prefer vector text when both sources overlap and agree. Retain both when they disagree.

## Annotation region model

Tokens are grouped into local annotation regions using geometry, not only PDF line identifiers.

Candidate links should consider:

- horizontal and vertical distance
- baseline angle
- overlap along the dimension reading axis
- relative font size
- plus/minus sign proximity
- enclosure by feature-control-frame lines
- leader and extension line proximity
- stacked-token arrangement
- shared prefix or suffix symbols

A simple first implementation can use a spatial index and scored neighborhood graph. Each connected component becomes one or more candidate regions.

## Required tolerance forms

### Symmetric bilateral

- `1.250 ±.005`
- `1.250 +/-.005`
- `1.250 .005` only when a known drawing convention explicitly defines the second value as tolerance

Result:

```text
nominal = 1.250
lower_deviation = -0.005
upper_deviation = +0.005
lsl = 1.245
usl = 1.255
```

### Asymmetric bilateral

- `1.250 +.010/-.005`
- stacked plus and minus values
- double-plus and double-minus deviations where permitted by the drawing

Store signed deviations exactly. Do not assume the lower value is negative merely because it is displayed below the nominal.

### Unilateral

- `1.250 +.010/-.000`
- `1.250 +.000/-.005`
- `1.250 +.010`
- `1.250 -.005`

The one-sided shorthand forms require a documented shop or drawing rule before assuming the omitted side is zero. Otherwise mark them for review.

### Limit dimensions

- `1.245–1.255`
- `1.245 / 1.255`
- vertically stacked upper and lower limits
- `1.255 MAX`
- `1.245 MIN`

Represent limit dimensions without inventing a nominal. A report renderer may optionally display the midpoint, but the canonical record should retain `nominal=None`, `lsl`, and `usl` unless a nominal is explicitly supplied.

### General/default tolerance

Resolve only after determining that no explicit tolerance controls the characteristic.

Precedence:

1. Explicit tolerance attached to the requirement
2. Requirement-specific referenced note
3. Local table or view-specific tolerance
4. Drawing general note or tolerance block
5. Customer/project tolerance profile
6. Manual unresolved state

Never silently apply a software default when the drawing tolerance block was expected but not confidently detected.

### Basic dimensions

Boxed basic dimensions do not receive plus/minus limits by themselves. Store:

```text
requirement_type = BASIC
nominal = value
lsl = None
usl = None
control_source = linked GD&T requirement
```

### Reference dimensions

Parenthesized or explicitly marked reference dimensions should default to `reference_only=True` and should not be treated as acceptance characteristics unless the user overrides the classification.

### Thread requirements

Parse the callout as a structured requirement rather than treating every number as an independent dimension.

Example fields:

- nominal diameter
- pitch or threads per inch
- thread series
- class
- internal/external
- depth
- quantity
- tolerance source

### Surface texture and edge requirements

Surface finish numbers, break-edge values, chamfers, radii, and deburr notes require dedicated parsers and classification. They must not be fed through the generic linear-number parser without context.

## Parser output

```python
ParsedRequirement(
    requirement_type: str,
    raw_expression: str,
    nominal: Decimal | None,
    lower_deviation: Decimal | None,
    upper_deviation: Decimal | None,
    lsl: Decimal | None,
    usl: Decimal | None,
    units: str | None,
    quantity: int | None,
    modifiers: list[str],
    reference_only: bool,
    basic: bool,
    source_token_ids: list[UUID],
    parser_rule: str,
    parser_version: str,
    confidence: float,
    warnings: list[str],
)
```

Use `Decimal`, not binary floating point, for tolerance arithmetic and report values.

## Confidence model

Confidence should be decomposed so the UI can explain uncertainty:

- text confidence
- grouping confidence
- classification confidence
- tolerance confidence
- title-block confidence

Examples that force review:

- OCR and vector text disagree
- more than one plausible tolerance is nearby
- explicit signs were not recognized
- nominal and tolerance use different rotations
- title-block default was inferred from weak text
- unresolved unit system
- a default tolerance was applied to a whole-number dimension without a whole-number rule

## Review interface

Each characteristic review row should show:

- cropped source image
- raw text and token sequence
- parsed requirement
- tolerance source and precedence level
- nominal, deviations, limits, and units
- confidence and warnings
- controls to merge, split, reclassify, or manually capture a region

Manual capture is not a fallback of shame. InspectionXpert's public workflow itself uses user-selected capture regions and correction for dimensions and GD&T. EZ FAIR should offer both automatic candidate discovery and precise region capture.

## Test corpus

Build a synthetic, redistributable drawing corpus covering at least:

- symmetric bilateral
- asymmetric bilateral
- unilateral
- upper/lower limits
- max/min
- stacked tolerances
- horizontal and vertical text
- imperial and metric
- comma decimal OCR cases
- fractions and mixed numbers
- basic and reference dimensions
- thread callouts
- hole patterns and quantities
- chamfers and radii
- title-block defaults
- local notes overriding defaults
- feature-control frames
- poor scans, skew, blur, and broken CAD fonts

Each fixture needs expected token groups, parsed requirements, tolerance source, and limits. Real customer drawings can be used for private regression testing but must not be committed.

## Immediate implementation sequence

1. Add `SourceToken`, `AnnotationRegion`, `ParsedRequirement`, and `ToleranceRule` models.
2. Replace global float tolerance calculations with `Decimal` and a versioned resolver.
3. Implement explicit parsers for symmetric, asymmetric, unilateral, and limit forms.
4. Associate stacked tokens geometrically.
5. Run OCR selectively on suspicious or low-coverage regions even when vector text exists.
6. Add a source-crop review panel.
7. Add synthetic fixtures and parser unit tests before attempting learned models.
8. Record extraction coverage and unresolved candidates instead of reporting only the number of accepted characteristics.

## Later learned extraction

A future optional pipeline can use oriented-object detection followed by structured document parsing. Public research has demonstrated engineering-drawing category detection for GD&T, general tolerances, measures, materials, notes, radii, surface roughness, threads, and title blocks. This should augment, not replace, deterministic parsing and human verification.

Any model must be trained on licensed, synthetic, public-domain, or customer-authorized data. Customer drawings must never be silently pooled into a training set.
