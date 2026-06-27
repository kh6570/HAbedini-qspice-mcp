# Real QSpice log corpus

These `.log` files were captured from a real local QSpice run (build version
`20260604`, reported via the executable timestamp) and are committed verbatim
except that absolute user paths in the first echoed line were replaced with a
neutral relative netlist name.

They pin the `cli.v1` adapter's log-classification contract
(`tests/unit/adapters/test_log_corpus_contract.py`) so behavior changes stay
deliberate. Regenerate by running the corresponding netlist through
`QSPICE64.exe -o <name>.log <name>.net`.

| File | Scenario | Expected classification |
| --- | --- | --- |
| `healthy.log` | RC `.tran`, clean run | none (success) |
| `fatal.log` | unresolved subcircuit | fatal `SimulationError` |
| `singular.log` | floating node, recovered via Gmin stepping | none (warning, recovered) |

## Synthetic second build (`v2_20271231/`)

We do not have a second real QSpice build, so the `v2_20271231/` logs are
**synthetic** and hand-authored to exercise the per-version classification seam
(`_VERSION_LOG_OVERRIDES` keyed by build `20271231`). They prove that build-specific
signatures classify only when that version is probed and stay invisible to both the
base rules and the real `20260604` corpus.

| File | Scenario | Base rules | Build `20271231` |
| --- | --- | --- | --- |
| `v2_20271231/healthy.log` | clean run | none | none |
| `v2_20271231/convergence.log` | `Gmin stepping did not converge` | none | `ConvergenceError` |
| `v2_20271231/fatal.log` | `Simulation aborted` | none | fatal `SimulationError` |
