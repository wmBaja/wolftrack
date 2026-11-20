# Part 0: Prep and Cleanup

**Area:** apps/visualizer · **Depends on:** nothing · **Size:** S

## Goal

Make the backend safe to build on: working tests, no dead code colliding with the new engine, a pinned Python version, shared test fixtures.

## Findings that motivate this part

- `pyproject.toml` declares no dev dependencies and no pytest config, yet `tests/` exists. CI (`.github/workflows/release.yml`) only builds the binary; it never runs tests.
- `src/pipeline/processor.py` (`Processor`, `ScaleProcessor`, `BiasProcessor`, `FilterProcessor`) and `DataPipeline` in `src/pipeline/manager.py` are **dead code**: `PipelineManager` creates `self.pipeline = DataPipeline()` but `_run_loop` never calls it. They mutate signals in place, the opposite of the new design. `tests/test_processors.py` is their only consumer.
- Tests use two import styles (`sys.path.append(src)` and `from src.pipeline...`).
- `.python-version` is 3.14 while CI builds on 3.12 (**Q4 answered: 3.12**).

## Tasks

- [x] **0.1 Python version.** Set `.python-version` to `3.12`; keep `requires-python = ">=3.12"`.
- [x] **0.2 Test tooling.** Add `[dependency-groups] dev = ["pytest"]` (add `pytest-asyncio` only if a test needs it) and `[tool.pytest.ini_options] pythonpath = ["src"]`, `testpaths = ["tests"]`. Run `uv sync` and `uv run pytest`; **record which existing tests pass before touching anything**, then fix only tooling-caused failures, not behavior.
- [x] **0.3 CI.** Add a test step (or `test.yml`) running `uv run pytest` on Python 3.12 for PRs to `dev` and `main`.
- [x] **0.4 Remove dead code.** Delete `src/pipeline/processor.py`; delete `DataPipeline`, the `Processor` import, and `self.pipeline` from `src/pipeline/manager.py`; delete `tests/test_processors.py`. Confirm with `grep -rn "Processor\|DataPipeline" src tests`.
- [x] **0.5 Test helpers** in `tests/helpers/`:
  - `make_blf.py`: write a `.blf` with `can.BLFWriter` from `(timestamp, arbitration_id, data)` tuples plus a small synthetic DBC string (a message holding `Front_Psi` and `Rear_Psi` so same-timestamp behavior is exercised, plus a single-signal message).
  - `streams.py`: seeded generators (sine, ramp, step, noise) with configurable rate and optional timestamp jitter.
  - `fixtures.py`: `tmp_user_data` (sets `WOLFTRACK_USER_DATA` to a tmp dir), `synthetic_dbc`, `synthetic_blf`.
- [x] **0.6 Docs.** Put the commands in the backend `AGENTS.md` and `README.md`.

## Acceptance criteria

- `uv run pytest` is green locally and in CI on 3.12.
- No remaining references to `DataPipeline` or the old processor classes.
- A smoke test builds a BLF with `make_blf` and indexes it with `LogQueryService`.
- No behavior change in any runtime path; no new runtime dependencies.

## Notes

- Do not modify `LogQueryService` or the live loop here beyond deleting `DataPipeline`.
- Keep the PyInstaller build working: `uv run pyinstaller --name wolftrack-visualizer --onefile --noconfirm --clean --paths src src/app.py`.