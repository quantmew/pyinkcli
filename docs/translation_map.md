# JS-to-Python Translation Map

This repository keeps the upstream JS sources in `js_source/` and targets a
Python source tree at `src/pyinkcli/`.

## Ground Rules

- Translation source of truth is upstream JS only.
- No `git`-based inspection of any previous Python implementation is allowed.
- Public names should stay as close as possible to upstream Ink/React export
  names, while Python files keep the package layout expected by this repo.

## Ink Core

The critical Ink execution chain in `js_source/ink/src` is:

`index.ts` -> `render.ts` -> `ink.tsx` -> `components/App.tsx` +
`reconciler.ts` + `renderer.ts` -> `render-node-to-output.ts` / `dom.ts` /
`output.ts`

Recommended translation priority:

1. Runtime core
2. Rendering/layout helpers
3. Public components
4. Public hooks

## Runtime Core Mapping

| JS source | Python target | Role |
| --- | --- | --- |
| `js_source/ink/src/index.ts` | `src/pyinkcli/index.py` | Public entrypoint and export surface |
| `js_source/ink/src/render.ts` | `src/pyinkcli/render.py` | Render API and instance lifecycle |
| `js_source/ink/src/ink.tsx` | `src/pyinkcli/ink.py` | Runtime coordinator |
| `js_source/ink/src/reconciler.ts` | `src/pyinkcli/reconciler.py` | Host reconciler bridge |
| `js_source/ink/src/dom.ts` | `src/pyinkcli/dom.py` | Ink DOM and layout nodes |
| `js_source/ink/src/renderer.ts` | `src/pyinkcli/renderer.py` | DOM-to-output adapter |
| `js_source/ink/src/output.ts` | `src/pyinkcli/output.py` | Buffered output model |
| `js_source/ink/src/styles.ts` | `src/pyinkcli/styles.py` | Public style type surface |

## Rendering/Layout Mapping

| JS source | Python target |
| --- | --- |
| `js_source/ink/src/render-node-to-output.ts` | `src/pyinkcli/render_node_to_output.py` |
| `js_source/ink/src/render-to-string.ts` | `src/pyinkcli/render_to_string.py` |
| `js_source/ink/src/render-border.ts` | `src/pyinkcli/render_border.py` |
| `js_source/ink/src/render-background.ts` | `src/pyinkcli/render_background.py` |
| `js_source/ink/src/measure-text.ts` | `src/pyinkcli/measure_text.py` |
| `js_source/ink/src/measure-element.ts` | `src/pyinkcli/measure_element.py` |
| `js_source/ink/src/wrap-text.ts` | `src/pyinkcli/wrap_text.py` |
| `js_source/ink/src/get-max-width.ts` | `src/pyinkcli/get_max_width.py` |
| `js_source/ink/src/ansi-tokenizer.ts` | `src/pyinkcli/ansi_tokenizer.py` |
| `js_source/ink/src/sanitize-ansi.ts` | `src/pyinkcli/sanitize_ansi.py` |
| `js_source/ink/src/squash-text-nodes.ts` | `src/pyinkcli/squash_text_nodes.py` |
| `js_source/ink/src/colorize.ts` | `src/pyinkcli/colorize.py` |

## Components Mapping

| JS source | Python target |
| --- | --- |
| `js_source/ink/src/components/Box.tsx` | `src/pyinkcli/components/Box.py` |
| `js_source/ink/src/components/Text.tsx` | `src/pyinkcli/components/Text.py` |
| `js_source/ink/src/components/Static.tsx` | `src/pyinkcli/components/Static.py` |
| `js_source/ink/src/components/Transform.tsx` | `src/pyinkcli/components/Transform.py` |
| `js_source/ink/src/components/Newline.tsx` | `src/pyinkcli/components/Newline.py` |
| `js_source/ink/src/components/Spacer.tsx` | `src/pyinkcli/components/Spacer.py` |
| `js_source/ink/src/components/App.tsx` | `src/pyinkcli/components/App.py` |
| `js_source/ink/src/components/ErrorBoundary.tsx` | `src/pyinkcli/components/ErrorBoundary.py` |
| `js_source/ink/src/components/ErrorOverview.tsx` | `src/pyinkcli/components/ErrorOverview.py` |

## Context Mapping

| JS source | Python target |
| --- | --- |
| `js_source/ink/src/components/AccessibilityContext.ts` | `src/pyinkcli/components/AccessibilityContext.py` |
| `js_source/ink/src/components/AppContext.ts` | `src/pyinkcli/components/AppContext.py` |
| `js_source/ink/src/components/BackgroundContext.ts` | `src/pyinkcli/components/BackgroundContext.py` |
| `js_source/ink/src/components/CursorContext.ts` | `src/pyinkcli/components/CursorContext.py` |
| `js_source/ink/src/components/FocusContext.ts` | `src/pyinkcli/components/FocusContext.py` |
| `js_source/ink/src/components/StderrContext.ts` | `src/pyinkcli/components/StderrContext.py` |
| `js_source/ink/src/components/StdinContext.ts` | `src/pyinkcli/components/StdinContext.py` |
| `js_source/ink/src/components/StdoutContext.ts` | `src/pyinkcli/components/StdoutContext.py` |

## Hooks Mapping

| JS source | Python target |
| --- | --- |
| `js_source/ink/src/hooks/use-app.ts` | `src/pyinkcli/hooks/use_app.py` |
| `js_source/ink/src/hooks/use-box-metrics.ts` | `src/pyinkcli/hooks/use_box_metrics.py` |
| `js_source/ink/src/hooks/use-cursor.ts` | `src/pyinkcli/hooks/use_cursor.py` |
| `js_source/ink/src/hooks/use-focus-manager.ts` | `src/pyinkcli/hooks/use_focus_manager.py` |
| `js_source/ink/src/hooks/use-focus.ts` | `src/pyinkcli/hooks/use_focus.py` |
| `js_source/ink/src/hooks/use-input.ts` | `src/pyinkcli/hooks/use_input.py` |
| `js_source/ink/src/hooks/use-is-screen-reader-enabled.ts` | `src/pyinkcli/hooks/use_is_screen_reader_enabled.py` |
| `js_source/ink/src/hooks/use-paste.ts` | `src/pyinkcli/hooks/use_paste.py` |
| `js_source/ink/src/hooks/use-stderr.ts` | `src/pyinkcli/hooks/use_stderr.py` |
| `js_source/ink/src/hooks/use-stdin.ts` | `src/pyinkcli/hooks/use_stdin.py` |
| `js_source/ink/src/hooks/use-stdout.ts` | `src/pyinkcli/hooks/use_stdout.py` |
| `js_source/ink/src/hooks/use-window-size.ts` | `src/pyinkcli/hooks/use_window_size.py` |

## React-family Test Surface

Tests in `tests/` currently pin these Python-side package families:

- `pyinkcli.packages.react`
- `pyinkcli.packages.react_reconciler`
- `pyinkcli.packages.react_devtools_core`
- `pyinkcli.packages.react_router`

These packages need to preserve JS-like symbol names even when the Python
implementation uses snake_case internally.
