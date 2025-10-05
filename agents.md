# Codex Agent Handbook

## Repository Snapshot
- Interactive D&D master that talks in Russian; CLI entrypoint `dnd_master.py`, optional GUI in `dnd_master_gui.py`.
- Dice logic lives in `dice_system.py`; game defaults and prompts are configurable in `rules.yaml`.
- Narrative assets such as `story_arc.md` and the auto-generated `world_bible.md` guide the campaign tone.

## Environment Setup
1. Use Python 3.8+ (project tested with CPython); create an isolated venv (`python -m venv .venv`).
2. Activate the environment and install dependencies: `pip install -r requirements.txt`.
3. Provide an OpenAI API key either via `.env` (`OPENAI_API_KEY=...`) or an exported environment variable before running.
4. Keep `.env` untracked; never commit keys or secrets.

## Running the App
- **CLI (recommended in Codex Cloud):** `python dnd_master.py`. The script loads `rules.yaml`, ensures `world_bible.md` exists, then starts an interactive loop.
- **GUI:** `python dnd_master_gui.py`. Requires a working Tk display; avoid in headless runners unless X forwarding is configured.
- Both entrypoints import the shared `dice_roller` instance for ability checks, damage, and initiative rolls.

## Generated and Static Data
- `world_bible.md` is created on first run via the OpenAI API. If it is missing, the app will request a fresh version—expect API usage.
- The dice subsystem and difficulty scales rely on values in `rules.yaml`; keep that file consistent when introducing new mechanics.
- Narrative guides (`story_arc.md`, `world_bible.md`) are human-readable references. Update them deliberately and review diffs carefully.

## Development Guidelines
- Respect the existing structure: core logic in `dnd_master.py`, UI layers in `dnd_master_gui.py`, utilities in `dice_system.py`.
- When extending gameplay rules, add configurable knobs to `rules.yaml` so prompts stay in sync with mechanics.
- There are no automated tests; validate behavior by running the CLI and exercising relevant commands.
- Localization is Russian-facing; keep player-facing strings in Russian, but code and config remain ASCII-friendly when possible.

## Git Workflow Notes
- Default branch is `main`; keep commits scoped and descriptive.
- Generated artifacts (e.g., `world_bible.md`) may change between runs; check diffs before committing to avoid noisy updates.
- Before pushing, ensure the venv directory or other local-only files stay excluded (no `.gitignore` changes required currently).
