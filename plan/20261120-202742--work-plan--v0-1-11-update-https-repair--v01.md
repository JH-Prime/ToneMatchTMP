# Portable update HTTPS repair work plan

Plan Type: Work plan
Workstream: ToneMatchTMP v0.1.11 frozen HTTPS repair and recovery
Version: 01
Status: Approved delivery and local recovery complete
Created: 2026-11-20 20:27:42 Asia/Seoul
Last Updated: 2026-11-22 20:04:19 Asia/Seoul
Related Plan: plan/20261116-230144--work-plan--v0-1-10-startup-animation--v01.md
Current Completion State: Public v0.1.11 developer artifact verified and desktop v0.1.08 repaired
Completed So Far: 532 guarded tests, independent review, frozen TLS and actual HTTPS, archive/cache checks, publication/readback, old frozen full download and single-file local recovery
Remaining Work: Interactive UI verification remains deferred by user instruction
Current Blockers: None for approved delivery
Next Step: Proceed with separately approved work when its scope is confirmed

## Approved objective and evidence

The user reports that v0.1.08 opens the existing application without a visible update screen even though v0.1.10 has been published. They explicitly approve including the missing security resource in v0.1.11, adding executable HTTPS checks and update failure records, running tests, building a developer ZIP, publishing through the existing GitHub workflow, and repairing the desktop v0.1.08 folder by adding only its missing resource. This approval does not authorize visible application windows, screen manipulation, audio playback, package installation, account enrollment, certificate purchases, or changes to historical releases. Continue without asking for the same approval again.

The reproduced defect is in distribution assembly. The current Python runtime adds a certificate distrust policy in its standard SSL context constructor. It loads the adjacent codex-rejected-cas.pem file before any network connection. The file is a 906-byte trusted-certificate resource whose exact SHA-256 is c916ce1b14ed8ca69e9b5c9fab22799a900dd610d6d4ec9b1347f4fd48e53718. The PyInstaller bundle includes the patched ssl module but omits this data file. A genuine frozen-runtime diagnostic copy of v0.1.08 fails with FileNotFoundError at context construction both before and after importing the application. Pointing only the diagnostic resource lookup at the intact build-runtime file makes release metadata selection and the asset connection succeed. No certificate verification was disabled in this experiment.

The desktop v0.1.08 executable hash matches its published manifest and the original executable remains unchanged. Its installation path maps to the observed local updater cache. That cache contains only the lock file, which was available for locking; there is no damaged installed version or current pointer to repair. The same missing resource is confirmed in v0.1.10. Source-only networking succeeds because the source runtime has the resource. Earlier archive installation checks used local transport fixtures and did not exercise the frozen HTTPS context. Preserve those historical receipts as accurate descriptions of their actual checks, while recording this newly discovered coverage gap in the new release and current guidance.

The old updater catches expected transport failures and the controller returns immediately to the installed application. If this happens before the first idle paint, the user may see no update screen at all. Preserve fallback availability, but stop treating an unobservable failure as adequate diagnostics. Do not misrepresent this as a user network problem, release-channel problem, SmartScreen problem, or a proven skip-update invocation. Do not change chord recognition or claim improvements in real-song accuracy as part of this repair.

## Minimal implementation boundaries

Keep Python, Tkinter, PyInstaller, the standard SSL library, and the established updater architecture. Include the exact security data required by the active build runtime in the location its bundled module expects. Make inclusion conditional on the actual runtime resource so ordinary CPython builds remain supported. Validate SSL context creation in the build environment so a damaged customized build runtime fails clearly rather than generating a knowingly incomplete application. Do not remove the distrust policy, replace system trust with an arbitrary bundle, allow insecure HTTP, disable hostname checking, or relax certificate verification to work around the failure.

Extend the existing frozen offline diagnostic to instantiate a real default HTTPS context and assert required certificate verification and hostname checking. This test must remain entirely offline, without audio devices or windows, and be included in the overall success result used by build acceptance. A missing resource must cause an explicit failing diagnostic rather than an overall success report. Add a small deliberate diagnostic command path to the executable that checks the actual updater HTTPS transport against the fixed project release endpoint. Keep this path before window construction and respect the existing self-test update-bypass rules. It may retrieve bounded release metadata and a minimal asset prefix through the same validated transport, but must not launch another executable, alter installed update caches, download arbitrary addresses, or modify user settings.

Record update failures in a bounded local diagnostic record. Limit recorded facts to controlled stages, exception class names, numeric error information when appropriate, application version, and a timestamp. Do not persist raw exception messages, stack traces, authentication data, signed download URLs, full user paths, audio names, or environmental secrets. Use a single latest record or another explicitly bounded form. Keep writes atomic where practical and ensure record-writing failures never prevent the installed application from opening. Do not weaken existing cache path or symlink guards, write outside the owned updater state, or cause failure logging to erase a valid offline installation pointer. Preserve cancellation precedence and distinguish a deliberate cancellation from a network or packaging error.

Keep the startup animation, brief intro, continue and close controls, package identity restrictions, and original data-directory handoff behavior. Retain the existing archive hash, manifest, file inventory, trusted-host, numeric-version, disk-space, cache-lock, and cancellation protections. Avoid unrelated repairs to the separately recorded damaged-cache recovery problem. Do not create a general networking framework, add retry loops without a demonstrated need, add an unrelated settings UI, or move scientific imports into a new startup architecture. Surgical changes should explain the observed failure and make its recurrence detectable.

## Verification sequence

Start with observable regression checks for missing SSL resources or context-construction failure, secure context settings, bounded transport diagnostics, and safe failure records. Verify both the custom-runtime resource case and the ordinary-runtime absence case without depending on the user's desktop path in repository tests. Use inert fixtures for downloadable archives, never a real executable in unit tests. Ensure a deliberately malformed or failing diagnostic destination cannot break normal fallback. Verify private paths and URL query strings do not appear in persisted failure reports even when an exception contains them. Cover a successful update, an offline fallback, cancellation, and a failure before download. Run relevant existing lifecycle tests after changing any controller or diagnostic arguments.

Use the existing guarded headless runner for the integrated suite. Keep native UI and audio restrictions active and record the intentionally deferred GUI tests. Run tests appropriate to the changed contracts, not repetitive whole-suite runs after documentation-only edits. Separate synthetic correctness tests, packaging verification, online metadata checks, and real-song measurements in all reports. This patch introduces no new actual-song accuracy measurement and no live musical playback. No private Room 335 sample may enter source, developer archives, diagnostics intended for publication, or GitHub assets.

Request an independent review of the resource inclusion, SSL verification settings, failure-record privacy and path handling, and update recovery ordering. Reviewers may inspect code and run guarded checks but must not open application windows. Incorporate bounded material repairs under this approved plan and rerun affected checks. Do not treat a spawned worker, a tool result, or a passing synthetic fixture as proof of the full frozen network path. Preserve concrete receipts with source hashes, commands or diagnostic modes, actual outcomes, and clearly stated limitations.

Build a new v0.1.11 from an accepted source commit using the explicit Development mode. The normal signing-input default remains unchanged. Run the actual frozen offline diagnostics and the dedicated HTTPS diagnostic without constructing Tk or querying audio devices. Independently inspect the resulting archive, including the required resource and manifest entry, source provenance, executable version, licensing, checksums, and absence of private media or local account files. Extract verification copies only into fresh project-owned work directories. Verify installation of the exact new ZIP through the real updater core and offline reuse in an isolated cache. Do not modify the user's live updater cache merely to manufacture a passing result.

## Release and recovery ordering

Preserve every published tag and release asset, including the defective historical bundles. Never replace v0.1.08 or v0.1.10 in place. Increment all runtime and Windows version metadata consistently to v0.1.11, add a new QA report, and update current documentation to explain both the repair and the older-version bootstrap limitation. Existing older executables that cannot create HTTPS contexts cannot download their own repair until the resource is restored or the user obtains a fixed build once. State this plainly rather than promising that publishing alone repairs every old installation.

Push the accepted source normally, create the new immutable v0.1.11 tag, and publish only the intended developer ZIP, checksums, and verification record. Follow the existing publication workflow with explicit artifact integrity checks and preservation snapshots. Download the actual public files without credentials and compare their sizes and hashes with the local accepted artifacts. Verify remote source and tag identities. Keep the developer prerelease clearly unsigned; neither the resource repair nor a successful HTTPS request provides Authenticode signing or removes SmartScreen warnings. SignPath Foundation and Microsoft Store enrollment remain deferred at the user's request, and their future distribution policy remains in force.

Publish and verify v0.1.11 before repairing the user's v0.1.08 folder. Otherwise the repaired old application may download the still-defective v0.1.10 and fail on future launches. The authorized local repair is to add the exact missing runtime resource to the original desktop portable installation only if it remains absent. Verify the original executable hash before and after the repair. If the destination already exists, compare it and stop rather than overwrite unexpected bytes. Keep user settings, logs, audio, analysis results, and the executable untouched. Record that this intentionally repaired local installation differs from its old public manifest by one added resource; do not alter that historical manifest or pretend its exact inventory still matches.

Do not add the resource directly into an already managed update installation. Such an edit would violate the updater's exact manifest inventory and provenance checks. Leave historical caches alone unless a separate confirmed problem requires another explicitly bounded intervention. Check the repaired old runtime through a guarded headless diagnostic that uses the old embedded updater code and the now-present resource. Confirm that it selects the newly published fixed version. If performing a complete download and validation for confidence, use an isolated project cache and do not launch the resulting executable. Disclose that interactive handoff and visual rendering were not observed because the user has not authorized them.

## Documentation, records, and completion

Keep this plan current after implementation, meaningful verification, independent review, artifact assembly, publication, and local recovery. Maintain the corresponding parent-session checkpoint so continuation does not depend on chat history. Add concise Korean release notes and developer guidance about the missing resource, the new failure record, the diagnostic mode, and the exact older-version recovery performed. Update generated function references through the established generator only when needed. Preserve prior QA snapshots and published assets. Repository documentation must not include private desktop paths, raw exception traces containing user paths, or temporary signed URLs; detailed local diagnostic receipts remain in ignored project work directories.

Completion requires the narrow fixes, meaningful passing regression and guarded tests, an independently reviewed source diff, the new versioned unsigned developer package, actual frozen offline and online HTTPS results, archive and public-byte integrity verification, remote publication, and the authorized local v0.1.08 missing-file repair with unchanged executable bytes. Report limitations honestly: normal app windows, animation smoothness, DPI, audio listening, actual-song accuracy, trusted signing, and Store certification remain untested or deferred as applicable. Do not leave authorized packaging or recovery work unfinished merely because those unrelated external gates remain deferred.

## Scoreboard

Current score: 49/100
Score source: provisional
Last updated: 2026-11-22 20:04:19 Asia/Seoul
Rationale: The confirmed failure is fixed in the public patch and original desktop folder with actual frozen HTTPS and archive verification.
What improved: The old frozen updater verified the public archive and the local repair preserved the original executable and manifest.
What remains unsatisfactory: Interactive update handoff and visual acceptance remain unverified.
Next score-maintenance action: Retain immutable public records and check interactive behavior only within the user-authorized scope.

Score history:

- 2026-11-20 20:27:42 Asia/Seoul — 29 provisional: user approved the concrete repair, frozen transport evidence is conclusive, implementation and recovery remain pending.
- 2026-11-22 19:47:30 Asia/Seoul — 39 provisional: implementation, focused tests and independent review complete. Integrated suite and distribution pending.

- 2026-11-22 19:48:20 Asia/Seoul — 43 provisional: 532 guarded tests passed in 86.136 seconds and all source hashes matched. Packaged verification is next.

- 2026-11-22 20:04:19 Asia/Seoul — 49 provisional: actual frozen HTTPS, public artifact verification and local recovery complete.

## Progress log

- 2026-11-20 20:27:42 Asia/Seoul — Explicit user approval received for v0.1.11 repair, tests, ZIP, publication, and adding the missing resource to desktop v0.1.08. Root-cause receipts are in ignored work/v108-runtime-probe-8rexm11i/result.json. Original executable and live cache were not altered during diagnosis.
- 2026-11-22 19:47:30 Asia/Seoul — Added TLS resource collection, offline context validation, explicit online EXE diagnostic and sanitized update failure record. Added regression tests that fail before the repair. Independent review confirmed PyInstaller data placement, guard ordering and record privacy. Source diagnostic reached GitHub release metadata and read the v0.1.10 archive signature with verification enabled. Started the guarded 532-case suite.
- 2026-11-22 19:48:20 Asia/Seoul — Integrated 532-case suite passed with zero failures, errors or skips. GUI 92 deferred. Source hashes verified before the Development build.
- 2026-11-22 20:04:19 Asia/Seoul — v0.1.11 verified and published, three public assets read back, prior artifacts preserved. Repaired the desktop v0.1.08 resource after isolated full public ZIP download and verification by its frozen runtime.
