In the name of God, the Most Gracious, the Most Merciful

# Closed-loop `.bode` details

- **Injection point:** the perturbing source goes between the SMPS output and the top of the feedback divider (low impedance driving high impedance).
- **Settling first:** run `prepare_transient` + `run_simulation` to learn how long the supply takes to settle; pass that as `settling_time` to `prepare_bode_analysis`. No settling acceleration is attempted by QSpice.
- **Reference node:** if the feedback reference is not at AC ground, pass `reference_node` (stages `.options boderef=<node>` alongside `.bode`).
- **Amplitude shaping:** perturbation amplitude rises away from the geometric mean of the sweep by default. Tune with `bode_amplitude_frequency`, `bode_low_power`, and `bode_high_power` (`.options bodeampfreq/bodelopow/bodehipow`), or set `bode_amplitude_frequency="0"` for constant amplitude.
- **Low FSTART is expensive:** each decade down multiplies simulation time.
