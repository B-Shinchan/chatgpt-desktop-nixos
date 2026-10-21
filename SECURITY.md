# Security and maintenance

This project packages a proprietary vendor application. It cannot audit or guarantee the security of the application, its hosted service, or its downloaded extensions. Use a supported NixOS system and keep its security updates current.

## Reporting

Do not publish credentials, private conversations, or working exploit details in an issue. If this repository offers GitHub's **Security → Report a vulnerability**, use it for packaging vulnerabilities. Otherwise open a minimal issue asking for a private reporting channel without disclosing exploitation details. Report vulnerabilities in the application or hosted service through the vendor's security reporting process.

## Automated updates

Updates use the vendor's HTTPS APT metadata and SHA256-pinned versioned downloads. Nix verifies archive content against the recorded hash. This is not independent verification of the vendor's release signatures and is not a security audit of its binaries.

Builds fail when required native libraries are absent or required application patches no longer apply. Updater and desktop checks, build checks, and an isolated headless launcher check must pass before automated publication. App-specific helper/sandbox checks supplement these. These checks reduce avoidable packaging failures; they cannot prove every application feature or security property.

The test job has read-only repository access and does not retain checkout credentials. Candidate metadata is captured in an immutable artifact before application execution, and the publisher downloads that exact artifact ID only after all checks succeed. A separate fresh job holds `contents: write`, downloads release and lock-pin metadata, validates it, and reconstructs only the version/hash and approved official Nixpkgs pin changes using trusted repository code. It does not execute downloaded application binaries. Commits use normal, non-forced pushes. A concurrent main-branch change can reject the push; the next scheduled run retries from the current branch.

Workflow actions use full commit pins. Dependabot proposes weekly action updates for review. Workflow code runs on `pull_request`, never `pull_request_target` with untrusted code. Do not add personal tokens or broad write permissions to the test job.

## Repository protections

A bot is an automated account; `github-actions[bot]` identifies commits made with GitHub's short-lived workflow token. It has the permissions assigned in each job, not unrestricted account access.

Branch protection is a server-side rule for important branches. The compatible minimum for this direct-publication design is a ruleset targeting `main` that blocks deletion and force pushes. Keep the automatic updater enabled and restrict who has repository write/admin access. Enable GitHub's dependency alerts and secret-scanning/push-protection features where available. Committing CODEOWNERS or a workflow does not enable those settings.

**Do not require every update to arrive through a pull request or require status checks on the generated commit without changing the updater design.** Those rules would reject this bot's direct push. The update job validates the candidate before publication; bot-token pushes do not trigger another push workflow. For stronger mandatory pull-request protection with unattended merging, first arrange a narrowly scoped GitHub App, candidate PR creation, CI on the PR, and auto-merge after required checks. That is a separate authenticated administrator setup; do not bypass rules or introduce a broad personal token as a shortcut.

## Maintenance limits

Routine application releases are automatic after validation. A vendor binary-layout, API, dependency, sandbox, or licensing change may need a packaging decision. A failed update keeps the last published package and remains visible in Actions. Enable GitHub Actions failure notifications for the repository.

The repository's Nixpkgs revision is locked between monthly refreshes. On the first Monday of each month the updater refreshes it and runs the full checks before publication. The publish job permits only the locked commit/hash/timestamp fields of the existing official NixOS/nixpkgs input; it rejects other repositories, changed input graphs, and backwards timestamps. A failed dependency refresh needs a packaging fix and is not published. Following a consumer's Nixpkgs can change dependency versions and is outside the exact lock tested here.

GitHub may delay scheduled runs, disable schedules after 60 days of repository inactivity, or stop jobs because of service/account limits. There is no promise of zero future maintenance or official vendor support for NixOS.
