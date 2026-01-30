# Repository Guidelines

## Project Structure & Module Organization
- Core code lives in `GramAddict/core/` (session flow, navigation, utils) and `GramAddict/plugins/` (jobs for hashtags, reels, followers, Telegram reports). Entry points are `run.py` and `python -m GramAddict`.
- Configs sit in `config-examples/` and `accounts/<user>/`; assets in `res/`; extras in `extra/`; tests in `test/` with fixtures under `test/mock_data/` and text samples in `test/txt/`.
- Dependencies are in `requirements.txt`; optional dev extras sit under `[project.optional-dependencies].dev` in `pyproject.toml`. Local adb binaries can live in `platform-tools/` when installed via `scripts/setup-adb.sh`.

## Build, Test, and Development Commands
- Create a venv and install: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` (add `pip install -e .[dev]` for lint/tests).
- Install bundled adb without touching the system: `./scripts/setup-adb.sh` then `export ADB_PATH=$PWD/platform-tools/platform-tools/adb`.
- Run the bot: `python -m GramAddict run --config accounts/<user>/config.yml`; initialize configs with `python -m GramAddict init <user>`; capture a UI dump with `python -m GramAddict dump --device <serial>`.
- Quality checks: `black .`, `pyflakes .`, and `python -m pytest` when dev extras are installed.

## Coding Style & Naming Conventions
- Black defaults (4-space indent, ~88-char lines); snake_case for functions/modules, PascalCase for classes, descriptive plugin filenames.
- Keep side effects in CLI layers; helpers should be deterministic and log via `GramAddict.core.log`.

## Testing Guidelines
- Use pytest with `test_*` names; fixtures live in `test/mock_data/`. Mock filesystem/adb to keep tests device-free.
- Add coverage for plugins and data transforms when behavior changes; keep samples lightweight.

## Commit & Pull Request Guidelines
- Commit messages: present-tense, imperative, ~72 chars (e.g., `fix: handle search reels`). Keep secrets and account configs out of VCS—use `config-examples/` as templates.
- PRs: include a short summary, tests run, linked issues, and logs/screenshots for UI changes.

## Feature Flags & Config Tips
- Prefer config over CLI. Key toggles: `watch-reels` (also used for search-opened reels), `reels-like-percentage`, `reels-watch-time`; startup randomness via `notifications-percentage`; comment likes via `like-comments-percentage`, `like-comments-per-post`, `comment-like-sort`; allow new IG builds with `allow-untested-ig-version: true`.
- Prefer USB connections; specify devices by serial. Set `ADB_PATH` if using the bundled adb; Wi-Fi adb is only used when an explicit host:port is provided.
