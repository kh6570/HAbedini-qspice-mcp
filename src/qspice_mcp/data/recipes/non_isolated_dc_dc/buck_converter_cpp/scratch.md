# Buck converter (C++ DLL) — scratch build (Track A)

Build `Buck-converter.qsch` and `buck_controller.cpp` in an **empty workspace** using MCP authoring tools only.

**Forbidden on this track:** `materialize_reference_circuit`, manual file copy into the workspace.

**Track B alternative:** `read_workflow_instruction(instruction_id="buck-converter-cpp-catalog")` — materialize bundled recipe instead.

## Preflight

1. `describe_topology_authoring_support` — confirm `scratch_buck_ready` is true.
2. `list_workflow_instructions` — confirm `buck-converter-cpp` is listed.
3. For ad-hoc part placement (not the coordinate table below), call
   `suggest_component_placement`, use `add_component(..., auto_place=true)`, or batch-apply
   a v1 JSON layout spec via `apply_schematic_layout_spec` (see
   `describe_schematic_layout_spec` and bundled `scratch_power_stage.v1.json`).

## Layout rules

- **Prefer the component table below** for the full buck — it is human-tuned.
- **Ad-hoc parts:** `suggest_component_placement` or `apply_schematic_layout_spec`
  scan a 400×400 grid from the origin, left-to-right then downward, keeping
  `rotation_degrees=0` unless the table specifies otherwise.
- After placement, use `read_component` to verify coordinates; nudge with
  `set_component_position` if needed.
- Rotate (`set_component_rotation`) only when the workflow table calls for non-zero rotation.

## Build steps

1. `create_schematic(output_path="Buck-converter.qsch", overwrite=true)`
2. Place components (table below) with `add_component` / `add_dll_block`.
3. Place junctions with `add_junction`.
4. Place net labels with `add_net_label`.
5. Route wires with `add_wire` (table below).
6. `set_parameter(name="Tsamp", value="10µ")`
7. `add_instruction(instruction=".tran 0 300µ 0 100n uic")`
8. `write_workspace_text_file(relative_path="buck_controller.cpp", content=<cpp below>, overwrite=true, schematic_path="Buck-converter.qsch", dll_reference="X1")` — auto-builds `buck_controller.dll` and validates X1 (uses bundled DMC when `QSPICE_EXE` is set; else MSVC/CMake)
9. `run_simulation` → `read_waveform` on `V(out)` (~5–6 V steady state)

Use `set_component_rotation` if `read_component` shows wrong `rotation_degrees` on rotated parts.

## Components (12)

| Ref | Tool | kind / notes | Value | Position (x,y) | Rot° |
| --- | --- | --- | --- | --- | --- |
| X1 | `add_dll_block` | `Buck_controller`; pins in0–in4, out0–out4 | — | (300, 100) | 0 |
| V2 | `add_component` | `voltage_source` | `pulse 0 1 0 10n 10n 0n {Tsamp}` | (-1700, -600) | 0 |
| V3 | `add_component` | `voltage_source` | `10` | (-2900, 1900) | 0 |
| M1 | `add_component` | `nmos` | `BSC123N08NS3` | (-1400, 2600) | 90 |
| D1 | `add_component` | `diode` | `RF1001NS2D` | (-100, 2000) | 0 |
| L1 | `add_component` | `inductor` | `50µ` | (400, 2700) | 90 |
| C1 | `add_component` | `capacitor` | `10µ` | (1600, 2300) | 0 |
| R1 | `add_component` | `resistor` | `1` | (2500, 2100) | 0 |
| R2 | `add_component` | `resistor` | `50m` | (1100, 2700) | 90 |
| R3 | `add_component` | `resistor` | `0.15` | (1600, 1800) | 180 |
| B1 | `add_component` | `behavioral` | `V=V(PWM)` | (-900, 1700) | 90 |
| R4 | `add_component` | `resistor` | `10` | (-1400, 2000) | 0 |

## Junctions (9)

`(2500,2700)`, `(1600,2700)`, `(1600,1300)`, `(-100,2700)`, `(-100,1300)`, `(-500,2700)`, `(-1000,-500)`, `(-1000,-700)`, `(-2900,1300)`

## Net labels (13)

| Position (x,y) | Net |
| --- | --- |
| (1300, 100) | `y[k]` |
| (-1700, -1100) | `GND` |
| (-1200, -100) | `clk` |
| (1300, -100) | `y[k-1]` |
| (1300, -300) | `y[k-2]` |
| (1400, -500) | `PWM` |
| (-2900, 1100) | `GND` |
| (-1900, 2700) | `in` |
| (2100, 2700) | `out` |
| (-1400, 2300) | `G` |
| (-700, 2700) | `S` |
| (1400, -700) | `SW` |
| (-1000, -1100) | `GND` |

## Wires (54)

Each row: `add_wire(start_x, start_y, end_x, end_y, net_name=...)`.

| start_x | start_y | end_x | end_y | net |
| --- | --- | --- | --- | --- |
| 1400 | -500 | 1600 | -500 | PWM |
| 1300 | 100 | 1600 | 100 | y[k] |
| 1300 | -100 | 1600 | -100 | y[k-1] |
| 1300 | -300 | 1600 | -300 | y[k-2] |
| -2100 | 100 | -500 | 100 | out |
| 900 | 100 | 1300 | 100 | y[k] |
| -1700 | -400 | -1700 | -100 | clk |
| -1700 | -1100 | -1700 | -800 | GND |
| -1200 | -100 | -500 | -100 | clk |
| -1700 | -100 | -1200 | -100 | clk |
| 900 | -100 | 1300 | -100 | y[k-1] |
| 900 | -300 | 1300 | -300 | y[k-2] |
| 900 | -500 | 1400 | -500 | PWM |
| -2900 | 2100 | -2900 | 2700 | in |
| -2900 | 1300 | -2900 | 1700 | GND |
| 2100 | 2700 | 2500 | 2700 | out |
| -100 | 2700 | 200 | 2700 | S |
| -1900 | 2700 | -1600 | 2700 | in |
| 2500 | 1900 | 2500 | 1300 | GND |
| 2500 | 2700 | 2500 | 2300 | out |
| -100 | 1300 | -2900 | 1300 | GND |
| -100 | 1800 | -100 | 1300 | GND |
| -500 | 2700 | -100 | 2700 | S |
| 1600 | 1300 | -100 | 1300 | GND |
| -100 | 2700 | -100 | 2200 | S |
| 1600 | 1600 | 1600 | 1300 | GND |
| 1300 | 2700 | 1600 | 2700 | out |
| 2500 | 1300 | 1600 | 1300 | GND |
| 1600 | 2700 | 1600 | 2500 | out |
| -2900 | 1100 | -2900 | 1300 | GND |
| 1600 | 2100 | 1600 | 2000 | N01 |
| 600 | 2700 | 900 | 2700 | N02 |
| -1400 | 1800 | -1400 | 1700 | N03 |
| -1400 | 2300 | -1400 | 2200 | G |
| -700 | 1700 | -500 | 1700 | S |
| -1400 | 1700 | -1100 | 1700 | N03 |
| -500 | 1700 | -500 | 2700 | S |
| -700 | 2700 | -500 | 2700 | S |
| -2900 | 2700 | -1900 | 2700 | in |
| 1600 | 2700 | 2100 | 2700 | out |
| -1400 | 2400 | -1400 | 2300 | G |
| -1200 | 2700 | -700 | 2700 | S |
| -2100 | 100 | -2100 | 700 | out |
| -2100 | 700 | 3200 | 700 | out |
| 3200 | 700 | 3200 | 2700 | out |
| 3200 | 2700 | 2500 | 2700 | out |
| 1400 | -700 | 1600 | -700 | SW |
| 900 | -700 | 1400 | -700 | SW |
| -1000 | -500 | -1000 | -300 | GND |
| -1000 | -300 | -500 | -300 | GND |
| -500 | -500 | -1000 | -500 | GND |
| -1000 | -700 | -1000 | -500 | GND |
| -500 | -700 | -1000 | -700 | GND |
| -1000 | -1100 | -1000 | -700 | GND |

## Verification

1. `inspect_schematic` — 12 components, `.tran 0 300µ 0 100n uic`, `Tsamp` parameter.
2. `read_component` on `M1`, `L1`, `R2`, `R3`, `B1` — rotations match the component table.
3. `run_simulation` → `V(out)` steady state with ripple.

## buck_controller.cpp

```cpp
#include <cmath>

double
Ts,
D,
Sawtooth,
PWM,
yk=0, yk_1=0, yk_2=0;

union uData
{
   bool b;
   char c;
   unsigned char uc;
   short s;
   unsigned short us;
   int i;
   unsigned int ui;
   float f;
   double d;
   long long int i64;
   unsigned long long int ui64;
   char *str;
   unsigned char *bytes;
};

int __stdcall DllMain(void *module, unsigned int reason, void *reserved) { return 1; }

#undef in0
#undef in1
#undef in2
#undef in3
#undef out0
#undef out1
#undef out2
#undef out3
#undef in4
#undef out4

extern "C" __declspec(dllexport) void buck_controller(void **opaque, double t, union uData *data)
{
   double  in0  = data[ 0].d;
   double  in1  = data[ 1].d;
   double  in2  = data[ 2].d;
   double  in3  = data[ 3].d;
   double  in4  = data[ 4].d;
   double &out0 = data[5].d;
   double &out1 = data[6].d;
   double &out2 = data[7].d;
   double &out3 = data[8].d;
   double &out4 = data[9].d;

      Ts= 5e-6;
      D= 0.56;
      Sawtooth= t/Ts - floor(t/Ts);
      if (D>Sawtooth) {PWM= 15;}
      else {PWM= 0;}
      if ((in1>0.999)&&(in1<=1.001)) { yk_2= yk_1;
                                       yk_1= yk;
                                       yk=in0;}
      out0= yk;
      out1= yk_1;
      out2= yk_2;
      out3= PWM;
      out4= Sawtooth;
}
```
