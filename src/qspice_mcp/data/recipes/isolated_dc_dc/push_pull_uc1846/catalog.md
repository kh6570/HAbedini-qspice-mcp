# UC1846 Current-Mode Push-Pull Converter (Open Loop) -- reference recipe (Track B)

Push-pull isolated converter driven by a behavioral UC1846 current-mode PWM
controller model, run open loop. The output settles near 5 V.

**Source:** [Qspice-6](https://github.com/marcosalonsoelectronics/Qspice-6) by
J. Marcos Alonso -- file `1.- UC1846 - push-pull-current-mode-open-loop - new.qsch`
@ `26c947c`. Adapted and redistributed with the author's permission.

> This recipe ships Alonso's **corrected** ("- new") schematic revision. The earlier
> revision of this circuit failed the QSpice bias point at t=0; the corrected schematic
> converges cleanly with no extra solver options.

## Files

- `push_pull_uc1846.qsch` -- Alonso's corrected QSpice schematic (source of truth).
- `push_pull_uc1846.cir` -- self-contained netlist ready to simulate.
- `UC1846.sub` -- Alonso's behavioral UC1846 controller model, referenced by the
  netlist via `.lib UC1846.sub`.

## Materialize and simulate

1. `materialize_reference_circuit(recipe_id="push_pull_uc1846")` -- writes all three files.
2. `run_simulation(source_path="push_pull_uc1846.cir")` -- runs the ready-to-run netlist.
   `UC1846.sub` is resolved from the same folder.
3. `list_signals` / `measure_waveform` on the produced `.qraw`; `V(out)` regulates near 5 V.
- Related topology block: `push_pull_converter` (see `describe_topology_block`).

> Note: the netlist also references QSpice's bundled `NMOS.txt` and `Diode.txt`
> device models by their default install path
> (`C:\Program Files\QSPICE\`). A standard QSpice install satisfies these.
