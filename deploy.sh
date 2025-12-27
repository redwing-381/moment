#!/bin/bash
# Deploy AI Risk Gatekeeper to Google Cloud Run

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-adk-learning-460506}"
REGION="${GCP_REGION:-asia-south1}"
SERVICE_NAME="ai-risk-gatekeeper"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Deploying AI Risk Gatekeeper to Cloud Run"
echo "   Project: ${PROJECT_ID}"
echo "   Region: ${REGION}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install it first."
    exit 1
fi

# Authenticate (if needed)
echo "📋 Checking authentication..."
gcloud auth print-access-token > /dev/null 2>&1 || gcloud auth login

# Set project
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com

# Build and push container
echo "🏗️  Building container image..."
gcloud builds submit --tag ${IMAGE_NAME} .

# Deploy to Cloud Run
echo "☁️  Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --timeout 300 \
    --concurrency 80 \
    --min-instances 0 \
    --max-instances 3 \
    --set-env-vars "KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS}" \
    --set-env-vars "KAFKA_SASL_USERNAME=${KAFKA_SASL_USERNAME}" \
    --set-env-vars "KAFKA_SASL_PASSWORD=${KAFKA_SASL_PASSWORD}" \
    --set-env-vars "VERTEX_AI_PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars "VERTEX_AI_LOCATION=${REGION}" \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}"

# Get the URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')

echo ""
echo "✅ Deployment complete!"
echo "🌐 Service URL: ${SERVICE_URL}"
echo ""
echo "Share this URL with judges to test the application."
