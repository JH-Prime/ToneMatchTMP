# Saved analysis boundary repair

Mode: write; bounded review repair pass 1 under approved v02.
Goal: reject malformed chord evidence before replacing UI state, and retain guitar-tone separation metadata independently from full-mixture chord source.
Scope: chord_edits.py, tests/test_chord_edits.py, related UI regression only if needed, plan and run records.
Evidence: 10 failing subcases in the new tests show non-numeric pitch classes, non-object evidence, invalid alternatives, invalid confidence/bass, excessive end time and lost tone metadata.
Implementation: validate only the supported persisted contract; do not execute/fetch file data or restore private audio paths. Preserve compatible missing legacy fields.
Verify: focused loader/UI tests, full warnings-as-errors suite, read-only review.
Stop: pass plus no repeated material boundary finding. Reopen approval only if the same root cause survives this bounded repair.
