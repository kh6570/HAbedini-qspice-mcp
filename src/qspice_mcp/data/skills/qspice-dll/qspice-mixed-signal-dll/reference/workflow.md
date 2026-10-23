In the name of God, the Most Gracious, the Most Merciful

# DLL authoring workflow

Use the device kind supplied with the prompt when one is given (controller, MCU, or another behavioral block).

1. **Check support.** `describe_mixed_signal_support` to confirm which scaffold generators and build toolchains (bundled DMC, MSVC `cl`, CMake) are available on this machine. Also call `describe_server_capabilities` if a later tool reports a missing backend.
2. **Preferred: one-call device spec.** For multi-pin devices (controllers, microcontrollers), call `describe_device_spec` for the PinDef-style JSON schema, then `create_dll_device_from_spec` — it places the block with every pin (inline `device_name` + `pins`, or a workspace spec file) and can scaffold the contract-matched C++ source in the same call. Skip to step 5.
3. **Manual path: place / shape the block.** `add_dll_block` to insert a block with starter input/output pins; adjust the interface with `add_dll_block_pin`, `remove_dll_block_pin`, and `set_dll_block_pin_role` (input vs output preset).
4. **Generate source.** `scaffold_dll_device_from_symbol` emits a C++ stub plus a `CMakeLists.txt` next to the schematic, with the pin signature already wired and a per-instance state struct (opaque allocation idiom). Use `scaffold_dll_device` instead for a blank start. Edit the generated `.cpp` with `write_workspace_text_file`.
5. **Build.** `build_dll_device` compiles the source to a `.dll` (prefers bundled DMC, falls back to MSVC/CMake). See the C-Block Build Guide for prerequisites.
6. **Validate.** `validate_dll_symbol_signature` cross-checks the symbol's pins against the source so the block and code can't silently drift.
7. **Simulate.** `generate_netlist` then `run_simulation` — DLL blocks are emitted correctly (not as unresolved subcircuits) by the clean-room netlister.

## Notes

- `generate_dll_variables` produces `.DLL` variable declarations via the QUX companion path when you need them.
- The symbol is the contract: pin order/names in the symbol must match the source's port list. Re-run `validate_dll_symbol_signature` after editing either.
- If no toolchain is present, `build_dll_device` reports a degradation rather than guessing — install MSVC build tools or rely on bundled DMC.

## Conventions

- Keep the `.cpp`, `CMakeLists.txt`, and `.qsch` in the same workspace folder so QSpice's *Show Source* and the build commands resolve relative paths.
- Validate before simulating; a mismatched signature fails confusingly at sim time.
