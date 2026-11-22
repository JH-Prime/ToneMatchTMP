# v0.1.11 portable updater HTTPS repair

- Updated 2026-11-22 19:47:30 Asia/Seoul.
- Approved plan: `plan/20261120-202742--work-plan--v0-1-11-update-https-repair--v01.md`.
- Cause confirmed in v0.1.08 and v0.1.10: customized SSL constructor needs its adjacent `codex-rejected-cas.pem`, which the previous bundle omitted. Root-cause receipt is in ignored `work/v108-runtime-probe-8rexm11i/result.json`.
- Implementation and focused review complete: TLS resource collection from the build runtime, secure offline TLS check, `--self-test-update-https <report.json>`, and one sanitized local `last-failure.json` under the updater lock. Source-level live HTTPS probe passed. Real GUI and audio remain deferred.
- Next: guarded suite, accepted source commit, explicit Development build, fresh extracted EXE offline and online checks, exact ZIP update and cache reuse, verified GitHub publication, then add the matching file to the desktop v0.1.08 and test the old embedded updater without handing off to a window.
- Separate feature request: title/key prompt, pasted editable and transposable chart, and practice accompaniment. The feature remains outside the approved repair patch. Its scope confirmation was requested separately.

- 2026-11-22 19:48:20 Asia/Seoul: 532 guarded tests passed in 86.136 seconds, 92 GUI cases deferred, and source hashes match. Receipt: `work/v111-headless.json`.
