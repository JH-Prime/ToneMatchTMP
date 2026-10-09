# v0.1.02 parent review

Mode: read-only product review. Scope: approved QC, chord-only, CQT tuning and distribution.

- Correctness: device-specific recipes survive localization and saved-result reopening. Chord-only bypasses separation, feature extraction and unsupported-device rejection. Empty tone fields are purpose-aware. Added early range/firmware validation. Old CorOS optional-delay failure was reproduced, fixed and verified across listed versions/routes.
- Readability: separate small QC catalog/recipe module; no generic device framework. Provenance stays alongside factual models. No numerical device parameters are invented.
- Architecture: original mixture remains the harmony source. Existing C++ ABI, separation weights, transport, mixer and PDF implementation are not changed. Shared result consumers preserve old TMP inputs.
- Security: no hardware writes, licensing access or runtime inventory download. Import is explicit, bounded and rejects malformed/duplicate rows. Existing bounded JSON loader and HTML escaping remain. User audio stays local and aggregate reports omit private paths.
- Performance: tuning samples at most 12 seconds. CQT remains batched and cancellable; no whole-song new STFT allocation. No new dependencies. Catalog is a small local JSON read, not a native-code optimization target.
- Verification: 376 unit/integration/UI tests pass with warnings as errors; 246 synthetic frontend cases retain labels. Actual Room335 full/excerpt cancellation/progress/save/reopen/export passes. Coverage is unchanged, not accuracy.
- Visual: native synthetic chart and catalog inspected. Browser blocked file URL; stopped rather than bypassing. HTML generation/content is tested but browser visual is unverified.
- Rollback: retain v0.1.01 portable folder and old analysis files; new QC/chords-only results require v0.1.02. Do not rewrite published assets.

Final release review — 2026-10-09 15:25:13 KST: frozen self-test and independent final ZIP verification passed. All 5448 manifest entries and 88 source inputs match; QC resources, licenses, private-data exclusions, native parity and cold EXE music checks passed. The README next-patch/trademark correction was re-reviewed and repackaged; final ZIP SHA256 51813FE64515E5B390EB9E3BEDD6BF732C90175EFA197ADAF6F2036833CF960A, 349494192 bytes. No unresolved required product-code or packaging finding. Accept for the explicitly scoped developer prerelease, not as proof of real-song accuracy or clean-machine/audio-hardware quality. Remote publication and digest read-back remain operational delivery steps.

Publication review — 2026-10-09 20:59:10 KST: public release is not a draft and is a prerelease, published at 15:27:07 KST. Remote annotated tag resolves to verified commit 96b579d; all three assets have exact local sizes and SHA-256 digests. Session-handle loss was resolved by read-only inspection, with no duplicate writes. Delivery accepted; only main-only publication records changed after the tag. Known limitations remain explicit.
