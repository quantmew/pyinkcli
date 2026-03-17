# ink Dependency Source Map

This file maps `js_source/ink` to the third-party source trees cloned under `js_source/`.

## Direct dependencies used to translate ink

| Package | Source directory |
| --- | --- |
| `@alcalzone/ansi-tokenize` | `js_source/@alcalzone/ansi-tokenize` |
| `ansi-escapes` | `js_source/ansi-escapes` |
| `ansi-styles` | `js_source/ansi-styles` |
| `auto-bind` | `js_source/auto-bind` |
| `chalk` | `js_source/chalk` |
| `cli-boxes` | `js_source/cli-boxes` |
| `cli-cursor` | `js_source/cli-cursor` |
| `cli-truncate` | `js_source/cli-truncate` |
| `code-excerpt` | `js_source/code-excerpt` |
| `es-toolkit` | `js_source/es-toolkit` |
| `indent-string` | `js_source/indent-string` |
| `is-in-ci` | `js_source/is-in-ci` |
| `patch-console` | `js_source/patch-console` |
| `react` | `js_source/react` |
| `react-devtools-core` | `js_source/react-devtools-core` |
| `react-reconciler` | `js_source/react-reconciler` |
| `scheduler` | `js_source/scheduler` |
| `signal-exit` | `js_source/signal-exit` |
| `slice-ansi` | `js_source/slice-ansi` |
| `stack-utils` | `js_source/stack-utils` |
| `string-width` | `js_source/string-width` |
| `terminal-size` | `js_source/terminal-size` |
| `type-fest` | `js_source/type-fest` |
| `widest-line` | `js_source/widest-line` |
| `wrap-ansi` | `js_source/wrap-ansi` |
| `ws` | `js_source/ws` |
| `yoga-layout` | `js_source/yoga-layout` |

## Additional runtime dependencies cloned recursively

These were not listed directly in `js_source/ink/package.json`, but they appear in the runtime dependency closure of the packages above.

| Package | Source directory |
| --- | --- |
| `ansi-regex` | `js_source/ansi-regex` |
| `bufferutil` | `js_source/bufferutil` |
| `convert-to-spaces` | `js_source/convert-to-spaces` |
| `environment` | `js_source/environment` |
| `escape-string-regexp` | `js_source/escape-string-regexp` |
| `get-east-asian-width` | `js_source/get-east-asian-width` |
| `is-fullwidth-code-point` | `js_source/is-fullwidth-code-point` |
| `mimic-fn` | `js_source/mimic-fn` |
| `node-gyp-build` | `js_source/node-gyp-build` |
| `onetime` | `js_source/onetime` |
| `restore-cursor` | `js_source/restore-cursor` |
| `shell-quote` | `js_source/shell-quote` |
| `strip-ansi` | `js_source/strip-ansi` |
| `tagged-tag` | `js_source/tagged-tag` |
| `utf-8-validate` | `js_source/utf-8-validate` |

## Notes

- Total runtime dependency closure currently cloned: `42` packages.
- `react`, `react-reconciler`, `scheduler`, and `react-devtools-core` were cloned as separate directories, but they all come from the same React monorepo.
- `ws` may use `bufferutil` and `utf-8-validate` as native optional accelerators.
- `yoga-layout` is a larger multi-language repo; the JavaScript-facing code is under its `javascript/` area.
