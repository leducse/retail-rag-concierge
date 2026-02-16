# Magic Apron — container for Cloud Run (GCP)
# AWS equivalent: same Dockerfile would work for ECS Fargate or Lambda container image

FROM python:3.12-slim

WORKDIR /app

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App and static frontend
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY static/ ./static/

# Run from project root so scripts and static resolve correctly
ENV PYTHONPATH=/app
WORKDIR /app
# Cloud Run sets PORT; default 8080 for local runs
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
