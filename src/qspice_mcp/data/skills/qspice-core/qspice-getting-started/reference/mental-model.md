In the name of God, the Most Gracious, the Most Merciful

# Mental model

## Core mental model

- **`.qsch` is the source of truth.** Netlists (`.net`/`.cir`), logs (`.log`), and waveforms (`.qraw`) are *derived* — regenerate them from the schematic rather than editing them by hand.
- **Staged analysis siblings are derived too.** Tools like `prepare_transient` write `*-tran.qsch` (and similar) as copies of `source_path` plus one directive. They **do not auto-sync** when you edit the base schematic in the GUI. Edit layout on the base `.qsch` only; re-run `prepare_*` before simulating; never treat `*-tran.qsch` as the layout master or open it in the GUI for placement.
- **Bounded results.** `read_waveform` is capped (about 2000 points). Prefer `measure_waveform` for scalars (peak, RMS, settling) over dumping raw samples.
- **Sandbox.** All paths resolve against the server's workspace root. Use relative paths or pass `workspace_root` per call.
- **Degraded gracefully.** Optional backends (waveform reader, schematic editor, QUX exporter, DLL toolchain) may be missing. Call `describe_server_capabilities` first when anything fails unexpectedly — it reports which tool groups are healthy, partial, or degraded and why.

## First step: check the environment

Before non-trivial work, call **`describe_server_capabilities`**. It tells you whether QSpice is configured, which optional backends are available, which tool groups are degraded, and feature flags. This avoids guessing when a later tool returns a backend error.

## When something fails

- Backend error → `describe_server_capabilities`, check the relevant group's state.
- Simulation didn't converge or stopped early → load the **qspice-convergence-debugging** skill.
- Missing `QSPICE_EXE` / `connected=false` → this is a setup/config issue, not a circuit issue; point the user to the server setup docs.

## Conventions

- Treat `.qsch` as source; never hand-edit derived `.net`/`.qraw`.
- Prefer `measure_waveform` over `read_waveform`; respect the sample budget.
- Read the log after every run before reporting results.
- Call `describe_server_capabilities` before assuming a tool is broken.
