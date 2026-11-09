# Security policy

This extension runs inside the Harness Maxxing server (root on a standard install) and holds a Dokploy API key, so
security reports are taken seriously.

## Reporting a vulnerability

**Do not open a public issue.** Use GitHub's private reporting:
[Report a vulnerability](https://github.com/Anthony14FR/harness-maxxing-dokploy/security/advisories/new).

Include the version (`manifest.json`), Harness and Dokploy versions, what an attacker can do, and the steps to
reproduce. You get an answer within 7 days; a fix is released as a patch version, and you are credited in the
advisory unless you prefer not to be.

## Supported versions

Only the latest release on `main` is supported: the extension updates itself from the Dokploy page.

## In scope

- The API key leaving Harness's vault (printed, logged, returned, sent to another host).
- A write to Dokploy without the user's confirmation, or on a protected service.
- Code execution or file access through `api.py`, `dokploy.py` or values passed to Dokploy.
- The self-update installing something other than the commit the user confirmed.

Out of scope: Harness Maxxing and Dokploy themselves (report to their projects), and a root session deliberately
going around `--yes` or the protection (documented limit).
