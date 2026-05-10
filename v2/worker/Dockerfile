FROM python:3.12-slim

WORKDIR /app

COPY api/pyproject.toml ./api/pyproject.toml
COPY api/app ./api/app
COPY packages/analytics_core ./packages/analytics_core
COPY worker/pyproject.toml ./worker/pyproject.toml
COPY worker/lalagolf_worker ./worker/lalagolf_worker
RUN pip install --no-cache-dir -e ./packages/analytics_core -e ./api -e ./worker

WORKDIR /app/worker

CMD ["python", "-m", "lalagolf_worker.main"]
