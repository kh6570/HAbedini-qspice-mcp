# Reference recipe attribution

Most bundled recipes are repo-owned, clean-room circuits. The recipes listed
below are **adapted from the public work of Prof. J. Marcos Alonso**
(Professor of Electronics Engineering, University of Oviedo,
<https://github.com/marcosalonsoelectronics>) and are redistributed here **with
the author's permission**.

For each adapted recipe:

- `<recipe_id>.qsch` is Alonso's original QSpice schematic (kept as the source of truth).
- `<recipe_id>.cir` is the self-contained netlist produced by QSpice/QUX with his
  behavioral component library (`website/Qspice/*.qsym`) inlined, so the circuit
  simulates without any external symbol files.

Per-recipe provenance (source repository, file path, and pinned commit SHA) is
recorded in each `recipe.json` `source` block, and the full traceability map lives
in `local-dev-docs/docs/recipe_crossref.md`.

| recipe_id | topology folder | source repo | video |
| --- | --- | --- | --- |
| `flyback_qr` | `isolated_dc_dc/` | [PE-82](https://github.com/marcosalonsoelectronics/PE-82) | Quasi-Resonant Flyback Converter |
| `buck_boost_dcm` | `non_isolated_dc_dc/` | [PE-90](https://github.com/marcosalonsoelectronics/PE-90) | Buck-Boost Converter in DCM |
| `two_phase_buck` | `non_isolated_dc_dc/` | [PE-103](https://github.com/marcosalonsoelectronics/PE-103) | Introduction to Multiphase Buck DC-DC Converters |
| `llc_resonant` | `resonant_dc_dc/` | [PE-119](https://github.com/marcosalonsoelectronics/PE-119) | Modelling of the LLC Resonant DC-DC Converter (I) |
| `series_resonant_src` | `resonant_dc_dc/` | [PE-110](https://github.com/marcosalonsoelectronics/PE-110) | Modelling of the Series Resonant DC-DC Converter (I) |
| `parallel_resonant_prc` | `resonant_dc_dc/` | [PE-113](https://github.com/marcosalonsoelectronics/PE-113) | Modelling of the Parallel Resonant DC-DC Converter (I) |
| `class_e` | `resonant_dc_dc/` | [PE-98](https://github.com/marcosalonsoelectronics/PE-98) | Design and Simulation of ZVS Class-E DC-DC Converters |
| `half_bridge_zvs` | `soft_switching/` | [PE-79-80](https://github.com/marcosalonsoelectronics/PE-79-80) | Understanding Zero Voltage Switching in Half-Bridge Converters |
| `npc_inverter` | `inverter/` | [PE-96](https://github.com/marcosalonsoelectronics/PE-96) | Three-level Neutral Point Clamped (NPC) Inverter |

The pre-existing `buck_converter_cpp`, `boost_converter_cpp`, and
`flyback_converter_cpp` recipes are repo-owned clean-room circuits and are **not**
derived from Alonso's repositories.
