# Repository governance and publication

The public `ha-homelab/ha-techo5-dot` repository is provisioned through the
organization's existing Terraform repository, not by a separate manual GitHub
repository-creation script. The implementation is in
[Terraform change 72](https://github.com/4alvit/terraform-github-ha-homelab/pull/72),
including `techo5-dot.tf` and its policy tests.

## Managed policy

- Public visibility, wiki enabled, no copied private Git history.
- Secret scanning, push protection and dependency alerts enabled.
- Read-only default workflow token; permissions increased only by individual jobs.
- GitHub-hosted CI for this repository, including public contributions.
- Scoped organization bot access for independent approval and merge automation.
- Protected main: pull request, one independent approval, resolved discussions,
  current required `CI gate`, and no force pushes/deletions.

Bootstrap creates the empty repository first. Reviewed public source establishes
main and its real CI check; the separate Terraform stage then enables the branch
policy. Ordinary later changes use pull requests. Do not reuse bootstrap to bypass
an existing branch policy or broadly apply unrelated infrastructure changes.

## Shared workflows

Python CI, CodeQL/Trivy, approval, merge and review automation call pinned workflows
from [venus-os-ci-toolkit](https://github.com/victron-venus/venus-os-ci-toolkit).
Repository-specific source checks and wake-classifier parity are also required by
`CI gate`. A passing source check cannot substitute for a skipped parity test.
The shared dependency review reads `.github/dependency-review-config.yml` and
rejects newly introduced high/critical dependency vulnerabilities.

The parity job constructs a synthetic model and runs the pinned TECHO5 interpreter.
It needs no household credentials, recordings or personalized model weights. Public
CI does not install firmware, connect to a Dot, or modify Home Assistant.

## Before publishing

Review `git diff --cached`, run `scripts/check_public.py`, and ensure the real
firmware, voice recordings, private state and generated models remain ignored.
This repository's MIT license covers its own code/docs; upstream assets retain
their original licenses. The wiki setting enables future publication, but the
versioned documentation in `docs/` is the current source of truth.
