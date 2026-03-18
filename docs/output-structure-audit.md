# Output Structure Audit

This document tracks structural parity between:

- `js_source/ink/src/output.ts`
- `src/ink_python/output.py`

The goal is not only behavior parity, but also clear ownership boundaries for:

- styled-character buffering
- clipping
- transformers
- width accounting
- final string generation

## High-Level Mapping

| JS output.ts responsibility | Python status | Python location |
|---|---|---|
| queue `write/clip/unclip` operations | Matched | `Output.write/clip/unclip` in `src/ink_python/output.py` |
| initialize full output surface eagerly | Matched | `Output.get()` in `src/ink_python/output.py` |
| apply nested clip stack during replay | Matched | `Output._apply_write()` |
| convert line text into styled units | Partially matched | `styled_cells()` |
| use visible width for placement | Matched | `string_width()` driven placement in `write_ansi_line()` |
| clear placeholder cells for full-width chars | Matched | placeholder `StyledCell` writes in `write_ansi_line()` |
| transformer application at replay time | Matched | transformer loop in `_apply_write()` |
| stringify styled output rows at the end | Matched | `styled_cells_to_string()` / `_render_row()` |

## Data Model

### JS

JS uses `StyledChar[]` from `@alcalzone/ansi-tokenize`:

- one styled item per output cell/character
- style list carried on each item
- final rendering via `styledCharsToString()`

### Python

Python uses `StyledCell`:

- `value`
- `width`
- `styles`
- `prefix`
- `suffix`
- `placeholder`

This is not one-to-one with JS `StyledChar`, but it is now serving the same role:

- visible cell ownership
- style stack transitions
- full-width placeholder behavior
- late stringification

## Clip Handling

### JS

- computes widest line and line count with caches
- horizontal clipping via `sliceAnsi()`
- vertical clipping via line slicing

### Python

- horizontal clipping via `slice_ansi_columns()`
- vertical clipping via line slicing
- dedicated `OutputCaches` object for:
  - `string_width(text)`
  - `widest_line(text)`
  - styled-cell expansion

Residual difference:

- Python now has a cache layer, but it is narrower than JS `OutputCaches`:
  - it caches width and styled-cell expansion
  - it does not yet cache higher-level replay/stringify products

## Transformer Handling

### JS

- transformers run after clipping, before tokenization to styled chars

### Python

- same order: clipping first, transformers second, styled-cell conversion last
- extra defensive sanitize runs after transformer output

Residual difference:

- Python intentionally adds sanitize at this boundary as part of the runtime defense layers. This is stricter than the immediate JS structure, but consistent with current Python safety goals.

## Styled Buffer Responsibility

### JS

- buffer is the canonical styled surface
- ANSI tokenization is delegated to upstream library `@alcalzone/ansi-tokenize`

### Python

- buffer is also the canonical styled surface
- tokenizer responsibility is split:
  - `ansi_tokenizer.py` parses terminal control tokens structurally
  - `output.py` converts sanitized ANSI-bearing strings into styled cells

Residual difference:

- Python still has an output-specific "ANSI to styled cells" layer inside `output.py`.
- This is not a duplicate file-level implementation, but it is a second-stage representation pipeline that JS gets from a single upstream library.
- The canonical styled-cell -> string boundary is now explicit via `_stringify_cells()`,
  but Python still owns that boundary internally instead of delegating it to an external styled-char library.

## Stringification

### JS

- `styledCharsToString()` then `trimEnd()`

### Python

- `styled_cells_to_string()` then row-level `rstrip()`

Residual difference:

- Python manually computes style transitions and resets.
- JS delegates this to the upstream styled-char library.

## Current Structural Conclusions

### Already aligned enough

- operation replay model
- clip stack semantics
- transformer timing
- width-aware write placement
- full-width placeholder cleanup

### Still structurally different

- cache layer is smaller than JS `OutputCaches`
- no single external styled-char library; Python keeps its own styled-cell representation and stringifier
- sanitizer is intentionally layered into output replay for runtime defense

## Recommended Next Steps

1. If parity work continues here, the next structural improvement should be widening `OutputCaches` beyond widths/cells into replay-adjacent products where profiling shows repeated work.
2. Keep `ansi_tokenizer.py` as the canonical low-level parser and avoid adding more ad-hoc ANSI parsing elsewhere.
3. Treat `styled_cells()` plus `_stringify_cells()` as the Python equivalent of JS's styled-char conversion/stringify boundary; if future refactors happen, tighten that boundary rather than duplicating parsing logic.
