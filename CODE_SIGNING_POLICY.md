# Code signing policy

Status: preparation for free sponsored signing; **not yet approved or signed**.
The published v0.1.08 executable is unsigned and remains unchanged.

ToneMatchTMP source is maintained in https://github.com/JH-Prime/ToneMatchTMP
under the MIT license. The repository owner, JH-Prime, is responsible for release
authorization. Contributors propose reviewed changes; the account owner designates
the human signing approver. An automated coding agent is not a substitute for the
service's required human release approval. Repository and signing accounts must use MFA.

We intend to apply for the SignPath Foundation open-source program. Acceptance is
not automatic: the Foundation reviews the project's reputation, ownership, licensing,
and verifiable source-to-build chain. We do not claim sponsorship before acceptance.
After approval, add the required attribution to the home and release pages:
“Free code signing provided by SignPath.io, certificate by SignPath Foundation”.
The Foundation certificate identifies SignPath Foundation as the certificate publisher;
it is not a certificate issued to the repository owner personally.

Signing input must come from the reviewed source commit in a GitHub-hosted build.
The first configuration signs only our root ToneMatchTMP executable. It does not
re-sign upstream FFmpeg, Python, Torch, or other third-party binaries. Our native DSP
DLL remains outside the initial signature coverage; it is rebuilt from tracked source
and bound by the archive manifest. Extending signature coverage requires metadata,
policy review, and explicit artifact configuration, not a wildcard over all PE files.

Signed output is accepted only after checking the certificate, approved publisher,
application version, unchanged executable content outside Authenticode fields, and
the complete original build binding. Manifests and final ZIP hashes are regenerated
after signing. Missing credentials, pending approval, an invalid signature, or an
unexpected certificate blocks signed release creation. No previous release is replaced.

Development-only artifacts can remain unsigned when explicitly requested by the build
mode. Their receipts state that fact. A valid signature does not guarantee immediate
SmartScreen reputation. Microsoft Store signing applies only to the Store channel.

For network behavior and local data, see [PRIVACY.md](PRIVACY.md). For build and
enrollment steps, see [DISTRIBUTION_KO.md](DISTRIBUTION_KO.md).

Policy sources: [Foundation conditions](https://signpath.org/terms),
[GitHub build provenance](https://docs.signpath.io/trusted-build-systems/github),
[Microsoft SmartScreen](https://learn.microsoft.com/windows/apps/package-and-deploy/smartscreen-reputation).
