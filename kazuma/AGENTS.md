# Repository Guidelines

## Project Structure & Module Organization
The FastAPI service lives in `main.py`, with typed schemas in `models.py`, EPA data ingestion logic in `epa_data.py`, and policy simulations in `policy_engine.py`. Static assets and Tailwind entrypoints are under `static/`, while generated CSS stays in `static/output.css`. Cached datasets or API responses should be written to `data/cache` (gitignored). Node build config files (`package.json`, `postcss.config.js`, `tailwind.config.js`) support CSS compilation; keep them in sync with any new frontend modules.

## Build, Test, and Development Commands
```bash
python3.12 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
npm install && npm run build:css            # compile Tailwind into static/output.css
npm run watch:css                           # rebuild CSS during frontend work
python main.py                              # run FastAPI with the default settings
uvicorn main:app --reload --host 0.0.0.0 --port 8000  # preferred hot-reload server
pytest tests/                               # execute the Python test suite
```

## Coding Style & Naming Conventions
Use Python 3.12 syntax, 4-space indentation, and explicit type hints for every public function in API, data, and policy modules. Keep Pydantic models grouped by domain (facility, policy, aggregation) and favor descriptive snake_case variable names; environment variables remain SCREAMING_SNAKE_CASE. Frontend scripts should stick to Tailwind utility classes in `static/*.html`, with shared JS in `static/app.js`. When adding formatting, run `ruff --select=F,E,W` or `black` if available to keep diffs minimal.

## Testing Guidelines
Prefer `pytest` with `httpx.AsyncClient` for endpoint tests and lightweight pandas fixtures for data checks. Name files `test_<module>.py` inside a top-level `tests/` package, mirroring the structure of `models.py`, `epa_data.py`, and `policy_engine.py`. Target at least 80% statement coverage on new modules and include regression cases for emissions aggregation math whenever raw EPA data schemas change. Run `pytest -q` before every commit; CI assumes a clean virtualenv and will fail fast on import errors.

## Commit & Pull Request Guidelines
Write short, present-tense commit subjects ("Add facility clustering API") and include a concise body when touching multiple modules. Reference relevant issues (e.g., `Fixes #12`) and keep unrelated refactors in separate commits. Pull requests should summarize intent, list endpoints or scripts touched, attach screenshots for UI changes, and describe any data migrations or `.env` expectations (MAPBOX_TOKEN, CACHE_DIR). Mark TODOs inline with `# TODO:` and file a follow-up issue rather than leaving silent gaps.

## Security & Configuration Tips
Never hardcode API keys—load `MAPBOX_TOKEN` and other secrets from the environment or a `.env` ignored by git. The EPA endpoints queried in `epa_data.py` can rate-limit, so throttle new integrations and respect the cache directory before making outbound requests. Validate any new user input through FastAPI dependency parameters and keep CORS settings minimal outside hackathon demos.
