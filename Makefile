.PHONY: install backend-install frontend-install test dev-api dev-ui run

install: backend-install frontend-install

backend-install:
	python3 -m venv .venv
	.venv/bin/pip install -U pip
	.venv/bin/pip install -r requirements.txt

frontend-install:
	cd frontend && npm install

test:
	.venv/bin/pytest -q

dev-api:
	.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

dev-ui:
	cd frontend && npm run dev
