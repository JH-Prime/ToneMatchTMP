# Independent read-only analyzer review: v0.1.05

Reviewed: 2026-10-13 21:26:25 Asia/Seoul
Reviewer: uncertainty-model worker, not author of analyzer changes
Scope: `voicing.py`, `song_chords.py`, `tests/test_uncertain_chords.py`, `tests/test_chord_reanalysis.py`, and chart/persistence integration.
Initial Verdict: Request one bounded repair before release; no other actionable issue found in this review.
Current Verdict: P2 resolved in the October 14 bounded re-review; no remaining actionable finding in the reviewed analyzer scope.

## P2: Bound new CQT uncertainty segmentation to the result model limit

Location at review time: `song_chords.py:281`; related new identity grouping at `voicing.py:576`; downstream limit `chord_edits.py:49`.

Candidate-aware unknown grouping can now create one event per 50ms observation when local unresolved candidates fluctuate. CQT returns `_merge_events` without an event limit. The correction/effective-view model accepts at most 10,000 events, and the application's result display calls that model. Consequently a valid bounded-length analysis can finish but fail on display with `ValueError: Invalid chord corrections`. Save/reopen has the same collection limit. Previously all unknown observations merged together, so introducing candidate-sensitive grouping increases the reachable failure surface.

Headless reproduction executed during review:

1. Classify ideal C and D major chroma using the real classifier, then convert each to an unknown observation with `_unknown_window` (preserving its own candidate).
2. Alternate these observations 10,002 times, with `_start_seconds = index * .05 - .3` and `_evidence_seconds = .05`.
3. Run the real `_smooth_labels` and `_merge_events(..., .05, .6, 500.1, include_shapes=False)`.
4. Convert resulting dataclasses to dictionaries and call the real `effective_voicing`.

Observed: `{'observations': 10002, 'events': 10002, 'known': 0}`, followed by `ValueError: Invalid chord corrections`. This is a deterministic model-path reproduction, not a claim that a particular real song generates this exact flicker.

Recommended repair: Apply a conservative event budget on the CQT output path that remains compatible with existing rendering, correction, file-size, and import limits. Preserve timeline duration and use the explicit `output_limit` reason without pretending omitted regions were analyzed as a particular chord. Add a regression proving dense uncertain observations can pass the effective-view and JSON reopen contracts. Do not merely raise one downstream limit while leaving the others inconsistent.

## Verified properties and limits

- Twenty focused tests passed in 0.191 seconds: uncertainty analyzer (5), bounded recovery (5), and model/persistence (10). Warnings treated as errors; Tk and Toplevel creation patched to fail. No GUI, audio playback, browser, or hardware operation.
- Recovery keeps the selected CQT frontend, reuses its matrix, requires two distinct bounded widths to agree, requires the winner to be an existing primary candidate with observed required tones, and does not overwrite a recognized primary result. The alternate windows are explicitly not represented as independent confidence measurements.
- Unknown conversion removes `reanalysis_recovered` and code-specific energy claims; optional Boolean import validation agrees with that policy. Unknown reason/candidate grouping preserves contiguous coverage and does not promote alternatives.
- Silence, flat profiles, and single notes retain abstention without candidates in the focused tests. Cancellation is checked between alternate classifications.
- Full source suite, real sample comparison, synthetic quality benchmark, packaging, and release verification are parent-owned and not independently repeated here. No native visual layout checks were performed.
- CQT kernels have finite temporal support around the selected aggregation interval; this review does not claim exact acoustic independence across adjacent harmonies or real-world chord accuracy.

No production edits were made during this review. This receipt is the only review write.

## Bounded re-review: P2 resolved

Reviewed: 2026-10-14 20:39:36 Asia/Seoul

The parent added a 4,096-event CQT output budget using the existing timeline limiter and explicit `event_count_before_limit`, `events_truncated`, `max_events`, and limiting-policy diagnostics. Omitted intervals use `output_limit` and do not keep misleading candidates. The unchanged early return preserves all events and evidence below the budget. Selection now updates its greedy timeline count from immediate neighbors in constant time per ranked event, avoiding repeated sorting/scanning of the growing retained set. The rank sort remains O(N log N). I independently inspected the repair and the parent's 100-case differential test against the previous full-gap-scan decision rule.

Verification executed independently after the repair:

- Twenty-two focused tests passed in 1.091 seconds with warnings-as-errors and hard Tk/Toplevel guards: uncertainty analyzer (6), bounded recovery including the dense CQT integration case (6), model/persistence (10).
- A 20-minute, 24,001-event unknown-candidate timeline reduced to one explicitly output-limited unknown event. The limiter took 0.1954 seconds in this run; its indented JSON fixture was 687 bytes.
- A 20-minute, 24,001-event recognized-chord timeline reduced to 4,096 events. The limiter took 0.1791 seconds in this run; its indented JSON fixture was 2,917,983 bytes, below the existing 8 MiB import limit.
- Both dense fixtures preserved start=0, end=1200 seconds, every adjacent boundary, and total covered duration. Both passed real `effective_voicing` and real `load_result` using an in-memory file stream; no temporary audio or result files were required.
- `git diff --check` passed. No production files were edited during re-review.

The probes test timeline/model/import contracts, not transcription accuracy. Exact timings are observations from this machine, not guaranteed latency. Full acoustic quality and release gates remain parent-owned as stated above. No remaining actionable analyzer finding was identified in this bounded re-review.
