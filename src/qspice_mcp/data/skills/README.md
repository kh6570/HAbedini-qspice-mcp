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

By default this copies each skill into `~/.agents/skills/`, which most MCP-aware
agents discover automatically. Pass `-SkillsRoot` to target a different location.

## Layout

```
skills/
  <group>/
    plugin.yaml                 # group description + keywords
    <skill>/
      SKILL.md                  # YAML frontmatter (name, description) + body
      manifest.yaml             # tooling metadata (version, requires-tools, ...)
      reference/*.md            # optional, loaded on demand
```

Install only the groups you need — agents trigger the right skill more reliably
when fewer are loaded. You can also invoke a skill by name when you know which
one you want.

## Groups

| Group | Description |
| --- | --- |
| `qspice-core` | Core QSpice workflow: discover/author circuits, simulate, read waveforms, debug convergence. Every user needs these. |

## Conventions

- `SKILL.md` frontmatter must declare `name` and a trigger-oriented `description`.
- `manifest.yaml` must declare `schema_version`, `version`, `human-description`,
  and `requires-tools` (every entry must be a real registered MCP tool — enforced
  by `tests/unit/data/test_skills_catalog.py`).
- Keep the main `SKILL.md` lean; push depth into `reference/*.md` loaded on demand.
