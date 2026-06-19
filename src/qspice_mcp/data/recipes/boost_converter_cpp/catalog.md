# Boost converter (C++ DLL) — catalog recipe

Second bundled recipe proving `data/recipes/{recipe_id}/` modularity.

This entry ships the same starter mixed-signal bundle layout as the buck recipe
while using a distinct `recipe_id` and manifest. Use it to verify catalog
discovery (`list_reference_circuit_recipes`, `describe_reference_circuit_recipe`)
and materialization without forking the server.

## Materialize

```text
materialize_reference_circuit(recipe_id="boost_converter_cpp")
build_dll_device(source_path="buck_controller.cpp")
run_simulation(source_path="Buck-converter.qsch")
```

## Notes

- A dedicated boost-specific schematic/controller pair may replace this bundle later.
- Treat this recipe as a **catalog-structure** example, not a topology reference design.
