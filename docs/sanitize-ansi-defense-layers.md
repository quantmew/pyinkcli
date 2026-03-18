# Sanitize ANSI Defense Layers

This document records the current Python-side policy for preventing user-provided ANSI control sequences from leaking into layout-sensitive or runtime-sensitive paths.

The target is not "strip all ANSI". The target is:

- preserve safe styling and hyperlinks
- drop layout-affecting and cursor-affecting control sequences
- keep terminal-control output available for internal runtime code only

## Layer 1: Render Input

Purpose: prevent raw user text from polluting measurement and wrapping.

Entry points:

- `src/ink_python/measure_text.py`
- `src/ink_python/wrap_text.py`
- `src/ink_python/render_node_to_output.py`
- screen-reader output in `src/ink_python/render_node_to_output.py`
- public `wrap_ansi()` / `truncate_string()` in `src/ink_python/utils/wrap_ansi.py`

Rule:

- user text is sanitized before width calculation, wrapping, and text-to-output conversion

Effect:

- cursor movement, clears, DCS, PM, APC, standalone C1 controls do not affect layout

## Layer 2: Output Buffer

Purpose: catch anything that slips through text-level sanitization, including transformer-produced strings.

Entry points:

- `src/ink_python/output.py`

Rule:

- `Output.write()` sanitizes incoming text
- transformed line output is sanitized again just before being converted to styled cells

Effect:

- `Transform` and other output transformers cannot inject unsafe control sequences into the virtual terminal buffer

## Layer 3: App Writes

Purpose: protect user-facing imperative write APIs.

Entry points:

- `src/ink_python/hooks/use_stdout.py`
- `src/ink_python/hooks/use_stderr.py`
- `src/ink_python/ink.py` via `_write_to_stdout()` / `_write_to_stderr()`

Rule:

- default `write()` paths sanitize user data
- explicit `raw_write()` exists only for internal terminal control output

Effect:

- app context and hooks cannot accidentally write raw user ANSI control sequences to stdout/stderr

## Layer 4: Debug Writes

Purpose: protect debug/static-output composition even if an upstream layer regresses.

Entry points:

- `src/ink_python/ink.py` `_on_render_callback()`

Rule:

- sanitize `RenderResult.output` and `RenderResult.static_output` before debug/non-interactive/intermediate composition

Effect:

- debug mode and static-output concatenation have a final defensive boundary

## Allowed Raw Control Paths

Raw terminal control output is still necessary for Ink internals.

Current intentional raw paths:

- cursor show/hide
- alternate screen enter/exit
- synchronized output wrappers
- low-level log update cursor sequences

These must stay on explicit raw/internal paths and should never be reachable through generic user text APIs.

## Maintenance Rule

When adding any new path that accepts user-provided text, place it into one of the four layers above.

If a path writes directly to a stream:

1. decide whether it is user text or terminal control
2. if user text, sanitize it
3. if terminal control, keep it on an explicit raw/internal API

Do not introduce mixed paths that sometimes treat data as user text and sometimes as raw terminal control without an explicit API split.
