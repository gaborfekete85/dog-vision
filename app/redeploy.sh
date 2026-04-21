#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="gabendockerzone/dog-vision"
IMAGE_TAG="latest"
NAMESPACE="dog-vision"
HELM_CHART="./helm/dog-vision"
RELEASE_NAME="dog-vision"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Dog Vision Deployment Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Step 1: Build Docker image
echo -e "${YELLOW}[1/4] Building Docker image...${NC}"
docker build --platform linux/amd64 -t ${IMAGE_NAME}:${IMAGE_TAG} .
echo -e "${GREEN}✓ Docker image built successfully${NC}"
echo ""

# Step 2: Push Docker image
echo -e "${YELLOW}[2/4] Pushing Docker image to registry...${NC}"
docker push ${IMAGE_NAME}:${IMAGE_TAG}
echo -e "${GREEN}✓ Docker image pushed successfully${NC}"
echo ""

# Step 3: Check if namespace exists, create if not
echo -e "${YELLOW}[3/4] Checking Kubernetes namespace...${NC}"
if kubectl get namespace ${NAMESPACE} > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Namespace '${NAMESPACE}' already exists${NC}"
else
    echo -e "${YELLOW}Creating namespace '${NAMESPACE}'...${NC}"
    kubectl create namespace ${NAMESPACE}
    echo -e "${GREEN}✓ Namespace created${NC}"
fi
echo ""

# Step 4: Deploy/Upgrade Helm chart
echo -e "${YELLOW}[4/4] Deploying to Kubernetes...${NC}"
if helm list -n ${NAMESPACE} | grep -q ${RELEASE_NAME}; then
    echo -e "${YELLOW}Upgrading existing release...${NC}"
    helm upgrade ${RELEASE_NAME} ${HELM_CHART} \
        --namespace ${NAMESPACE} \
        --wait \
        --timeout 5m
    echo -e "${GREEN}✓ Helm chart upgraded successfully${NC}"
else
    echo -e "${YELLOW}Installing new release...${NC}"
    helm install ${RELEASE_NAME} ${HELM_CHART} \
        --namespace ${NAMESPACE} \
        --create-namespace \
        --wait \
        --timeout 5m
    echo -e "${GREEN}✓ Helm chart installed successfully${NC}"
fi
echo ""

# Step 5: Show deployment status
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Status${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
kubectl get pods -n ${NAMESPACE}
echo ""
kubectl get services -n ${NAMESPACE}
echo ""
kubectl get ingress -n ${NAMESPACE}
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Application should be accessible at:${NC}"
echo -e "${GREEN}https://dog-vision.rewura.com${NC}"
echo ""
echo -e "${YELLOW}To view logs, run:${NC}"
echo -e "kubectl logs -f -n ${NAMESPACE} -l app=${RELEASE_NAME}"
echo ""
