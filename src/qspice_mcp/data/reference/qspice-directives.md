# QSpice Directive Cheatsheet

Agent-oriented index of QSpice netlist directives and simulator options.
This is a clean-room summary written for this project; consult the QSpice
in-app help for authoritative syntax. Where an MCP staging tool exists it is
listed — prefer it over hand-editing netlists.

## Analysis directives

| Directive | Syntax sketch | MCP staging tool |
| --- | --- | --- |
| `.tran` | `.tran TSTOP` or `.tran 0 TSTOP [TSTART [MAXSTEP]] [UIC\|SKIPBP]` | `prepare_transient` |
| `.ac` | `.ac <dec\|oct\|lin> N FSTART FSTOP` or `.ac list F1 F2 ...` | `prepare_ac` |
| `.dc` | `.dc [lin\|oct\|dec] SRC FIRST LAST STEP [second dimension ...]` or `.dc SRC list V1 V2 ...` (up to 6 sweep dimensions) | `prepare_dc_sweep` |
| `.op` | `.op` — DC bias point only | `prepare_op` |
| `.bode` | `.bode SOURCE TSETTLE [FSTART [FSTOP [AMP]]] [SQUARE=n] [DEBUG] [SKIPBP\|UIC]` — closed-loop SMPS frequency response | `prepare_bode_analysis` |
| `.noise` | `.noise OUTPUT INPUT <dec\|oct\|lin> N F1 F2` or `... list F1 F2 ...` | `prepare_noise` |
| `.net` | `.net [Rout] Vin` — S/Y/Z/H two-port parameters with `.ac`; input source needs `Rser` | `prepare_net` |
| `.tf` | `.tf OUTPUT INPUT` — DC transfer function | `prepare_transfer_function` |
| `.sens` | `.sens OUTPUT` — DC sensitivities | `prepare_sensitivity` |
| `.four` | `.four FREQ [HARMONICS] [PERIODS] expr1 [expr2 ...]` — THD via QPOST | `prepare_four` |
| `.meas` | see below | `prepare_meas` |
| `.step` | `.step [lin\|oct\|dec] param NAME FIRST LAST N` or `.step param NAME list ...` | `prepare_temperature_sweep` (temp); sweep runners for params |
| `.save` | `.save PATTERN [PATTERN ...]` — limit stored traces; `*`/`?` wildcards; ignored for `.noise` | `prepare_save` |

## Setup directives

| Directive | Purpose |
| --- | --- |
| `.ic V(node)=x I(L1)=y` | Hard initial conditions for `.tran` (asserted through `RIC` impedance) |
| `.nodeset V(node)=x` (`.ns`) | Soft DC-solve hints, removed near convergence |
| `.param NAME=VALUE` | User parameters; expressions need no braces; `mc(x,y)` / `gauss(sigma)` for tolerance analysis |
| `.func NAME(args) {expr}` | User-defined function |
| `.temp T1 [T2 ...]` | Circuit temperature(s) |
| `.global NET` | Un-scope a net from subcircuits (`0`/`GND` and `$G_*` are always global) |
| `.inc PATH` / `.lib PATH [ENTRY]` / `.libpath DIR` | Include files / libraries / search path |
| `.plot [AC\|DC\|NOISE\|OP\|TRAN] expr...` | Waveform-viewer plot suggestions (`.print`/`.probe` synonyms) |
| `.system CMD` | Run a shell command after simulation (`%RAWFILE%`, `%DECK%`, `%QUX%` env strings) |

## `.meas` templates

Executed post-simulation by QPOST; results readable via `read_measures`.

```spice
.meas NAME find EXPR1 at EXPR2                     ; value at abscissa point
.meas NAME find EXPR1 when EXPR2=EXPR3 [td=..] [cross|rise|fall=n|last]
.meas NAME <avg|max|min|pp|rms|integ> EXPR [from A to B]
.meas NAME trig EXPR1=EXPR2 targ EXPR3=EXPR4       ; interval measurement
.meas NAME four FREQ EXPR                          ; Fourier component
.meas NAME fra FREQ INPUT OUTPUT                   ; frequency-response ratio (SMPS Bode verification)
.meas plot RESULT1 [RESULT2 ...]                   ; embed plot suggestions
```

`.meas NAME fra ...` is the most reliable way to verify individual `.bode`
gain/phase points.

## High-value `.options`

Stage any option in these tables with `prepare_options` (allowlisted `.options`
staging) instead of hand-writing directive text.

Convergence (see the `qspice-convergence-debugging` skill for triage order):

| Option | Meaning |
| --- | --- |
| `cshunt` | Capacitance from every node to ground (aka CMIN); `1e-12` fixes many ideal-switch tanks |
| `gshunt` | Conductance from every node to ground |
| `gmin` | Minimum conductance (default 1e-12) |
| `gminsteps` / `srcsteps` | 0 disables gmin / source stepping (counts are otherwise adaptive) |
| `noopiter` | Go directly to gmin stepping |
| `feather` | Trap integration damping factor (alternative to `method=gear`) |
| `itl1` / `itl4` | DC / transient iteration limits |
| `maxstep` / `max1ststep` | Timestep caps for `.tran` and `.bode` / first step only |
| `reltol` / `abstol` / `vntol` / `chgtol` | Error tolerances |
| `method` | `trap` (default) or `gear` |
| `ric` | Source impedance asserting `.ic` (default 1 mΩ) |

Bode / FRA:

| Option | Meaning |
| --- | --- |
| `boderef` | Reference node when feedback reference is not AC ground (default node 0) |
| `bodeampfreq` | Frequency of minimum perturbation amplitude; `0` = constant amplitude |
| `bodelopow` / `bodehipow` | Amplitude growth exponents below / above `bodeampfreq` |
| `bodeperiods` | Max periods in the deconvolution |
| `bodetol` | FRA relative tolerance |
| `bodeinput` / `bodeoutput` | Override transfer-function input/output nodes |

Output / bookkeeping:

| Option | Meaning |
| --- | --- |
| `savepowers` | Record per-device dissipation as waveform data |
| `keepopinfo` | Retain the operating point for small-signal analyses |
| `saveparam` / `listparam` | Include evaluated parameters as data / print them |
| `numdgt` / `measdgt` | ASCII `.qraw` / `.meas` output precision |
| `forcestepdatasize` | Force stepped waveform files readable when trace counts vary |
| `seed` / `seedclock` | RNG control for `mc()`/`gauss()` parameter runs |
| `fastmath2` | Annotate preferred solver (QSPICE64 vs QSPICE80) |

## Syntax conventions worth remembering

- Expressions need no curly braces or quotes: `R1 A B 3*x` works after `.param x=100k`.
- Metric suffixes: `f p n u m K Meg G T` plus `mil`; no space before the suffix.
- `Meg` is 1e6 — a bare `M`/`m` is always milli.
- Hex (`0xff`) and binary (`0b111`) integers are understood; comments via `;`, `//`, `*` or `#` at line start.
- Extended-ASCII device letters (`¥`, `£`, `Ø`, `×`, `Ã`, `€`) denote mixed-signal blocks; `.qsch` files are Latin-1 on the wire.
