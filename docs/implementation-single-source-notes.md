# Implementation Single-Source Notes

This note records modules that should stay single-source during parity work.

The purpose is to avoid repeating the earlier `squash_text_nodes` drift, where
multiple implementations existed and could diverge silently.

## Current Single-Source Anchors

### Text squashing

Canonical implementation:

- `src/ink_python/dom.py` -> `squash_text_nodes()`

Compatibility wrapper only:

- `src/ink_python/squash_text_nodes.py`

Rule:

- if squash behavior changes, update `dom.py`
- do not reintroduce a second full implementation in the wrapper module

### ANSI tokenization

Canonical implementation:

- `src/ink_python/ansi_tokenizer.py`

Rule:

- control-string parsing must be implemented here
- do not add separate structural ANSI parsers in other modules

### ANSI sanitization

Canonical implementation:

- `src/ink_python/sanitize_ansi.py`

Rule:

- entry points may call `sanitize_ansi()`
- they should not reimplement selective filtering locally

### Text wrapping

Canonical runtime-facing wrapper:

- `src/ink_python/wrap_text.py`

Low-level convenience module:

- `src/ink_python/utils/wrap_ansi.py`

Rule:

- runtime code should prefer `ink_python.wrap_text.wrap_text()`
- `utils.wrap_ansi.wrap_text()` is a compatibility wrapper only
- `utils.wrap_ansi` remains the low-level primitive layer and should not grow separate runtime policy

### Output styled surface

Canonical implementation:

- `src/ink_python/output.py`

Rule:

- styled-cell conversion and final stringification live here
- `_stringify_cells()` is the explicit styled-cell -> ANSI boundary inside this module
- if this area is refactored, move behavior rather than clone it elsewhere

## Current Scan Result

As of this note:

- no second `squash_text_nodes` implementation remains
- no second low-level ANSI tokenizer implementation remains
- sanitize routing is shared through `sanitize_ansi()`

## Maintenance Rule

Before adding a new helper that sounds like an existing primitive:

1. check whether a canonical implementation already exists
2. extend it if possible
3. use wrappers/reexports instead of copying logic
