#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}NGINX Ingress Controller Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Step 1: Install NGINX Ingress Controller
echo -e "${YELLOW}[1/3] Installing NGINX Ingress Controller...${NC}"
if kubectl get namespace ingress-nginx > /dev/null 2>&1; then
    echo -e "${YELLOW}NGINX Ingress Controller namespace already exists${NC}"
else
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm repo update

    helm install ingress-nginx ingress-nginx/ingress-nginx \
        --create-namespace \
        --namespace ingress-nginx \
        --set controller.service.type=LoadBalancer \
        --wait \
        --timeout 5m

    echo -e "${GREEN}✓ NGINX Ingress Controller installed${NC}"
fi
echo ""

# Step 2: Wait for LoadBalancer IP
echo -e "${YELLOW}[2/3] Waiting for LoadBalancer external IP...${NC}"
echo -e "${YELLOW}This may take a few minutes...${NC}"

ATTEMPTS=0
MAX_ATTEMPTS=60
while [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
    EXTERNAL_IP=$(kubectl get service ingress-nginx-controller \
        -n ingress-nginx \
        -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")

    if [ -n "$EXTERNAL_IP" ] && [ "$EXTERNAL_IP" != "null" ]; then
        echo -e "${GREEN}✓ LoadBalancer IP assigned: ${EXTERNAL_IP}${NC}"
        break
    fi

    echo -e "${YELLOW}Waiting for external IP... (attempt $((ATTEMPTS+1))/${MAX_ATTEMPTS})${NC}"
    sleep 5
    ATTEMPTS=$((ATTEMPTS+1))
done

if [ -z "$EXTERNAL_IP" ] || [ "$EXTERNAL_IP" == "null" ]; then
    echo -e "${RED}Warning: Could not retrieve external IP after ${MAX_ATTEMPTS} attempts${NC}"
    echo -e "${YELLOW}You may need to check your cloud provider's load balancer configuration${NC}"
else
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}DNS Configuration Required${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${YELLOW}Please configure your DNS to point:${NC}"
    echo -e "${GREEN}dog-vision.rewura.com${NC} → ${GREEN}${EXTERNAL_IP}${NC}"
    echo ""
    echo -e "${YELLOW}You can create an A record in your DNS provider:${NC}"
    echo -e "Host: ${GREEN}dog-vision.rewura.com${NC}"
    echo -e "Type: ${GREEN}A${NC}"
    echo -e "Value: ${GREEN}${EXTERNAL_IP}${NC}"
    echo ""
fi

# Step 3: Show ingress controller status
echo -e "${YELLOW}[3/3] Ingress Controller Status:${NC}"
kubectl get pods -n ingress-nginx
echo ""
kubectl get services -n ingress-nginx
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}NGINX Ingress Controller setup complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Configure DNS as shown above"
echo -e "2. Run ${GREEN}./redeploy.sh${NC} to deploy the application"
echo ""
