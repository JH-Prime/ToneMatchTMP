# v0.1.05 release helper review

Reviewed: 2026-10-18 16:24:19 Asia/Seoul
Mode: Read-only release code audit; this receipt is the only write
Verdict: No version, hidden-execution or immutable-archive blocker found; two release-proof preconditions require explicit binding before publication.

## Scope and evidence

- Reviewed `../work/package_v105.py`, `../work/publish_v105.py`, imported `package_v103.py` and `verify_release_v013.py`, plus manifest generation and the relevant build-script staging/self-test branches.
- A no-bytecode import check confirmed package/checker version `0.1.05`, publisher version `v0.1.05`, matching project paths, and that the old self-test function uses the exact shared checks module whose version was updated by the v105 helper. Merely importing these modules did not run publication, credentials, native validation, extraction, or frozen diagnostics.
- The older helpers' executable entry points remain guarded; their v103/v013 package routines are not called by v105. Only the reusable document list, self-test and source/native/privacy validators are used.
- Finalization requires passing frozen/source/native evidence, matching 348-test source hashes and 32-case uncertainty source hashes, copies final documentation/QA, then regenerates the complete manifest. ZIP uses exclusive `x` creation. Fresh verification rejects unsafe/duplicate/symlink members, verifies every manifest size/hash and exact file set, and excludes user audio, model weights and JIT caches.
- Extracted frozen diagnostics run with `CREATE_NO_WINDOW` and a 240-second timeout. The build-stage frozen diagnostic uses `-WindowStyle Hidden`. Neither path requests playback or native UI interaction. The v105 wrapper additionally requires the uncertainty reopen/export flag.
- Publication checks clean HEAD, local tag equality, matching remote tag and passed QA; an already published release cannot be overwritten. Existing draft assets must already match exact size and digest. Uploaded assets are re-read and compared before and after publication. Credentials remain in memory and are not printed.
- Public source/document/diagnostic/history text is screened for the actual user-profile/project paths. No credentials, networks, GUI/screens, audio hardware, builds or release writes were used in this audit.

## Release-proof closure requested

1. The initial archive receipt did not record the verified source commit. Although package verification compares source/docs to the current checkout and publication checks HEAD against the tag, a later clean commit could separate these facts. Bind the receipt to a clean HEAD `source_commit` and require it to equal the publishing tag commit. Freeze source/docs before packaging.
2. The initial publisher verified the checksum asset's transport digest but not its checksum entries. Validate `SHA256SUMS` content against the actual staged EXE, manifest, frozen diagnostic and final ZIP before publication. This also catches a stale build-only sidecar lacking the final ZIP entry.

The parent accepted these two narrow helper-only hardening changes; re-review remains pending. Existing build.ps1 can overwrite its own version ZIP unless `-SkipZip` is supplied, so retain the already selected `-SkipZip` invocation and let the exclusive v105 packager create the immutable archive.

## Reviewed helper hashes before hardening

- package_v105.py: `65FB92D349416543A1D4E4BE35F19845162D9718A656765C0419B607B8094F0B`
- publish_v105.py: `94AAD5567486AACD6A6F1FFB6CC6556710CD9CE40DD67D948F45BEF16C1A9652`
- package_v103.py: `02EBAB4009B098EBB18BC9142A705D60DCEA3263D6086729E5DE03915A18B5F1`
- verify_release_v013.py: `823CE3CF8F78A1A8F6148BC4B8EFE8A1DD7F8F80950D7375CE01BDB9A7605ACD`

This is a code review, not evidence that the pending frozen build, final ZIP or public release has passed.

## Bounded hardening re-review

Reviewed: 2026-10-18 16:25:59 Asia/Seoul
Verdict: Approved; both requested proof bindings are addressed. No further actionable release-helper finding.

- `package_v105.verify()` now requires a clean checkout before extraction/verification, captures HEAD, and requires the checkout to remain clean with the same HEAD after all verification. The exclusively created receipt records that exact `source_commit` together with the archive hash and size.
- `publish_v105.verify_release_receipt()` requires the verified commit to equal the release tag commit and validates archive version, success, size and SHA-256. These checks occur before draft creation/update.
- `verify_checksums()` builds the exact expected four-entry map from the EXE, manifest and frozen diagnostic read from the ZIP itself, plus the final ZIP bytes. It rejects duplicate, missing, extra and mismatching checksum entries before any draft mutation. It does not trust a potentially stale staging folder.
- Reviewed the offline regression script: one positive scenario, three checksum-negative scenarios and five receipt-negative scenarios. The parent reports all three test methods passed in 0.056 seconds after a failing pre-implementation run. This reviewer did not rerun fixture-writing tests under the read-only scope; independently reran only the no-bytecode import/version-wiring check, which passed.
- Updated helper hashes: `package_v105.py` = `B02A8C60723CEBC766C9281E29C029A3E05627F83C934A3E53849C41DE72D21F`; `publish_v105.py` = `21447044394414DC74699783371B81FED669C4537DF7298AEE42AFD061C1EBFF`; test script = `7FA9B5A309E17604D75C2D7E3C5A689C9185ECC00A5FBED75B3AFCD8FF2348F2`.

All reviewer writes stop after this addendum so the parent can freeze the release commit. Actual archive verification and publication remain parent-owned gates, not implied by this approval.
