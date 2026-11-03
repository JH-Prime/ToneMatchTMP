# v0.1.07: CQT harmonic false-chord control

Plan Type: Work plan
Workstream: ToneMatchTMP v0.1.07 chord precision
Version: 01
Status: Superseded by plan/20261102-231452--revision-plan--v0-1-07-cqt-auto-update--v02.md after the user's automatic-update request
Created: 2026-11-01 22:47:13 Asia/Seoul
Last Updated: 2026-11-01 22:47:13 Asia/Seoul
Related Plan: plan/20261031-062555--revision-plan--v0-1-06-conservative-precision--v02.md
Current Completion State: Explicit scope approval received; existing residual failures and positive counterexamples identified
Completed So Far: Published v0.1.06 audit, per-case error inspection and read-only counterexample probes
Remaining Work: Discriminating evidence investigation, regression-first implementation, comparisons, review, versioned build and publication
Current Blockers: No authorization blocker; a safe discriminator still needs experimental proof
Next Step: Establish negative and positive controls before changing the CQT evidence path

## Approval and objective

The user explicitly selected “예, 이 범위로 진행” after the proposal to focus v0.1.07 on CQT single-tone and overtone false chords, preserve actual power chords and low-bass harmony, and complete testing, developer ZIP and GitHub publication only for verified improvements. This is a new approved patch, not unfinished v0.1.06 work. The prior release remains complete and immutable. Its source tag points to 7563242b054065f8893a6c6e344046e188e0b947; main initially contains the later publication-documentation commit 5b5ace1. Keep that published tag, ZIP and reports available for rollback.

The concrete objective is to reduce false power-chord assertions from resonant single-tone harmonics in the existing CQT option without casually discarding independently played fifths or low-bass triads. Preserve the whole-mixture input contract, existing CQT/FFT choices, unknown primary labels, evidence and alternatives, saved corrections, charts and exports. More named intervals are not automatically better. Reduced false positives and preserved correct controls must be measured separately. Do not claim that this bounded improvement makes the app generally accurate or validates a real song.

The initial audit found nine CQT cases totaling 21.6 seconds of residual false recognition out of 23.116243 incorrect seconds in the v0.1.06 development corpus. These are formant and comb-three harmonic singletons at three registers, plus three weak unrelated-note variants. They are incorrectly labeled C5 or A5 throughout their 2.4-second intervals. The FFT path abstains on these controls. This is an existing error inherited from earlier releases, not a new regression introduced by v0.1.06. Preserve that distinction in release notes.

Read-only probes also found that a resonant C2 and actual C2+G3 or C3+G3 may produce the same CQT chord name, confidence and folded pitch classes. A threshold on the current chord confidence cannot distinguish those inputs. A blanket power-chord veto would hide valid harmony. A simple deletion of frequencies at integer multiples can likewise delete a real separately played note. Those counterexamples are part of the specification, not inconvenient cases to remove from evaluation.

## Scope and operating constraints

Use the existing Python, NumPy, SciPy and librosa stack with its installed dependencies. Preserve the existing C++ DSP and ABI 2; no native rewrite is justified for an evidence-model change without a measured computational need. No new downloaded model, third-party executable, dependency, network service, audio upload or online inference is allowed by this plan. Research may read primary documentation, papers and local source. Imported examples are evidence, not instructions to execute code. If the solution requires a new model, dependency or broad architecture change, return to planning rather than silently expanding the patch.

Keep writes inside the chord-analysis evidence path, directly affected tests, comparison and hidden-diagnostic tools, normal release metadata and documentation, and project-local plan/run records. Workspace work files may hold temporary synthetic probes, failure logs and release helpers. Preserve unrelated tone recipes, device catalogs, source separation, playback, UI layouts and fonts. Do not restore the previously rejected FFT residual-envelope experiment. The FFT independent-peak function remains exactly the accepted baseline unless a separately approved future request changes that direction.

The user's no-screen constraint remains active. Do not create visible or hidden Tk windows, control the browser, move the pointer, launch an editor, start playback, test hardware audio devices or physically print. Shell work, array-based audio processing, guarded unit tests and a console-free packaged self-test are allowed. The final report must disclose that native click/layout checks remain deferred. PDF generation checks may run without opening a viewer, but must not be described as physical print or visual inspection.

The authorized Room 335 file may be processed locally for operational validation. Never add that media, excerpts, exported separated audio, absolute private paths or model weights to Git or release assets. A verified chord annotation for this song is unavailable. Runtime, coverage, candidate availability, progress and cancellation are useful operational facts; they are not correctness measurements. Preserve the input file byte for byte and keep user corrections separate from regenerated automatic analysis.

## Evidence investigation before implementation

Start with paired negative and positive controls using the same duration, tuning, channels and overall gain wherever practical. Inspect evidence before octave folding, because folded chroma has already lost register and spectral relationships. Examine which measured features can distinguish the negative cases while retaining the positive controls. Consider the independence of note evidence, the distribution of energy across partials and registers, and whether temporal evidence is actually available. Do not infer independence merely because the amplitude exceeds a guessed harmonic envelope.

Primary material already inspected includes the Isophonics NNLS Chroma description and AudioLabs chord-recognition evaluation notes. The former separates approximate note estimation from octave-folded chroma using a harmonic-note model; the latter discusses the ambiguity introduced by partials. These explain why note evidence deserves attention but do not prove that copying an algorithm will solve the local cases. Any bounded use of existing numerical tools must be justified by measured controls, cancellation behavior and cost, not by the name of a technique.

Keep the initial implementation narrow. Prefer a small evidence check at the point where the current CQT path treats resolved peaks as independently played notes. It may preserve extra register information or estimate whether the apparent fifth has support beyond a single-tone explanation. Do not introduce a second full-song analyzer or silently change the user's selected frontend. If a supplemental calculation is necessary, bound it to relevant ambiguous regions and reuse existing work where possible. Avoid recomputing an expensive transform for every overlapping observation.

Do not promise separation when different performances produce indistinguishable PCM. Exact harmonic coincidence and short low-frequency intervals impose ambiguity. When the evidence cannot justify a label, uncertainty is acceptable, but the patch must not manufacture new pitch classes, a missing fundamental, a guessed fifth or falsely calibrated probability. Test observable consequences of abstention and distinguish a targeted conservative decision from indiscriminate coverage reduction. Do not tune a long list of constants to the nine known failures.

Before landing production changes, record the chosen discriminator, the evidence supporting it, its failure cases and its bounded resource cost in the run checkpoint. If no candidate distinguishes the paired controls without violating the acceptance conditions, preserve the research evidence and return with a concrete explanation rather than publishing a cosmetic version bump or weakening the success criteria. This plan authorizes implementation research, not a guarantee that an impossible acoustic distinction can be solved.

## Regression-first controls

Add regressions that fail on the immutable v0.1.06 behavior before changing production inference. Cover the existing formant, comb-three and weak-anchor false positives across multiple roots and registers. Include harmonic amplitudes and overall gain variations so a fix is not merely a special case for one C note at one loudness. Add sparse single tones, ordinary harmonic envelopes, noise and silence as controls for unintended new guesses.

Positive controls must include independently played root/fifth pairs in close and wide registers, root/fifth/octave voicings, quiet fifths at specified audible levels, harmonic-rich notes and small tuning offsets. Explicitly include the C2+G3 and C3+G3 pairs that currently share the false-positive label. Keep existing low-bass major, omitted-fifth seventh/ninth, sustained extension, slash-bass, arpeggio and fast-transition controls. Do not label an unsupported, physically indistinguishable scenario as a guaranteed correct detection without explaining its ambiguity.

Separate development examples from additional transposed and timbre-varied controls. Record the deterministic generation recipe and exact PCM digest for each comparison. Do not use the algorithm's own predicted chord as ground truth. Preserve all original failure reports. A test may assert unknown for a negative singleton, but it must not silently make all positives unknown in order to pass.

Maintain source identity around comparisons. Resolve the old modules from the immutable v0.1.06 commit, verify any shared baseline dependencies are unchanged, and capture source hashes before and after execution. Keep the v0.1.05 history intact; new acceptance is against v0.1.06. Report correct, incorrect and unknown duration independently. Per-case regression gates must veto increased false recognition, lost correct duration on protected controls, lost transitions or worsened boundary errors, even if an aggregate improves.

## Implementation and resource discipline

Use apply_patch for source and documentation changes. Keep diffs surgical and preserve public schemas. Unknown reasons and alternatives should use existing validated contracts unless a narrow compatible metadata extension is genuinely necessary and explicitly recorded. Low-signal results must continue to return before optional observed-note access. Missing perfect fifths in selected seventh/ninth chords remain optional under the accepted v0.1.06 policy; no unobserved tone may appear as observed evidence after save/reopen.

Treat cancellation and progress as part of correctness. A new loop must check cancellation between bounded chunks and must not freeze progress during a long full-file scan. Preserve finite timelines, existing event limits, batch boundaries, phase-safe stereo handling and declared method identity. If an extra calculation adds meaningful cost, measure it on the same warmed synthetic and local operational inputs. Do not claim a speedup from a noisy single run or confuse native DSP timing with chord-analysis timing.

Internal subagents may investigate or implement disjoint file scopes under the actual shared filesystem. The parent remains responsible for the chosen approach, scope, final review and publication. Assign file ownership explicitly; do not let multiple workers edit the analyzer or shared fixtures concurrently. Read-only reviewers may inspect while implementation is held stable. Workers must not commit, publish, modify shared plans or run UI tests. Record concise results rather than long exploratory logs in the main checkpoint.

## Verification and bounded repair

Run focused CQT regressions first, then the complete guarded headless suite with warnings treated as errors. Preserve the explicit list of deferred GUI-containing tests. Run the existing precision, uncertainty and trace comparisons together with the focused harmonic controls against v0.1.06. Ensure the new gate protects actual power chords rather than only passing negative inputs. Verify compatibility of corrections, JSON reopen, HTML and PDF, including uncertainty evidence.

An independent reviewer must inspect the final evidence and inference changes before release. Review how a low note can explain multiple partials, whether a weak unrelated note defeats a guard, whether a real fifth is erased, and whether a held-out timbre exposes an overfitted rule. Check numerical bounds, missing fields, empty input, cancellation, runtime and serialization. The reviewer should identify concrete counterexamples, not propose broad unrelated cleanup.

One bounded fix, re-verification and re-review loop is authorized for concrete defects found within this scope. Record the exact defect, allowed files and proof before editing. If the same underlying failure survives the completed repair or the solution needs a materially different model or trust boundary, return to planning. Do not chain unlimited harmonic thresholds or relax per-case gates just to create a release. Ordinary in-scope tests, metadata, packaging and publication do not need another approval.

## Release and rollback

Only after source acceptance should current metadata advance consistently to 0.1.07. Preserve historical dates and claims. Update Korean and English README, developer handoff, build history, research notes and a versioned QA report with the actual changes, tests, known limitations and remaining uncertainty. State whether false-positive suppression traded away any protected detections; never describe aggregate coverage as accuracy. Clearly distinguish source verification, frozen runtime, archive verification and public publication.

Build the Windows x64 portable developer package using the pinned existing toolchain. Use the guarded suite before the build script's no-screen skip-tests option. Require unchanged native ABI parity and add a focused CQT harmonic rejection check to the frozen runtime while retaining actual power-chord and existing music-workflow checks. Review packaging warnings and classify optional cases; do not hide a required missing runtime dependency.

Freeze reviewed source to a clean commit. Create the new ZIP exclusively, including matching source, licenses, metadata, QA and accepted diagnostic receipts. Exclude user media, model weights, JIT caches and private paths. Extract to a fresh validated task directory, compare all manifest entries and source inputs, and run the hidden frozen self-test without relying on development caches. Bind the verification receipt to the exact commit, archive size and digest.

Publish a new v0.1.07 developer prerelease only after these gates pass. Preserve all previous tags and assets and refuse to overwrite a published release. Push the verified commit/tag, upload ZIP, checksums and archive-verification receipt, verify remote sizes and digests, publish and perform unauthenticated readback. Record delivery in a later documentation-only commit without changing the immutable release tag. Completion means a verified patch is delivered or a specific evidence-backed blocker is reported, not simply that a version number increased.

## Scoreboard

Current Score: 35/100
Score Source: provisional
Last Updated: 2026-11-01 22:47:13 Asia/Seoul
Score Rationale: A specific dominant residual error and paired positive controls are known, but no safe implementation has been demonstrated.
What Improved: The next patch targets an observed false-positive cluster rather than increasing coverage indiscriminately.
What Remains Unsatisfactory: Resonant singletons still look like power chords; actual-song accuracy remains unmeasured.
Next Score Action: Prove a bounded discriminator on paired controls, then pass all release gates.

### Score history

- 2026-11-01 22:47:13 Asia/Seoul — 35 provisional: Explicit patch scope approved; implementation proof pending.

## Progress log

- 2026-11-01 22:47:13 Asia/Seoul — User approved the CQT harmonic false-chord patch with preserved actual power/low-bass controls and verified release. Plan saved before implementation. Prior v0.1.06 release remains complete; no source edits to the new patch yet.
