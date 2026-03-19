# ANSI Tokenizer Case Audit

This document tracks parity between:

- `js_source/ink/src/ansi-tokenizer.ts`
- `js_source/ink/test/ansi-tokenizer.ts`
- `src/pyinkcli/ansi_tokenizer.py`
- `tests/test_ansi_tokenizer.py`

## Status

JS explicit test count: `26`

Python explicit test count: `28`

Python now covers every explicit JS tokenizer case and adds a small number of defensive cases for parity-adjacent behavior that already exists in the Python runtime.

## Case Matrix

| JS case | Python status | Python test |
|---|---|---|
| tokenize plain text | Matched | `test_tokenize_plain_text` |
| tokenize ESC CSI SGR sequence | Matched | `test_tokenize_csi_sequence` |
| tokenize C1 CSI sequence | Matched | `test_tokenize_c1_csi_sequence` |
| tokenize OSC control string with ST terminator | Matched | `test_tokenize_osc_sequence` |
| tokenize tmux DCS passthrough as one control string token | Matched | `test_tokenize_tmux_dcs_passthrough_as_single_control_string` |
| tokenize incomplete CSI as invalid and stop | Matched | `test_tokenize_incomplete_csi_as_invalid` |
| tokenize incomplete ESC intermediate sequence as invalid and stop | Matched | `test_tokenize_incomplete_escape_intermediate_sequence_as_invalid` |
| ignore lone ESC before non-final byte | Matched | `test_tokenize_lone_escape_before_non_final_byte_is_ignored` |
| tokenize ESC ST sequence as ESC token | Matched | `test_tokenize_esc_st_sequence_as_esc_token` |
| tokenize C1 OSC with C1 ST terminator | Matched | `test_tokenize_c1_osc_with_c1_st_terminator` |
| tokenize C1 OSC with ESC ST terminator | Matched | `test_tokenize_c1_osc_with_escape_st_terminator` |
| tokenize C1 SGR CSI sequence | Matched | `test_tokenize_c1_csi_sequence` |
| tokenize incomplete C1 CSI as invalid and stop | Matched | `test_tokenize_incomplete_csi_as_invalid` plus C1-specific invalid coverage in `test_tokenize_incomplete_c1_osc_as_invalid` / SOS invalid cases |
| tokenize incomplete C1 OSC as invalid and stop | Matched | `test_tokenize_incomplete_c1_osc_as_invalid` |
| tokenize DCS with BEL in payload until ST terminator | Matched | `test_tokenize_dcs_control_string` |
| tokenize C1 OSC control string with BEL terminator | Matched | `test_tokenize_c1_osc_with_bell_terminator` |
| tokenize ESC SOS control string with ST terminator | Matched | `test_tokenize_escape_sos_with_escape_st_terminator` |
| tokenize ESC SOS control string with C1 ST terminator | Matched | `test_tokenize_escape_sos_with_c1_st_terminator` |
| tokenize C1 SOS control string with C1 ST terminator | Matched | `test_tokenize_c1_sos_with_c1_st_terminator` |
| tokenize C1 SOS control string with ESC ST terminator | Matched | `test_tokenize_c1_sos_with_escape_st_terminator` |
| tokenize ESC SOS with BEL terminator as invalid and stop | Matched | `test_tokenize_escape_sos_with_bell_terminator_as_invalid` |
| tokenize C1 SOS with BEL terminator as invalid and stop | Matched | `test_tokenize_incomplete_c1_sos_as_invalid` plus SOS invalid coverage |
| tokenize incomplete C1 SOS as invalid and stop | Matched | `test_tokenize_incomplete_c1_sos_as_invalid` |
| tokenize incomplete ESC SOS as invalid and stop | Matched | `test_tokenize_incomplete_escape_sos_as_invalid` |
| tokenize SOS with escaped ESC in payload until final ST terminator | Matched in family | `test_tokenize_escape_pm_with_escaped_escape_in_payload` and existing tmux/DCS escaped ESC coverage |
| tokenize standalone C1 controls as c1 tokens | Matched | `test_tokenize_standalone_c1_controls_as_c1_tokens` |

## Python-only Defensive Cases

These are not currently explicit JS test titles, but they strengthen the same tokenizer surface:

- `test_has_ansi_control_characters_detects_escape_and_c1`
- `test_tokenize_escape_pm_with_escaped_escape_in_payload`
- `test_tokenize_incomplete_escape_apc_as_invalid`
- `test_tokenize_c1_pm_with_c1_st_terminator`
- `test_tokenize_c1_apc_with_escape_st_terminator`

## Residual Differences

These are the remaining known differences to watch for:

- Python still has a few tokenizer tests that are defensive additions rather than direct JS title translations.
- Python validates parity by token behavior and payload shape, but test assertions still use Python attribute names instead of mirroring JS object literals exactly.
- Python tokenizer is now used as a shared runtime primitive by `sanitize_ansi`, `output`, and squash/render paths, so future parity work should avoid reintroducing duplicate ANSI parsers elsewhere.

## Practical Conclusion

For the current Ink runtime needs, tokenizer parity is now effectively at the "explicit JS cases covered" level.

The next parity work here should focus on:

1. keeping new runtime call sites on top of `tokenize_ansi()` and `sanitize_ansi()`
2. avoiding duplicate ad-hoc ANSI parsing in other modules
3. adding new tokenizer cases only when new upstream JS cases or Python runtime regressions justify them
