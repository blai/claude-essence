# claude-essence

Personal Claude Code plugin and `blai` marketplace.

## Structure

Each plugin lives in its own directory:

- `claude-essence/` — Output styles, skills, self-evolving commands
  - `commands/` — Slash commands (auto-discovered, YAML frontmatter)
  - `skills/` — Skills (each in own directory with SKILL.md)
  - `output-styles/` — Output style definitions
  - `.claude-plugin/plugin.json` — Plugin manifest
- `md-quality/` — Markdown documentation quality skills
  - `skills/` — Skills (each in own directory with SKILL.md)
  - `.claude-plugin/plugin.json` — Plugin manifest
- `.claude-plugin/marketplace.json` — Repo-level marketplace manifest

## Development

- Test locally: `claude --plugin-dir ./claude-essence` (or `./md-quality`)
- All internal paths use `${CLAUDE_PLUGIN_ROOT}` for portability
- Version bumps go in both the plugin's plugin.json and marketplace.json

## Conventions

- Minimalist prose. No filler.
- Every tool must have clear frontmatter metadata (name, description).
- Commands: `description`, `argument-hint`, `allowed-tools` in frontmatter.
- Skills: `name`, `description` in SKILL.md frontmatter.
- Output styles: `name`, `description`, `keep-coding-instructions` in frontmatter.
