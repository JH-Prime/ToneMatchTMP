# v0.1.03 parent read-only review

Scope: approved UI/style/font repair, inventory entrypoint removal, genuine original-mixture CQT/FFT selection, method-preserving correction/export and developer release. No new algorithm dependency, separation model or accuracy claim.

Code reviewed: new behavioral tests first, then app/playback layout and state, engine request validation, FFT adapter/cancellation, legacy defaults, JSON validation, i18n/PDF identity, frozen diagnostics and verification tools. Documentation/version/resource changes reviewed separately; function reference is generated.

Findings addressed: extra transport row reduced chart space; two-row layout repaired. Real-source FFT immediate editing rejected tuple events; normalize once at the song-analysis boundary without weakening saved-input validation. Native compact header overlapped; compact layout and callback restoration now covered. Hidden roots cannot prove actual window-manager resize: visual maximize check was interrupted and is not claimed.

Verification: 387 warnings-as-errors tests pass (223.881s), compiled C++ ABI 2 parity passes. Private input stays local/unchanged; public reports are aggregate. Changed-file secret/private-root scan and diff whitespace check pass. Existing v0.1.02 tag resolves to the original commit. Frozen build/archive/release gates are pending, so this is not publication approval yet.

No unresolved blocking source finding. Remaining limitations: no real-song ground truth, no clean-PC/CUDA/physical sound/printing/code-signing evidence. User requires no screen manipulation; all remaining checks must be shell-only and hidden.
