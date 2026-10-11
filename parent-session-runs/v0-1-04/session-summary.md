# v0.1.04 chord trace

Status: Complete and published 2026-10-11 23:13:04 KST. 318 headless tests pass; 92 GUI cases deferred. Both local MP3 frontends and fresh archive checks passed. No screen manipulation.
Active plan: plan/20261011-025644--revision-plan--v0-1-04-chord-trace-device--v02.md
Approval: User said “진행ㄹ해” after the v0.1.04 understanding report.
Predecessor: v0.1.03 source commit 41caed5; developer archive verified but not published. Existing dirty documentation belongs to that work and must be checkpointed before new edits.
Scope: CQT timing/context regression, duration-consistent candidate tracing, exact bounded path optimization, headless tests and truthful release evidence.
Next: User acceptance of v0.1.04; any new bug uses v0.1.05. Do not rebuild/replace the immutable published ZIP or tag.
Accepted diagnosis: v0.1.02 and current completion handlers can leave controls disabled if the done event arrives before worker return. Chords-only also intentionally disables the device while idle; user approved both corrections.
Implemented: Terminal done/error events clear the analysis worker before availability checks. Idle chords-only mode allows device selection; unsupported devices do not falsely block chords. Other operations retain their locks and result refresh does not retire active work. Eight test methods passed after reproducing eight failing subcases; native UI tests remain unrun due to the no-screen constraint.
Verification correction: Initial guarded suite selected test_chord_controls by mistake; Tk guard prevented all eight attempted GUI subcases before a window was created. Corrected runner explicitly defers that module, resulting in 318 passing tests and 92 deferred cases. tools/verify_headless.py writes a durable receipt with source hashes.
Evidence: work/v104-headless-tests.json, v104-chord-trace-comparison.json, v104-actual-cqt.json, v104-actual-fft.json (all outside Git until sanitized packaging). Synthetic agreement 90.66% to 99.36%; real-song coverage is not accuracy. Source original preserved.
Review: Independent reviewer found no actionable issues; 23 focused tests passed. Packaged music workflow, CQT/FFT, edits/reopen, mixer/PDF and C++ ABI 2 passed. 17 third-party packaging warnings are disclosed. Checked at 2026-10-11 23:07:15 KST.
Release: https://github.com/JH-Prime/ToneMatchTMP/releases/tag/v0.1.04
Tag commit: 96bae548efd22cc56818e418a3698a04de021264. ZIP 349538383 bytes, SHA-256 49AD63DB4480DEDE045CBB57FD6B5CA961B18B3D77BB65454892CB3C7D12D9C4. Independent extraction verified 5458 files/96 source inputs. Three public assets match local digests. Receipt: release/ToneMatchTMP-v0.1.04-ARCHIVE-VERIFICATION.json and work/v104-publication.json.
Post-publication plan/history edits do not alter the release tag or ZIP. v0.1.03 archive retained unchanged and unpublished; its fixes are included in v0.1.04.
