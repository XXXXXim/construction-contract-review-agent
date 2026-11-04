PY ?= python3
VENV := .venv
BIN := $(VENV)/bin
CONFIG ?= v2

.PHONY: setup test lint fmt eval eval-baseline run

setup:
	$(PY) -m venv $(VENV)
	$(BIN)/pip install -q --upgrade pip
	$(BIN)/pip install -q -e ".[dev]"

test:
	LLM_PROVIDER=fake EMBEDDING_PROVIDER=none $(BIN)/pytest -q

lint:
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .

fmt:
	$(BIN)/ruff format .
	$(BIN)/ruff check --fix .

# M5에서 구현: src/contract_review/eval.py
eval:
	$(BIN)/python -m contract_review.eval --config $(CONFIG)

eval-baseline:
	$(BIN)/python -m contract_review.eval --config baseline

# M6에서 구현
run:
	$(BIN)/streamlit run app/streamlit_app.py
