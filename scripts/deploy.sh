#!/usr/bin/env bash
# Deploy Magic Apron to Cloud Run (GCP) from your machine.
# Prereqs: gcloud CLI, ADC (gcloud auth application-default login), and
# GOOGLE_CLOUD_PROJECT set. See docs/SETUP_GCP_AND_CREDENTIALS.md.
#
# AWS equivalent: deploying a container to ECS Fargate or App Runner;
# here we use "gcloud run deploy --source" so GCP builds the image for us (like CodeBuild + ECR + ECS).

set -e

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-magic-apron}"

if [ -z "$PROJECT_ID" ]; then
  echo "Set GOOGLE_CLOUD_PROJECT or run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

echo "Project: $PROJECT_ID  Region: $REGION  Service: $SERVICE_NAME"
echo "Building and deploying (this may take a few minutes)..."

# Deploy from source: builds a container with Cloud Build, pushes to Artifact Registry, deploys to Cloud Run.
# --allow-unauthenticated: so the portfolio frontend is publicly callable (optional: remove for auth-only).
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID" \
  --set-env-vars "MAGIC_APRON_DATA_STORE_ID=${MAGIC_APRON_DATA_STORE_ID:-}" \
  --set-env-vars "VERTEX_LOCATION=${VERTEX_LOCATION:-global}"

echo "Done. Service URL:"
gcloud run services describe "$SERVICE_NAME" --region "$REGION" --project "$PROJECT_ID" --format='value(status.url)'
