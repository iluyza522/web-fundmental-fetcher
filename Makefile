.PHONY: install test

install:
	pip install -r requirements.txt

test:
	pip install pytest pytest-asyncio && pytest -v

test-cov:
	pip install pytest-cov && pytest --cov=. --cov-report=term-missing
