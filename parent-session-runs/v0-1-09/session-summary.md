# v0.1.09 distribution checkpoint

- Updated: 2026-11-15 18:53:48 Asia/Seoul.
- Status: source implementation and 502 headless tests pass; frozen/MSIX final verification and source push remain.
- Approval: user requested both no-cost SignPath and Store routes, said proceed, and required application to future builds. No repeated scope approval needed.
- Plan: plan/20261114-204042--work-plan--free-signing-store-distribution--v01.md.
- Constraints: no GUI/normalEXE/audio/package installation, no paid services, no private audio/assets uploads. Existing v108 tag b829b446f1aef52a552927e7a022bce9639e9941 and earlier releases remain untouched.
- Version: source 0.1.09 / 2026-11-15. Store package maps to 1.1.9.0 (app major+1). Animation and corrupted portable cache repair remain follow-ups.
- Implemented: default SigningInput produces no public ZIP; explicit Development is unsigned; release paths refuse overwrite. build.ps1 supports explicit Python path and guarded headless tests. Future release policy in AGENTS.md, DISTRIBUTION_KO.md, CODE_SIGNING_POLICY.md and PRIVACY.md.
- Runtime: package_runtime native Windows identity returns packaged/unpackaged/unknown; packaged LocalState/Numba cache outside install; unknown uses user fallback; all portable update entry points block packaged/unknown. Focused 31 tests passed.
- Signing: manual hosted workflow, own root EXE only, source/full-file binding, PE signed-byte envelope comparison, actual Authenticode/publisher/cert/timestamp/product checks; final manifest regenerated. Old Portable-Dev asset name retained for existing clients (red/green integration regression). Foundation enrollment pending.
- Cost: default workflow uploads no artifacts; signing uploads need FREE_CI_STORAGE_CONFIRMED and Foundation approval. Compressed artifacts retained 1 day. Hosted workflow not run; no paid-service assumption.
- MSIX: package_msix CLI validates identity/version/x64/paths, exclusive layout/output, validation-only dummy identity never publishable. 12 tests pass. Official SDK downloaded to work/windows-sdk-buildtools-10.0.28000.2957; MakeAppx valid Microsoft signature. Full new app build still needed before meaningful structural package check.
- Verification: work/v109-headless.json reports 502 passed/91.561s, 92 GUI deferred, zero failures/errors/skips. tools/generate_function_reference.py subsequently changed only generated document title/source list; final source binding requires another appropriate check. SignPath XML passed downloaded official v1 XSD. Logs in work/v109-*.log. No actual signed output, Store identity, package installation or actual-song accuracy claim.
- Workers hit usage limit and independent final review did not complete; parent must review rather than mark independent approval.
- Next: final review/syntax checks and source suite, commit accepted source, build SigningInput using known Zig path, structurally package full onedir via official MakeAppx, update QA/docs with exact receipts, push preparation. Do not publish signed release or Store app until external gates truly pass.

- 2026-11-15 Asia/Seoul — Final accepted source suite: 504 headless tests passed in 74.565 seconds, 92 GUI deferred, source hashes exact. Added red/green repairs for existing updater asset-name compatibility, local-account file exclusion, and private media/model/cache rejection before manifest/MSIX/signing binding. Parent read-only source/tool review completed; independent final review was unavailable due worker usage limits. Frozen and full MSIX verification follow.
