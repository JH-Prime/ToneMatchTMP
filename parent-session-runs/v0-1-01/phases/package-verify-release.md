# Package and release verification

Mode: write; approved v02 final phase, after feature implementation and PDF review.
Goal: version 0.1.01 source/frozen verification and immutable developer prerelease, with explicit unverified launch conditions.
Writable scope: catalog/version metadata, app diagnostics integration, music_diagnostics.py and tests, ToneMatchTMP.spec/build.ps1, requirements/license inventory, developer-source and manifest inputs, README/QA/handoff/build history/research docs, release scripts and plan/run records.
Proof: full warnings-as-errors tests; source/frozen CQT, corrections, PCM/mixer and PDF/font self-tests; existing C++ parity; real cached CPU sample separation/cancellation and exported PCM checks; fresh archive hashes/source inputs/frozen execution. Confirm primary remote unchanged before push. Never overwrite published assets.
Safety: no private audio, caches, credentials or logs with absolute user paths in public output. No first-download/GPU/listening/signing/physical-printing claims without evidence. Publish as prerelease while those launch gates remain unverified. No force push. Preserve all old releases.

Bounded repair 2026-10-06: Actual cached-model cancellation raised separator.SeparationCancelled
through StemBank.prepare, while MixerSession only treats StemRemovalCancelled as cancellation.
Scope: stem_mixer.py exception normalization plus tests/test_stem_mixer.py regression. Preserve
all unrelated errors and cleanup, reproduce RED, focused/full tests, repeat actual cancel and
rebuild. Publication stays blocked until this repair and frozen verification pass.

Frozen packaging repair: the new SciPy vendored NumPy namespace dynamically imports its
FFT module via a string; the first EXE music self-test failed with that exact missing module.
Scope: explicit hidden import in ToneMatchTMP.spec, then rebuild and actual frozen CQT
self-test. Do not fall back to FFT or omit CQT testing to bypass a package failure.

Archive-only repair 2026-10-07: librosa collect_all included 54 development-machine
Numba .nbc/.nbi cache files. Exclude those generated caches in build.ps1 and identical
package finalization, update staged build metadata (no compiled application source changes),
regenerate the unpublished archive, and require fresh cache-free CQT self-test. Preserve
the first unshipped archive locally as evidence; never replace any published asset.
Selected skills: git/versioning for safe history, CI/CD for reproducible packaging gates, docs/ADRs for user-facing migration and limits, shipping/launch for rollback readiness, migration for retaining original analyses and separate corrections.
