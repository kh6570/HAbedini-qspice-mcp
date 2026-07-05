"""Nox sessions for local quality gates and multi-version testing."""

from __future__ import annotations

import os

import nox

TEST_PYTHONS = ("3.11", "3.12")
NON_INTEGRATION_TEST_ARGS = (
    "-m",
    "not integration",
    # Per-package coverage floors (scripts/check_package_coverage.py) require a
    # deterministic measurement. pytest-randomly reshuffles every run with a fresh
    # seed, which makes order-sensitive coverage (subprocess/watchdog/infra) drift a
    # few points and flip the floors. Pin a fixed collection order for the
    # coverage-bearing runs; developers can still fuzz order via a direct pytest run.
    "-p",
    "no:randomly",
    "--cov",
    "--cov-report=term",
    "--cov-report=xml",
)

nox.options.error_on_missing_interpreters = False
nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["quality"]


def _install_dev_environment(session: nox.Session) -> None:
    session.install("-e", ".[dev,backends]")


def _run_package_coverage_floors(session: nox.Session) -> None:
    session.run("python", "scripts/check_package_coverage.py")


def _run_non_integration_tests(session: nox.Session) -> None:
    session.run("python", "-m", "pytest", *NON_INTEGRATION_TEST_ARGS, *session.posargs)
    _run_package_coverage_floors(session)


@nox.session
def lint(session: nox.Session) -> None:
    """Run Ruff lint checks."""

    _install_dev_environment(session)
    session.run("python", "-m", "ruff", "check", ".", *session.posargs)


@nox.session(name="format")
def format_check(session: nox.Session) -> None:
    """Run Ruff format checks."""

    _install_dev_environment(session)
    session.run("python", "-m", "ruff", "format", "--check", ".", *session.posargs)


@nox.session
def mypy(session: nox.Session) -> None:
    """Run strict MyPy checks for the source tree."""

    _install_dev_environment(session)
    session.run("python", "-m", "mypy", "--strict", "src/")


@nox.session(python=TEST_PYTHONS)
def tests(session: nox.Session) -> None:
    """Run the non-integration pytest suite with coverage."""

    _install_dev_environment(session)
    _run_non_integration_tests(session)


@nox.session
def integration(session: nox.Session) -> None:
    """Run the integration pytest suite on a QSpice-capable host."""

    _install_dev_environment(session)
    if "QSPICE_EXE" not in os.environ:
        session.log(
            "QSPICE_EXE is not set; pytest will rely on host auto-discovery "
            "and skip when unavailable."
        )
    session.run("python", "-m", "pytest", "-m", "integration", "-v", *session.posargs)


@nox.session
def quality(session: nox.Session) -> None:
    """Mirror the local repo quality gate."""

    _install_dev_environment(session)
    for hook_id in (
        "ruff",
        "ruff-format",
        "check-no-third-party-imports",
        "check-test-ci-safety",
        "check-tool-reference-drift",
        "check-mcp-env-drift",
        "check-markdown-docs",
        "check-tool-metadata-casing",
        "check-service-spec-annotation-drift",
        "check-prompts-drift",
    ):
        session.run("pre-commit", "run", hook_id, "--all-files", "--show-diff-on-failure")
    session.run("python", "-m", "mypy", "--strict", "src/")
    _run_non_integration_tests(session)


@nox.session(name="ci-parity")
def ci_parity(session: nox.Session) -> None:
    """Run the unit suite against a clean ``git archive HEAD`` export.

    This catches files that are present in the working tree but missing from
    version control (a common source of "passes locally, fails in CI" drift).
    """
    import tarfile  # noqa: PLC0415
    import tempfile  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    export_root = Path(tempfile.mkdtemp(prefix="qspice-ci-parity-"))
    archive_path = export_root / "HEAD.tar"
    session.run(
        "git",
        "archive",
        "--format=tar",
        "-o",
        str(archive_path),
        "HEAD",
        external=True,
    )
    extract_root = export_root / "tree"
    extract_root.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path) as archive:
        archive.extractall(extract_root)  # noqa: S202

    session.install(f"{extract_root}[dev,backends]")
    session.chdir(extract_root)
    session.run("python", "-m", "pytest", "-m", "not integration", *session.posargs)


@nox.session(name="cold-start")
def cold_start(session: nox.Session) -> None:
    """Assert MCP stdio initialize + tools/list completes within the Cursor budget."""

    session.install(".")
    session.run("python", "scripts/verify_mcp_stdio.py", "30")


@nox.session(name="check-imports")
def check_imports(session: nox.Session) -> None:
    """Verify zero third-party imports in the source and test trees.

    Scans all ``.py`` files under ``src/``, ``tests/``, and ``scripts/``
    for any trace of ``spicelib`` or ``qspice`` (the library, not the
    simulator name used in comments/docs).
    """
    import re  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    FORBIDDEN = re.compile(  # noqa: N806
        r"^\s*(?:import|from)\s+(spicelib|qspice)\b",
        re.MULTILINE,
    )
    EXCLUDE_DIRS = {"__pycache__", ".nox", ".venv", ".git", ".mypy_cache"}  # noqa: N806

    root = Path().resolve()
    violations: list[str] = []

    for directory in ("src", "tests", "scripts"):
        dir_path = root / directory
        if not dir_path.is_dir():
            continue
        for py_file in dir_path.rglob("*.py"):
            if any(part in EXCLUDE_DIRS for part in py_file.parts):
                continue
            text = py_file.read_text(encoding="utf-8")
            for match in FORBIDDEN.finditer(text):
                violations.append(
                    f"{py_file.relative_to(root)}:{match.start()}: {match.group(0).strip()}"
                )

    if violations:
        session.error(
            f"Found {len(violations)} forbidden third-party import(s):\n"
            + "\n".join(f"  - {v}" for v in violations)
        )
    session.log("No forbidden third-party imports detected.")
