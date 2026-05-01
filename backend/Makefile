VENV    := venv
PYTHON  := $(VENV)/bin/python
PIP     := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn

.PHONY: setup dev run docker-build docker-run clean

## Create virtualenv and install dependencies
setup:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

## Run with auto-reload (development)
dev:
	$(UVICORN) app.main:app --reload --port 8000

## Run without auto-reload (production-like)
run:
	$(UVICORN) app.main:app --host 0.0.0.0 --port 8000

## Build Docker image
docker-build:
	docker build -t llm-chat-api .

## Run Docker container (reads ANTHROPIC_API_KEY from .env)
docker-run:
	docker run --rm -p 8000:8000 --env-file .env llm-chat-api

## Remove virtualenv
clean:
	rm -rf $(VENV) __pycache__ app/__pycache__ app/routers/__pycache__ app/services/__pycache__
