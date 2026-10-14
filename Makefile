.PHONY: verify-setup test lint-contract run install install-dev

verify-setup:
	@python --version
	@python -c "import fastapi, pydantic, httpx, pytest, schemathesis; assert pydantic.VERSION.startswith('2'), 'Pydantic v2 required'; print('packages OK')"
	@claude --version
	@test -s setup/claude-answer.md || (echo 'MISSING: setup/claude-answer.md (A0 step 6)'; exit 1)
	@pytest -q tests/test_smoke.py

test:
	pytest -q

lint-contract:
	python tools/lint_contract.py docs/openapi.yaml

run:
	uvicorn app.main:app --reload --port 8000

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt
	playwright install --with-deps chromium
