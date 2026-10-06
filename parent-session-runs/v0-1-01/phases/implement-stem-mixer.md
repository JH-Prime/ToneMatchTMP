# Independent instrument mixer

Mode: write; approved v02 fourth phase, after playback and corrections.
Goal: separate six stems once, retain aligned file-backed estimates, allow gain/mute/solo and individual/mix WAV export.
Read first: separator.py separate_stem_chunks, stem_removal.py safe export helpers, playback.py single-owner output loop, existing app lifecycle tests.
Writable scope: stem_mixer.py, stem_mixer_ui.py, focused tests, narrow playback reader injection and app/i18n integration, dependency/build records when verifying distribution, plan/run records.
Limits: no inference per fader move; no full-track six-stem RAM allocation; 20 minute maximum; cancel preparation/export; exclusive no-overwrite destination commit; shared headroom, not independent stem normalization. Six estimates are not claims of exact instrument isolation. No audible playback unless explicitly testing output with user awareness.
State: preparation/output worker owns resources, Tk polls queue, stale completions cannot overwrite newer state. Stop and release audio before capture, AI or shutdown; no GUI-thread joins.
Proof: gain/mute/solo arithmetic, alignment and finite PCM validation, common clipping protection, selected-range and cancellation cleanup, collision-safe export, fader changes do not rerun separation; hidden real Tk plus fake device/model boundary.
Review: bounded read-only pass, one narrow repair if material findings, then resume approved PDF phase.
