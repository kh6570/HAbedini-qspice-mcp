In the name of God, the Most Gracious, the Most Merciful

# SMPS loop gain

Extract the open-loop frequency response of a closed-loop SMPS and assess stability. Use the schematic path, perturbation source, and settling time supplied with the prompt. The perturbation source is the series source inserted in the feedback loop, between the output and the top of the feedback divider.

1. `prepare_transient` + `run_simulation` first to confirm the supply settles within the stated settling time; adjust if it does not.
2. `prepare_bode_analysis` with the perturbation source and settling time. If the feedback reference is not at AC ground, pass `reference_node` (stages `.options boderef=<node>`). See `bode.md` for amplitude shaping.
3. `run_simulation` on the staged artifact, then `measure_stability_margins` for crossover frequency, phase margin, and gain margin.
4. Verify the crossover point independently: `prepare_meas(kind="fra")` at the measured crossover frequency, re-run, and `read_measures` — `.meas fra` is the most reliable frequency-domain check QSpice offers.
5. Report margins (target: phase margin >= 45 deg, positive gain margin) and note any Bode artifacts the fra check contradicted.
