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
