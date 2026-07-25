---
name: qspice-mixed-signal-dll
description: Author, scaffold, build, and validate QSpice `.DLL` custom-device blocks for mixed-signal C/C++ models. Use when adding a controller or behavioral block backed by compiled code, generating a C++ scaffold from a symbol, building the DLL, or checking that a symbol matches its source.
license: MIT
metadata:
  author: qspice-mcp
  version: "1.1"
---

# QSpice: Mixed-Signal `.DLL` Custom Devices

QSpice runs compiled C/C++ models as `.DLL` custom-device blocks. This skill
covers the full loop: place the block, generate matching source, build it, and
prove the symbol and source agree.

## When to use

- A circuit needs a digital controller, state machine, or behavioral block that
  is easier to express in code than in SPICE primitives.
- You have a `.DLL` symbol and need a C++ scaffold, or a source file and need to
  verify it matches the symbol.

## When NOT to use

- Pure analog authoring/placement → `qspice-getting-started` and
  `qspice-schematic-layout`.
- A simulation that runs but won't converge → `qspice-convergence-debugging`.

## Workflow

1. **Check support.** `describe_mixed_signal_support` to confirm which scaffold
   generators and build toolchains (bundled DMC, MSVC `cl`, CMake) are available
   on this machine.
2. **Preferred: one-call device spec.** For multi-pin devices (controllers,
   microcontrollers), call `describe_device_spec` for the PinDef-style JSON
   schema, then `create_dll_device_from_spec` — it places the block with every
   pin (inline `device_name` + `pins`, or a workspace spec file) and can
   scaffold the contract-matched C++ source in the same call. Skip to step 5.
3. **Manual path: place / shape the block.** `add_dll_block` to insert a block
   with starter input/output pins; adjust the interface with `add_dll_block_pin`,
   `remove_dll_block_pin`, and `set_dll_block_pin_role` (input vs output preset).
4. **Generate source.** `scaffold_dll_device_from_symbol` emits a C++ stub plus a
   `CMakeLists.txt` next to the schematic, with the pin signature already wired
   and a per-instance state struct (opaque allocation idiom). Edit the generated
   `.cpp` with `write_workspace_text_file`.
5. **Build.** `build_dll_device` compiles the source to a `.dll` (prefers bundled
   DMC, falls back to MSVC/CMake). See the C-Block Build Guide for prerequisites.
6. **Validate.** `validate_dll_symbol_signature` cross-checks the symbol's pins
   against the source so the block and code can't silently drift.
7. **Simulate.** `generate_netlist` then `run_simulation` — DLL blocks are emitted
   correctly (not as unresolved subcircuits) by the clean-room netlister.

## Symbol reuse (`.qsym`)

- `export_symbol_to_qsym` writes one component's embedded symbol as a standalone
  `.qsym` file for reuse across schematics or external symbol libraries.
- `add_component_from_qsym` places a `.qsym` symbol into a schematic with a new
  reference designator (full drawing, pins, type, and library file embedded).

## Notes

- `generate_dll_variables` produces `.DLL` variable declarations via the QUX
  companion path when you need them.
- The symbol is the contract: pin order/names in the symbol must match the
  source's port list. Re-run `validate_dll_symbol_signature` after editing either.
- If no toolchain is present, `build_dll_device` reports a degradation rather than
  guessing — install MSVC build tools or rely on bundled DMC.

## Conventions

- Keep the `.cpp`, `CMakeLists.txt`, and `.qsch` in the same workspace folder so
  QSpice's *Show Source* and the build commands resolve relative paths.
- Validate before simulating; a mismatched signature fails confusingly at sim time.
