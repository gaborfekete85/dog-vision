# Dog Vision - Kubernetes Deployment Guide

This guide covers deploying the Dog Vision application to Kubernetes using Helm.

## Overview

The deployment includes:
- **Deployment**: Manages application pods with health checks
- **Service**: ClusterIP service exposing port 5001
- **Ingress**: NGINX ingress controller routing traffic from dog-vision.rewura.com
- **Docker Image**: `gabendockerzone/dog-vision:latest`
- **Namespace**: `dog-vision`

## Prerequisites

Before deploying, ensure you have:

1. **Docker** installed and running
2. **kubectl** configured to access your Kubernetes cluster
3. **Helm 3** installed
4. **Docker Hub credentials** configured (for pushing images)
   ```bash
   docker login
   ```

## Quick Start

### 1. Setup NGINX Ingress Controller

Run the setup script to install the NGINX ingress controller:

```bash
./setup-ingress.sh
```

This will:
- Install NGINX Ingress Controller
- Wait for the LoadBalancer to get an external IP
- Display the IP address for DNS configuration

**Important**: Note the external IP address and configure your DNS:
- Create an A record: `dog-vision.rewura.com` → `<EXTERNAL_IP>`

### 2. Deploy the Application

Run the redeploy script to build, push, and deploy:

```bash
./redeploy.sh
```

This script will:
1. Build the Docker image
2. Push to `gabendockerzone/dog-vision:latest`
3. Create/verify the `dog-vision` namespace
4. Deploy/upgrade the Helm release
5. Show deployment status

## Manual Deployment

If you prefer to run commands manually:

### Build and Push Docker Image

```bash
docker build -t gabendockerzone/dog-vision:latest .
docker push gabendockerzone/dog-vision:latest
```

### Create Namespace

```bash
kubectl create namespace dog-vision
```

### Install Helm Chart

```bash
helm install dog-vision ./helm/dog-vision --namespace dog-vision
```

### Upgrade Existing Release

```bash
helm upgrade dog-vision ./helm/dog-vision --namespace dog-vision
```

## Helm Chart Structure

```
helm/dog-vision/
├── Chart.yaml              # Chart metadata
├── values.yaml            # Configuration values
└── templates/
    ├── deployment.yaml    # Pod deployment
    ├── service.yaml       # Service definition
    └── ingress.yaml       # Ingress routing
```

## Configuration

Edit `helm/dog-vision/values.yaml` to customize:

### Image Settings
```yaml
image:
  repository: gabendockerzone/dog-vision
  tag: "latest"
  pullPolicy: Always
```

### Resources
```yaml
resources:
  limits:
    cpu: 2000m
    memory: 4Gi
  requests:
    cpu: 500m
    memory: 2Gi
```

### Ingress Domain
```yaml
ingress:
  hosts:
    - host: dog-vision.rewura.com
      paths:
        - path: /
          pathType: Prefix
```

## Accessing the Application

Once deployed and DNS is configured:

- **Application URL**: https://dog-vision.rewura.com
- **Health Check**: https://dog-vision.rewura.com/api/health
- **Breeds API**: https://dog-vision.rewura.com/api/breeds

## Monitoring

### View Pods
```bash
kubectl get pods -n dog-vision
```

### View Services
```bash
kubectl get services -n dog-vision
```

### View Ingress
```bash
kubectl get ingress -n dog-vision
```

### View Logs
```bash
kubectl logs -f -n dog-vision -l app=dog-vision
```

### Describe Pod (for troubleshooting)
```bash
kubectl describe pod <pod-name> -n dog-vision
```

## Health Checks

The deployment includes:

### Liveness Probe
- Endpoint: `/api/health`
- Initial delay: 30 seconds
- Period: 10 seconds

### Readiness Probe
- Endpoint: `/api/health`
- Initial delay: 10 seconds
- Period: 5 seconds

## Troubleshooting

### Pod Not Starting

Check pod status:
```bash
kubectl describe pod -n dog-vision -l app=dog-vision
```

Check logs:
```bash
kubectl logs -n dog-vision -l app=dog-vision
```

### Ingress Not Working

1. Verify NGINX Ingress Controller is running:
```bash
kubectl get pods -n ingress-nginx
```

2. Check ingress configuration:
```bash
kubectl describe ingress dog-vision -n dog-vision
```

3. Verify DNS resolution:
```bash
nslookup dog-vision.rewura.com
```

### Image Pull Errors

Ensure the image exists on Docker Hub:
```bash
docker pull gabendockerzone/dog-vision:latest
```

If the repository is private, create an image pull secret:
```bash
kubectl create secret docker-registry regcred \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username=<your-username> \
  --docker-password=<your-password> \
  --docker-email=<your-email> \
  -n dog-vision
```

Then update `deployment.yaml` to include:
```yaml
spec:
  template:
    spec:
      imagePullSecrets:
      - name: regcred
```

## Uninstalling

To remove the application:

```bash
helm uninstall dog-vision -n dog-vision
kubectl delete namespace dog-vision
```

To remove NGINX Ingress Controller:

```bash
helm uninstall ingress-nginx -n ingress-nginx
kubectl delete namespace ingress-nginx
```

## SSL/TLS (Optional)

The ingress is configured with cert-manager annotations for automatic SSL certificate generation using Let's Encrypt.

To enable SSL:

1. Install cert-manager:
```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

2. Create a ClusterIssuer for Let's Encrypt:
```bash
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

3. Redeploy the application:
```bash
./redeploy.sh
```

The certificate will be automatically requested and configured.

## Support

For issues or questions:
- Check pod logs: `kubectl logs -f -n dog-vision -l app=dog-vision`
- Check events: `kubectl get events -n dog-vision --sort-by='.lastTimestamp'`
