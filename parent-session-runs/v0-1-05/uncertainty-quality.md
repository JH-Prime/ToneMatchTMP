# Independent uncertainty validation checkpoint

Recorded: 2026-10-13 21:24:15 Asia/Seoul
Scope: Approved v0.1.05 plan; synthetic, headless analysis only.
Status: Comparison harness ready; final analyzer integration rerun required.

## Artifacts and reproduction

- Harness: `tools/verify_chord_uncertainty.py`
- Initial receipt: workspace `../work/v105-uncertainty-comparison.json`
- Command: `..\.venv\Scripts\python.exe -B tools/verify_chord_uncertainty.py --methods cqt fft --output ../work/v105-uncertainty-comparison.json`
- Baseline: immutable Git tag `v0.1.04`, loaded in memory using the existing trace helper. No checkout/reset is performed.
- No application window, browser, audio playback, user recording, network access, or production-file edit was used by this validation worker.

## Measured results before alternate-window integration

The initial run completed 16 deterministic audio fixtures for each of CQT and FFT (32 comparisons), with no comparison-gate failures. Correct new recognition in baseline-unknown intervals was 0 seconds; incorrect new recognition was also 0 seconds. This is evidence of no measured recognition regression at this checkpoint, **not evidence of successful audio recovery**. The parent still needs to rerun the harness after alternate-window integration and final source changes.

Clean C, a quiet defining third, detuned Am, C6/Am7 ambiguity, and the C-G power dyad retained their existing interpretation. Low-register transitions, 180 BPM changes, and a silent gap retained the baseline scored durations. Silence, seed-17 white noise, a single A2, the incomplete C-E dyad, and a twelve-note chromatic cluster had no accepted chord or unresolved candidate in either method.

The heavy-noise C stress fixture already has 1.499 seconds of incorrect accepted CQT labels in the baseline; the checkpoint leaves this unchanged. The same FFT fixture recognizes C throughout. These are explicitly visible limitations, not a passing claim about absolute accuracy. The fast FFT fixture likewise retains its existing larger transition errors.

The decaying arpeggio stress fixture remains unresolved at the primary level in both methods. FFT now preserves candidates for 0.6 seconds that previously had none; those candidates are not counted as accepted recognition or as accurate unless their symbols agree with the declared pitch collection. Initial arpeggio onset before all three notes have sounded is excluded from label correctness scoring.

## Counterexample that constrained the design

A read-only experiment on baseline code changed only the CQT evidence width from 0.6 seconds to 0.3 seconds. For three seconds of independent stereo Gaussian noise, seed 17, standard deviation 0.025, sample rate 22050 Hz:

- Default 0.6 seconds: all unresolved.
- Naive 0.3 seconds: falsely accepted A-flat13/C for 0.175 seconds.
- 1.0 seconds: all unresolved.

Short-window acceptance alone is therefore insufficient evidence for recovery. A bounded retry should require original plausible candidates and local required tones, agreement between both independent lengths, stronger support, and the normal temporal guard. These controls should not be relaxed to manufacture a positive recovery example.

## Measurement and acceptance contract

The tool records accepted correct seconds and accepted incorrect seconds separately. It also records unresolved time with candidates, unresolved time without candidates, candidate-hit time, and candidate suggestions in annotated negative intervals. New primary labels intersecting baseline unknown intervals are split into correct and incorrect promotions. Increased named coverage is never used as the pass criterion.

Gates fail on incorrect new promotion, increased incorrect recognized time, increased candidate suggestions in negative truth intervals, or lost correct recognized time on the non-stress controls (one-millisecond rounding allowance). Source hashes, method identity, complete contiguous positive-duration timelines, and a three-candidate bound are checked. The latest harness also rejects source changes during its run; this guard was added after the initial report and must be exercised by the final rerun.

The metric code was separately checked in memory using hand-calculated 0.5-second correct and incorrect promotions, candidate-hit and negative-candidate durations, unknown partitioning, and a deliberately invalid timeline. These checks passed. Existing parent red/green classifier tests supply the behavioral regression proof; this harness supplies measured cross-version audio comparison.

## Limits and next action

These fixtures were inspected during development and are not held-out real-world evaluation data. No Room 335 ground truth exists here, so no real-song accuracy claim is possible. The exploratory smooth/decaying signal sweep did not establish a robust two-window-consensus recovery example; retain abstention if the evidence remains inconclusive.

Rerun after the final analyzer changes, inspect every incorrect or recovered interval, retain all failing cases, then run the existing trace corpus to ensure timing improvements remain intact. This checkpoint does not authorize broad classifier threshold changes, unsupported arpeggio claims, or release publication without the parent plan's remaining gates.
