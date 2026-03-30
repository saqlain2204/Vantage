# Contributing to Vantage

Thank you for your interest in contributing to Vantage.

## Development setup

```bash
git clone https://github.com/saqlain2204/vantage.git
cd vantage
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -e ".[dev]"
cp .env.example .env   # fill in your API keys
```

## Workflow

1. **Fork** the repository and clone your fork.
2. **Create a branch** — one branch per feature or bug fix.
3. **Make your changes** and add tests under `tests/`.
4. **Verify** the full check suite passes:
   ```bash
   python -m ruff check .
   python -m mypy src/vantage
   python -m pytest -q
   ```
5. **Submit a Pull Request** against `main`.

## Code conventions

- Follow PEP 8 and PEP 526.
- Use type annotations on all public functions and methods.  The project targets `mypy --strict` compliance.
- Keep components modular and single-purpose.
- Async counterparts (`AsyncAgent`, `AsyncOpenAIModel`, etc.) must mirror the sync API exactly.
- Do not add dependencies to `pyproject.toml` without discussion in an issue first.

## Tests

All new features and bug fixes must include tests.  Run the suite with:

```bash
python -m pytest -q
```

For coverage:

```bash
python -m pytest --cov=vantage --cov-report=term-missing -q
```

Async tests use `pytest-asyncio`.  Mark them with `@pytest.mark.asyncio`.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
feat: add Redis memory backend
fix: correct tool_calls serialisation in OpenAI client
docs: update Quick Start YAML example
chore: bump Pillow to 11.0
```

## Changelog

Update `CHANGELOG.md` under the `[Unreleased]` heading for every user-visible change.

