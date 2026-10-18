In the name of God, the Most Gracious, the Most Merciful

# Schematic regression fixtures

`regen_layout.json` is the original 26-component layout from the QSPICE MCP
observations reported on 2026-10-12. It includes named references (`Vpwm`,
`Bgate`, `Cbus`) and expression values (`V=...`, `R=...`, and `IC=...`).
Tests apply it in a temporary workspace; the fixture is placement-only and does
not describe the complete wired simulation circuit.
