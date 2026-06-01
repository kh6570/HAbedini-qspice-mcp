# Security Policy

## Supported Versions

`qspice-mcp` is in early development (pre-1.0). Security fixes are applied
to the `main` branch only. There is no formal back-port policy yet.

## Reporting a Vulnerability

If you believe you have found a security issue in `qspice-mcp`, please **do
not open a public GitHub issue**. Instead, report it privately to the
project maintainer so the fix can land before the details become public.

- Preferred channel: open a GitHub Security Advisory on the repository
  (Settings → Security → Advisories → New draft advisory).
- Alternate channel: email the maintainer listed in `pyproject.toml`
  (`[project.authors]`).

Please include:

- A clear description of the issue and the affected component.
- Reproduction steps or a minimal proof of concept.
- The version, commit hash, or environment where it reproduces.
- Any suggested mitigation, if you have one.

You should expect an acknowledgement within seven days. We aim to ship a
fix or a public mitigation within thirty days for confirmed issues, and
will credit reporters in the changelog unless they request otherwise.

## Threat Model and Hardening Notes

For the threat model, workspace-sandboxing rules, subprocess-execution
controls, and the path/suffix validation that protects callers from
arbitrary `QSPICE.exe` or `QUX.exe` invocations, see the in-tree security
posture document at `docs/security.md`.

The published [error taxonomy](docs/errors.md) also exposes
`sandbox_violation` and `validation_failed` codes that clients can branch
on to detect refused requests.
