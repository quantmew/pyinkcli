# Sanitize ANSI Case Audit

This document tracks parity between:

- `js_source/ink/src/sanitize-ansi.ts`
- `js_source/ink/test/sanitize-ansi.ts`
- `src/pyinkcli/sanitize_ansi.py`
- `tests/test_sanitize_ansi.py`

## Status

JS explicit test count: `29`

Python explicit test count: `32`

Python covers the explicit JS sanitize cases and adds a few parity-adjacent defensive checks that reflect the current Python runtime layering.

## Case Matrix

| JS case | Python status | Python test |
|---|---|---|
| preserve plain text | Matched | `test_sanitize_ansi_returns_plain_text_unchanged` |
| preserve SGR sequences | Matched | `test_sanitize_ansi_preserves_sgr_sequences` |
| preserve OSC hyperlinks | Matched | `test_sanitize_ansi_preserves_osc_sequences` |
| preserve OSC hyperlinks terminated by C1 ST | Matched | `test_sanitize_ansi_preserves_osc_hyperlinks_terminated_by_c1_st` |
| preserve C1 OSC hyperlinks terminated by C1 ST | Matched | `test_sanitize_ansi_preserves_c1_osc_hyperlinks_terminated_by_c1_st` |
| preserve C1 OSC hyperlinks terminated by ESC ST | Matched | `test_sanitize_ansi_preserves_c1_osc_hyperlinks_terminated_by_escape_st` |
| preserve C1 OSC hyperlinks terminated by BEL | Matched | `test_sanitize_ansi_preserves_c1_osc_hyperlinks_terminated_by_bel` |
| strip non-SGR CSI sequences as complete units | Matched | `test_sanitize_ansi_strips_non_sgr_csi_with_intermediate_bytes` |
| strip C1 non-SGR CSI sequences as complete units | Matched | `test_sanitize_ansi_strips_c1_non_sgr_csi_sequences_as_complete_units` |
| preserve C1 SGR CSI sequences | Matched | `test_sanitize_ansi_preserves_c1_sgr_csi_sequences` |
| strip private-parameter m-sequences that are not SGR | Matched | `test_sanitize_ansi_strips_private_parameter_m_sequences_that_are_not_sgr` |
| strip tmux DCS passthrough wrappers with escaped ST payload terminators | Matched | `test_sanitize_ansi_drops_tmux_passthrough_control_string` |
| strip incomplete DCS passthrough sequences to avoid payload leaks | Matched | `test_sanitize_ansi_strips_incomplete_dcs_passthrough_to_avoid_payload_leaks` |
| strip DCS control strings with BEL in payload until ST terminator | Matched | `test_sanitize_ansi_strips_dcs_and_c1_controls_but_keeps_osc` |
| strip ESC SOS control strings as complete units | Matched | `test_sanitize_ansi_strips_esc_sos_control_strings_as_complete_units` |
| strip ESC SOS control strings with C1 ST terminator | Matched | `test_sanitize_ansi_strips_esc_sos_control_strings_with_c1_st` |
| strip C1 SOS control strings as complete units with C1 ST terminator | Matched | `test_sanitize_ansi_strips_c1_sos_control_strings_with_c1_st` |
| strip C1 SOS control strings as complete units with ESC ST terminator | Matched | `test_sanitize_ansi_strips_c1_sos_control_strings_with_escape_st` |
| strip ESC SOS with BEL terminator as malformed control string | Matched | `test_sanitize_ansi_strips_esc_sos_with_bel_as_malformed_control_string` |
| strip C1 SOS with BEL terminator as malformed control string | Matched | `test_sanitize_ansi_strips_c1_sos_with_bel_as_malformed_control_string` |
| strip incomplete ESC SOS control strings to avoid payload leaks | Matched | `test_sanitize_ansi_strips_incomplete_esc_sos_to_avoid_payload_leaks` |
| strip incomplete C1 SOS control strings to avoid payload leaks | Matched | `test_sanitize_ansi_strips_incomplete_c1_sos_to_avoid_payload_leaks` |
| strip SOS with escaped ESC in payload until final ST terminator | Matched | `test_sanitize_ansi_strips_sos_with_escaped_escape_in_payload_until_final_st` |
| preserve SGR around stripped SOS control strings | Matched | `test_sanitize_ansi_preserves_sgr_around_stripped_sos_control_strings` |
| strip ESC ST sequences | Matched | `test_sanitize_ansi_strips_esc_st_sequences` |
| strip malformed ESC control sequences with intermediates and non-final bytes | Matched | `test_sanitize_ansi_strips_malformed_esc_control_sequences_with_intermediates` |
| strip incomplete CSI after preserving prior SGR content | Matched | `test_sanitize_ansi_strips_incomplete_csi_after_preserving_prior_sgr_content` |
| strip standalone ST bytes | Matched | `test_sanitize_ansi_strips_standalone_st_bytes` |
| strip standalone C1 control characters | Matched | `test_sanitize_ansi_strips_standalone_c1_control_characters` |

## Python-only Defensive Cases

These are not direct JS title mirrors, but they close parity-adjacent gaps:

- `test_sanitize_ansi_preserves_colon_sgr_sequences`
- `test_sanitize_ansi_strips_cursor_movement`
- `test_sanitize_ansi_drops_pm_and_apc_control_strings`

## Upstream Call-Site Notes

The most important current Python-side sanitize call sites are:

- `src/pyinkcli/dom.py` `squash_text_nodes()`
- `src/pyinkcli/measure_text.py`
- `src/pyinkcli/wrap_text.py`
- `src/pyinkcli/utils/wrap_ansi.py`
- `src/pyinkcli/output.py`
- `src/pyinkcli/ink.py`

This is intentionally broader than the immediate JS call-site shape because Python now uses layered defense for runtime safety.

## Residual Differences

- Python includes a few additional defensive tests beyond the JS title set.
- Python runtime intentionally applies sanitize at more layers than the current JS source layout, to guard imperative writes and transformer output.
- Parity questions for sanitize are now less about behavior gaps and more about whether future runtime changes keep using the same shared sanitizer/tokenizer primitives.
