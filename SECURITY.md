# Private data and supported access

Use existing authorized administration interfaces and supported installation
procedures. This repository does not provide exploits or authentication bypasses.

Keep recordings, personalized weights, device-specific recovery material,
credentials, private addresses and logs outside Git. The `private/` directory and
common artifact formats are ignored. File permissions and `.gitignore` do not
replace reviewing the staged content.

Before publication run `python3 scripts/check_public.py --include-untracked` and
inspect `git diff --cached`. The checker inspects the Git index and working files,
rejects common credential/artifact patterns, and prints locations instead of secret
values. It is a guardrail, not a complete secret scanner.

If a secret is committed, revoke/rotate it before arranging history cleanup.
Do not post the value or a support bundle to a public issue. Report vulnerabilities
privately through GitHub's reporting channel if available; upstream firmware
issues should follow upstream's reporting policy.
