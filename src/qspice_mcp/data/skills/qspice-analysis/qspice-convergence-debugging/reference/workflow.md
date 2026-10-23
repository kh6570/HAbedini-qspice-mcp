In the name of God, the Most Gracious, the Most Merciful

# Convergence workflow

1. **Read the evidence.** `read_log` — identify the exact failure phrase and the time/node where it stopped. Don't guess before reading the log.
2. **Localize.** `inspect_schematic` + `list_components` — find the stage near the failing node (switching node, feedback, high-impedance net, nonlinear device).
3. **Form one hypothesis** from the table below and change **one thing**.
4. **Re-run** `run_simulation`, then `read_log` again. Iterate; change one factor at a time so you know what helped.

## Common causes → fixes

| Log symptom | Likely cause | Fix |
| --- | --- | --- |
| `singular matrix`, floating node | No DC path to ground; dangling net | Add a path to GND (large `R` to ground), fix unconnected pins; verify with `list_components` |
| `timestep too small` | Stiff switching, ideal edges, no parasitics | Add small series R / snubber; soften driver edges; `.options cshunt=1e-12`; relax `reltol` slightly |
| `no convergence` at t=0 | Hard DC operating point | Add `.ic` initial conditions; enable gmin/source stepping; add soft-start to sources |
| Stops mid-transient | Discontinuity / ideal switch chatter | Add hysteresis or RC snubber across the switch; add device parasitics; cap `maxstep` |
| Nonlinear/behavioral (`B`) blowup | Aggressive expression, divide-by-zero | Clamp/limit the `B` expression; add series resistance |
| Trap ringing (numerical oscillation) | Trapezoidal integration on stiff circuit | `.options method=gear` or `.options feather=...` (trap damping factor) |

Open `options.md` before applying a simulator directive. Prefer a physical parasitic over a global tolerance change.

## Verify the fix

After it runs to completion: `read_log` (clean exit, reached stop time) → `list_signals` → `measure_waveform` on the target node to confirm the result is physically sane (for example a buck `V(out)` near its expected regulation point), not just "it ran."

## Conventions

- Read the log before changing anything; change one factor per iteration.
- Prefer adding real parasitics (series R, snubbers) over brute-force tolerance loosening — it's both more convergent and more physical.
- Re-confirm correctness with `measure_waveform`, not just a non-error exit.
