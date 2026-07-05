# Boost converter (C++ DLL) — catalog recipe

Bundled **boost** topology: inductor on the input path, switch to ground, diode to
the output rail, and output capacitor/load. PWM control comes from the
`Boost_controller` C-block DLL.

## Materialize

```text
materialize_reference_circuit(recipe_id="boost_converter_cpp")
build_dll_device(source_path="boost_controller.cpp")
run_simulation(source_path="Boost-converter.qsch")
```

## Topology notes

- Schematic block `X1` references `Boost_controller` (10-pin `.DLL` device).
- Controller duty cycle defaults to `D=0.56` at `200 kHz` in `boost_controller.cpp`.
- Compare with `buck_converter_cpp` for catalog modularity: distinct `recipe_id`,
  manifest, schematic, and controller source.
