# Playback vertical slice

Role: implementer in the parent session. Mode: write after approved plan.
Goal: user-triggered, bounded local audio playback linked to the existing manual chord chart.
Read first: global AGENTS and routed TDD/incremental skills; current decoder, chart methods, lifecycle handlers, and UI tests.
Writable scope: playback.py, playback_ui.py, tests/test_playback.py, app.py, i18n.py, related chart/playback UI tests, requirements.txt for the necessary output dependency; active plan and session summary. Packaging and license collection follow during the release phase.
Outputs: tested playback behavior, main-thread UI integration, updated progress and acceptance evidence.
Success criteria: no automatic playback, correct source offsets/seeks/loop/end handling, responsive pause/stop/cleanup, safe task exclusion, existing chart evidence preserved.
Validation: focused unittest with real PCM and output fake, hidden Tk integration, affected existing tests, compileall.
Stop condition: material scope change or verification requiring unavailable hardware authority; otherwise proceed to a read-only review and then the next approved slice.
Selected skills: karpathy-guidelines for narrow scope; incremental-implementation for vertical delivery; test-driven-development for transport and lifecycle regression proof.
