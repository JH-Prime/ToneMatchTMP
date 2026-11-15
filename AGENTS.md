# ToneMatchTMP release rules

Read the global AGENTS instructions and the active project plan before work.

The user approved two **no-cost** distribution routes and requires this policy
for **every future version**: SignPath Foundation signing for GitHub portable
EXEs, and Microsoft Store signing for Store-distributed MSIX packages. See
[DISTRIBUTION_KO.md](DISTRIBUTION_KO.md), [CODE_SIGNING_POLICY.md](CODE_SIGNING_POLICY.md),
and [PRIVACY.md](PRIVACY.md). Enrollment and certification remain external gates.

- Normal builds prepare unsigned signing inputs; they are not public trusted releases.
- Create an unsigned developer ZIP only with the explicit Development build mode.
  Never describe it as signed, Store-certified, or guaranteed free of SmartScreen warnings.
- Public signed artifacts require verified provenance and actual Authenticode checks.
  Generate manifests, archives, and hashes from the final signed bytes.
- Store packages require the assigned Partner Center identity. Validation-only packages
  are nonpublishable. Store installations must use Store updates and writable user data.
- Never replace existing release files or move a published tag. Increment the application
  version for each patch; preserve old QA snapshots and publication records.
- Use only free standard public-repository CI runners. Do not buy certificates,
  subscribe to paid services, or expose signing credentials in source, logs, or chat.
- Do not launch native UI, play audio, or install packages without the user's permission.
  Use the guarded headless runner for automated checks and disclose deferred UI checks.
- User audio, including the local Room 335 sample, never belongs in source, CI,
  signing artifacts, GitHub releases, or Store packages.

The startup-animation request remains a follow-up after trusted-distribution preparation;
do not silently drop it or claim it is part of the current completed release.
