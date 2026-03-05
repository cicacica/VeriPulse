#uv run mypy src/ tests/ --disallow-untyped-defs --warn-unused-ignores
#uv run ruff check src/ tests/
#uv run ruff format --check src/ tests/
#uv run docstr-coverage src/veripulse
#uv run coverage run -m pytest tests
#uv run coverage report -m

uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run pytest tests/ -s
