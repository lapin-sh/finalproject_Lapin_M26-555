install:
	uv sync

run:
	uv run python main.py

lint:
	uv run ruff check .
