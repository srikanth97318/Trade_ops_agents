#!/bin/bash
# ==============================================================================
# TradeSage Ops — One-Click Google Cloud Run Deployment Script
# ==============================================================================
#
# This script automates:
#   1. Verification of Google Cloud CLI (gcloud) setup
#   2. Activation of necessary GCP APIs (Cloud Run, Cloud Build, Artifact Registry)
#   3. Local production build of the Vite/React frontend
#   4. Bundling the static frontend into the FastAPI backend
#   5. Submitting the build to Cloud Build for deployment on Cloud Run
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh
# ==============================================================================

set -e

# Configuration
SERVICE_NAME="tradesage-ops"
REGION="us-central1"
AR_REPO="tradesage-repo"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0;0m' # No Color

echo -e "${BLUE}=== Starting TradeSage Ops Cloud Run Deployment ===${NC}\n"

# Step 1: Check gcloud authentication
echo -e "${BLUE}[Step 1/6] Checking Google Cloud SDK configuration...${NC}"
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: Google Cloud SDK (gcloud) is not installed. Please install it first.${NC}"
    exit 1
fi

PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: No active Google Cloud project set. Run 'gcloud config set project <PROJECT_ID>' first.${NC}"
    exit 1
fi
echo -e "Deploying to Project: ${GREEN}$PROJECT_ID${NC}"

# Step 2: Enable required APIs
echo -e "\n${BLUE}[Step 2/6] Enabling Google Cloud Services (APIs)...${NC}"
gcloud services enable \
    run.googleapis.com \
    build.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    --quiet

# Step 3: Create Artifact Registry if it doesn't exist
echo -e "\n${BLUE}[Step 3/6] Setting up Artifact Registry repository...${NC}"
if ! gcloud artifacts repositories describe "$AR_REPO" --location="$REGION" &> /dev/null; then
    echo -e "Creating Artifact Registry repository '${AR_REPO}' in '${REGION}'..."
    gcloud artifacts repositories create "$AR_REPO" \
        --repository-format=docker \
        --location="$REGION" \
        --description="Repository for TradeSage Ops containers" \
        --quiet
else
    echo -e "Artifact Registry repository '${AR_REPO}' already exists. Skipping creation."
fi

# Step 4: Build and bundle frontend assets
echo -e "\n${BLUE}[Step 4/6] Building production frontend assets...${NC}"
if [ -d "frontend" ]; then
    cd frontend
    if [ ! -d "node_modules" ]; then
        echo "Installing frontend dependencies..."
        npm install
    fi
    echo "Running production build..."
    npm run build
    
    echo "Copying assets to backend serving directory..."
    mkdir -p ../backend/frontend
    rm -rf ../backend/frontend/dist
    cp -r dist ../backend/frontend/
    cd ..
else
    echo -e "${RED}Error: frontend directory not found. Are you running the script from tradesage-ops root?${NC}"
    exit 1
fi

# Step 5: Verify backend setup
echo -e "\n${BLUE}[Step 5/6] Preparing backend configuration...${NC}"
if [ ! -d "backend" ]; then
    echo -e "${RED}Error: backend directory not found. Please run the script from the tradesage-ops root.${NC}"
    exit 1
fi

# Step 6: Submit to Cloud Build for deployment
echo -e "\n${BLUE}[Step 6/6] Submitting container to Cloud Build & Deploying...${NC}"
gcloud builds submit backend \
    --config=backend/cloudbuild.yaml \
    --substitutions=_AR_REPO="$AR_REPO",_SERVICE_NAME="$SERVICE_NAME",_REGION="$REGION" \
    --project="$PROJECT_ID"

echo -e "\n${GREEN}=== TradeSage Ops successfully deployed to Google Cloud Run! ===${NC}"
echo -e "To access the service, click the service URL in the terminal output above."
echo -e "Ensure to configure your GEMINI_API_KEY in the Cloud Run service variables if you want real-time LLM analysis."
