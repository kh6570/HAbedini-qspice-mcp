In the name of God, the Most Gracious, the Most Merciful

# QSpice Agent Skills Catalog

Curated **agent skills** that teach an AI coding agent how to drive the QSpice MCP
server effectively. Skills are client-side knowledge (loaded by the agent on
demand), **not** MCP tools — they add zero always-on context cost to the server
and only enter the model's context when a relevant task triggers them.

This catalog ships **inside the `qspice-mcp` package** (`qspice_mcp/data/skills/`),
so `pip install qspice-mcp` delivers it to every user. Install the skills into your
agent's skills directory with:

```powershell
pwsh -File scripts/install_skills.ps1
```

By default this copies `qspice-getting-started` into `~/.agents/skills/`, which
most MCP-aware agents discover automatically. Pass `-SkillsRoot` for a different
directory and `-Groups` for the optional groups listed below.

## Layout

```
skills/
  <group>/
    plugin.yaml                 # group description + keywords
    <skill>/
      SKILL.md                  # short router: when to use, when not to, reference names
      manifest.yaml             # when-not-to-use, reference-files, requires-tools
      reference/*.md            # procedures, loaded only when named
```

The default install is the orientation skill only. Install optional groups when
the task needs them. Agents trigger the right skill more reliably when fewer
are loaded.

## Groups

| Group | Install | Skills |
| --- | --- | --- |
| `qspice-core` | default | `qspice-getting-started` |
| `qspice-layout` | optional | `qspice-schematic-layout` |
| `qspice-power` | optional | `qspice-power-electronics` |
| `qspice-dll` | optional | `qspice-mixed-signal-dll` |
| `qspice-analysis` | optional | `qspice-waveform-analysis`, `qspice-convergence-debugging` |

```powershell
pwsh -File scripts/install_skills.ps1 -Groups qspice-core,qspice-layout,qspice-power,qspice-dll,qspice-analysis
```

## Conventions

- `SKILL.md` frontmatter must declare `name` and a trigger-oriented `description`.
  The body is a router. It does not repeat the numbered procedure.
- `manifest.yaml` must declare `schema_version`, `version`, `human-description`,
  `when-not-to-use`, `reference-files`, and `requires-tools` (every tool must be
  a real registered MCP tool — enforced by `tests/unit/data/test_skills_catalog.py`).
- Reference filenames are loaded only when named. They live in `reference/`
  beside the skill.
