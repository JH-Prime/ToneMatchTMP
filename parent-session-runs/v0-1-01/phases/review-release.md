# Release read-only review

Mode: read-only for product code; writes only this review/checkpoint.
Reviewed at: 2026-10-06 20:15:53 KST (Asia/Seoul).
Scope: cancellation repair, current documentation, package gates and rollback.

- Actual cached CPU mixer completed all six stems and seven aligned PCM16 outputs.
  Cancellation originally escaped as SeparationCancelled. A failing regression now guards
  normalization to StemRemovalCancelled and exactly-once temporary-bank cleanup.
- Focused discovery ran ten mixer/model/UI tests successfully. The incorrect dotted UI
  invocation failed on an existing fixture import; the repository's discovery command passes.
- Read-only rereview: catch is narrow, exception cause preserved, other exceptions continue
  to propagate after cleanup. No suppressed inference failure or fabricated success.
- Actual corrected whole-song run passes: 252.6099 seconds, 65 monotonic progress callbacks,
  source unchanged, bank/export cleanup, real inference cancellation. No listening claim.
- First frozen check exposed SciPy's string-imported array_api_compat.numpy.fft.
  The spec explicitly includes that module. Rebuilt EXE must demonstrate actual CQT;
  source success cannot waive this gate.
- README current behaviors are separated from historical developer records. Corrections,
  headroom, piano-vs-all-keys, original-monitor-only export and explicit PDF viewer semantics
  are explained. 0.0.13 history is unchanged.
- No observed extra product-code repair within this review. Full suite/build/frozen/ZIP checks
  remain mandatory. Publish a developer prerelease, not a claim of validated musical accuracy.
- Remote main still 874aeb18b18aa210401e150b94d220f20a54a802; no existing v0.1 tag.
  Do not force push or replace released artifacts. Final archive receipt is a separate
  release asset to avoid self-referential ZIP hashes.

2026-10-07 01:16:07 KST continuation: repaired build finished successfully.
358 tests / 201.559s, frozen music/C++ self-test and 80 source-input comparison pass.
SciPy hidden-import repair is closed. Actual EXE full-song/cancel and fresh archive remain.
PortAudio upstream notice added; package excludes unused ASIO/other-platform binaries,
retaining only libportaudio64bit.dll. Verify the filtered package with a fresh EXE launch.

2026-10-07 01:27:45 KST: final archive passed 5438 hashes, 80 source/build inputs and
fresh cold CQT/music/C++ self-test after development JIT caches were excluded.
No additional product-code defect remains. Ready for immutable developer-prerelease publication.
