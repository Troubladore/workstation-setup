# Deployment and CI/CD Guide

Comprehensive guide for deploying the Astronomer Airflow platform and implementing continuous integration and delivery pipelines.

## 🎯 Deployment Philosophy

Our deployment strategy follows **GitOps** principles with progressive delivery:

```
     Code Push              Build & Test           Progressive Rollout
         │                       │                         │
    ┌────▼────┐            ┌────▼────┐            ┌───────▼───────┐
    │   Git   │───────────▶│   CI    │───────────▶│   Canary      │
    │  Commit │            │Pipeline │            │  Deployment   │
    └─────────┘            └─────────┘            └───────┬───────┘
                                                          │
                                                   ┌──────▼──────┐
                                                   │   Blue/Green │
                                                   │  Deployment  │
                                                   └──────┬──────┘
                                                          │
                                                   ┌──────▼──────┐
                                                   │ Production  │
                                                   │   Rollout   │
                                                   └─────────────┘
```

## 📚 Documentation Structure

### Core Deployment
- **[Environment Setup](#environment-setup)** - Development, staging, production
- **[CI/CD Pipeline](#cicd-pipeline)** - GitHub Actions, GitLab CI, Jenkins
- **[Deployment Strategies](#deployment-strategies)** - Blue/green, canary, rolling
- **[Infrastructure as Code](#infrastructure-as-code)** - Terraform, Helm charts

### Advanced Topics
- **[Secret Management](#secret-management)** - Vault, Sealed Secrets
- **[Disaster Recovery](#disaster-recovery)** - Backup and restore
- **[Multi-Region Deployment](#multi-region-deployment)** - Global distribution
- **[Rollback Procedures](#rollback-procedures)** - Safe rollback strategies

## 🏗️ Environment Setup

### **Environment Configuration**

```yaml
# environments/config.yaml
environments:
  development:
    cluster: dev-cluster
    namespace: airflow-dev
    replicas:
      scheduler: 1
      webserver: 1
      worker: 2
    resources:
      scheduler:
        cpu: 500m
        memory: 1Gi
      worker:
        cpu: 1000m
        memory: 2Gi
    database:
      type: postgres
      host: dev-postgres.internal
      size: small
    features:
      debug_mode: true
      example_dags: true
      test_connections: true

  staging:
    cluster: staging-cluster
    namespace: airflow-staging
    replicas:
      scheduler: 2
      webserver: 2
      worker: 4
    resources:
      scheduler:
        cpu: 1000m
        memory: 2Gi
      worker:
        cpu: 2000m
        memory: 4Gi
    database:
      type: postgres
      host: staging-postgres.internal
      size: medium
      backup_enabled: true
    features:
      debug_mode: false
      example_dags: false
      monitoring: true

  production:
    cluster: prod-cluster
    namespace: airflow-prod
    replicas:
      scheduler: 3
      webserver: 3
      worker: 10
    resources:
      scheduler:
        cpu: 2000m
        memory: 4Gi
      worker:
        cpu: 4000m
        memory: 8Gi
    database:
      type: postgres
      host: prod-postgres.internal
      size: large
      backup_enabled: true
      high_availability: true
    features:
      debug_mode: false
      example_dags: false
      monitoring: true
      alerting: true
      audit_logging: true
```

### **Kubernetes Deployment**

```yaml
# k8s/base/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: airflow-scheduler
  labels:
    component: scheduler
    tier: airflow
spec:
  replicas: {{ .Values.scheduler.replicas }}
  selector:
    matchLabels:
      component: scheduler
  template:
    metadata:
      labels:
        component: scheduler
        version: {{ .Values.image.tag }}
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
    spec:
      serviceAccountName: airflow
      initContainers:
        - name: wait-for-db
          image: busybox:1.35
          command:
            - sh
            - -c
            - |
              until nc -z {{ .Values.database.host }} {{ .Values.database.port }};
              do
                echo "Waiting for database...";
                sleep 2;
              done
        - name: run-migrations
          image: {{ .Values.image.repository }}:{{ .Values.image.tag }}
          command:
            - airflow
            - db
            - upgrade
          env:
            - name: AIRFLOW__DATABASE__SQL_ALCHEMY_CONN
              valueFrom:
                secretKeyRef:
                  name: airflow-database
                  key: connection
      containers:
        - name: scheduler
          image: {{ .Values.image.repository }}:{{ .Values.image.tag }}
          command:
            - airflow
            - scheduler
          env:
            - name: AIRFLOW__CORE__EXECUTOR
              value: {{ .Values.executor }}
            - name: AIRFLOW__DATABASE__SQL_ALCHEMY_CONN
              valueFrom:
                secretKeyRef:
                  name: airflow-database
                  key: connection
          resources:
            requests:
              cpu: {{ .Values.scheduler.resources.requests.cpu }}
              memory: {{ .Values.scheduler.resources.requests.memory }}
            limits:
              cpu: {{ .Values.scheduler.resources.limits.cpu }}
              memory: {{ .Values.scheduler.resources.limits.memory }}
          volumeMounts:
            - name: dags
              mountPath: /opt/airflow/dags
            - name: logs
              mountPath: /opt/airflow/logs
            - name: config
              mountPath: /opt/airflow/airflow.cfg
              subPath: airflow.cfg
          livenessProbe:
            exec:
              command:
                - airflow
                - jobs
                - check
                - --job-type
                - SchedulerJob
            initialDelaySeconds: 30
            periodSeconds: 30
            timeoutSeconds: 10
            failureThreshold: 3
          readinessProbe:
            exec:
              command:
                - airflow
                - db
                - check
            initialDelaySeconds: 10
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
      volumes:
        - name: dags
          persistentVolumeClaim:
            claimName: airflow-dags
        - name: logs
          persistentVolumeClaim:
            claimName: airflow-logs
        - name: config
          configMap:
            name: airflow-config
---
apiVersion: v1
kind: Service
metadata:
  name: airflow-scheduler
  labels:
    component: scheduler
spec:
  type: ClusterIP
  selector:
    component: scheduler
  ports:
    - name: scheduler
      port: 8793
      targetPort: 8793
    - name: metrics
      port: 8080
      targetPort: 8080
```

## 🔄 CI/CD Pipeline

### **GitHub Actions Workflow**

```yaml
# .github/workflows/deploy.yml
name: Deploy Airflow Platform

on:
  push:
    branches:
      - main
      - staging
      - develop
  pull_request:
    types: [opened, synchronize, reopened]

env:
  REGISTRY: registry.localhost
  IMAGE_NAME: airflow-platform

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run unit tests
        run: |
          pytest tests/unit/ --cov=dags --cov-report=xml

      - name: Run integration tests
        run: |
          docker-compose -f docker-compose.test.yml up -d
          pytest tests/integration/
          docker-compose -f docker-compose.test.yml down

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

      - name: Run Snyk security scan
        uses: snyk/actions/python@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}

  build:
    needs: [test, security-scan]
    runs-on: ubuntu-latest
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Log in to Container Registry
        uses: docker/login-action@v2
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ secrets.REGISTRY_USERNAME }}
          password: ${{ secrets.REGISTRY_PASSWORD }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha,prefix={{branch}}-

      - name: Build and push Docker image
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:buildcache
          cache-to: type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:buildcache,mode=max
          build-args: |
            BUILD_DATE=${{ github.event.head_commit.timestamp }}
            VCS_REF=${{ github.sha }}
            VERSION=${{ steps.meta.outputs.version }}

  deploy-dev:
    if: github.ref == 'refs/heads/develop'
    needs: build
    runs-on: ubuntu-latest
    environment: development
    steps:
      - uses: actions/checkout@v3

      - name: Install kubectl
        uses: azure/setup-kubectl@v3
        with:
          version: 'v1.28.0'

      - name: Configure kubectl
        run: |
          echo "${{ secrets.KUBECONFIG_DEV }}" | base64 -d > kubeconfig
          export KUBECONFIG=$(pwd)/kubeconfig

      - name: Deploy to development
        run: |
          helm upgrade --install airflow-dev ./charts/airflow \
            --namespace airflow-dev \
            --create-namespace \
            --values ./environments/dev/values.yaml \
            --set image.tag=${{ needs.build.outputs.image-tag }} \
            --wait \
            --timeout 10m

      - name: Run smoke tests
        run: |
          kubectl exec -n airflow-dev deploy/airflow-scheduler -- \
            airflow dags list
          kubectl exec -n airflow-dev deploy/airflow-scheduler -- \
            airflow connections list

  deploy-staging:
    if: github.ref == 'refs/heads/staging'
    needs: build
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v3

      - name: Deploy to staging
        run: |
          helm upgrade --install airflow-staging ./charts/airflow \
            --namespace airflow-staging \
            --create-namespace \
            --values ./environments/staging/values.yaml \
            --set image.tag=${{ needs.build.outputs.image-tag }} \
            --wait \
            --timeout 15m

      - name: Run E2E tests
        run: |
          npm install -g newman
          newman run tests/e2e/airflow-api.postman_collection.json \
            --environment tests/e2e/staging.postman_environment.json

      - name: Performance tests
        run: |
          docker run --rm \
            -v $(pwd)/tests/performance:/scripts \
            loadimpact/k6 run /scripts/load-test.js

  deploy-production:
    if: github.ref == 'refs/heads/main'
    needs: [build, deploy-staging]
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v3

      - name: Create deployment
        uses: chrnorm/deployment-action@v2
        id: deployment
        with:
          token: ${{ github.token }}
          environment: production
          ref: ${{ github.sha }}

      - name: Deploy canary
        run: |
          helm upgrade --install airflow-canary ./charts/airflow \
            --namespace airflow-prod \
            --values ./environments/prod/values.yaml \
            --values ./environments/prod/canary.yaml \
            --set image.tag=${{ needs.build.outputs.image-tag }} \
            --set canary.enabled=true \
            --set canary.weight=10 \
            --wait \
            --timeout 15m

      - name: Monitor canary metrics
        run: |
          ./scripts/monitor-canary.sh \
            --duration 300 \
            --error-threshold 1 \
            --latency-p99 1000

      - name: Promote to production
        if: success()
        run: |
          helm upgrade --install airflow-prod ./charts/airflow \
            --namespace airflow-prod \
            --values ./environments/prod/values.yaml \
            --set image.tag=${{ needs.build.outputs.image-tag }} \
            --set canary.enabled=false \
            --wait \
            --timeout 20m

      - name: Update deployment status
        if: always()
        uses: chrnorm/deployment-status@v2
        with:
          token: ${{ github.token }}
          deployment-id: ${{ steps.deployment.outputs.deployment_id }}
          state: ${{ job.status }}
```

### **GitLab CI Pipeline**

```yaml
# .gitlab-ci.yml
stages:
  - test
  - build
  - deploy-dev
  - deploy-staging
  - deploy-production

variables:
  DOCKER_DRIVER: overlay2
  DOCKER_TLS_CERTDIR: ""
  REGISTRY: $CI_REGISTRY
  IMAGE_NAME: $CI_REGISTRY_IMAGE/airflow

test:unit:
  stage: test
  image: python:3.10
  script:
    - pip install -r requirements-test.txt
    - pytest tests/unit/ --junitxml=report.xml
  artifacts:
    reports:
      junit: report.xml

test:integration:
  stage: test
  services:
    - docker:dind
  script:
    - docker-compose -f docker-compose.test.yml up --abort-on-container-exit
  artifacts:
    reports:
      junit: tests/results/*.xml

security:scan:
  stage: test
  image:
    name: aquasec/trivy:latest
    entrypoint: [""]
  script:
    - trivy fs --no-progress --format json --output trivy.json .
  artifacts:
    reports:
      container_scanning: trivy.json

build:image:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - docker build -t $IMAGE_NAME:$CI_COMMIT_SHA .
    - docker tag $IMAGE_NAME:$CI_COMMIT_SHA $IMAGE_NAME:$CI_COMMIT_REF_SLUG
    - docker push $IMAGE_NAME:$CI_COMMIT_SHA
    - docker push $IMAGE_NAME:$CI_COMMIT_REF_SLUG
  only:
    - branches
    - tags

deploy:dev:
  stage: deploy-dev
  image: bitnami/kubectl:latest
  script:
    - kubectl config use-context $K8S_CONTEXT_DEV
    - helm upgrade --install airflow-dev ./charts/airflow
        --namespace airflow-dev
        --values environments/dev/values.yaml
        --set image.tag=$CI_COMMIT_SHA
        --wait
  environment:
    name: development
    url: https://airflow-dev.example.com
  only:
    - develop

deploy:staging:
  stage: deploy-staging
  image: bitnami/kubectl:latest
  script:
    - kubectl config use-context $K8S_CONTEXT_STAGING
    - helm upgrade --install airflow-staging ./charts/airflow
        --namespace airflow-staging
        --values environments/staging/values.yaml
        --set image.tag=$CI_COMMIT_SHA
        --wait
  environment:
    name: staging
    url: https://airflow-staging.example.com
  only:
    - staging

deploy:production:
  stage: deploy-production
  image: bitnami/kubectl:latest
  script:
    - kubectl config use-context $K8S_CONTEXT_PROD
    - |
      helm upgrade --install airflow-prod ./charts/airflow \
        --namespace airflow-prod \
        --values environments/prod/values.yaml \
        --set image.tag=$CI_COMMIT_SHA \
        --wait
  environment:
    name: production
    url: https://airflow.example.com
  when: manual
  only:
    - main
```

## 🚀 Deployment Strategies

### **Blue/Green Deployment**

```bash
#!/bin/bash
# scripts/blue-green-deploy.sh

set -e

NAMESPACE="airflow-prod"
NEW_VERSION=$1
CURRENT_COLOR=$(kubectl get service airflow-webserver -n $NAMESPACE -o jsonpath='{.spec.selector.color}')

if [ "$CURRENT_COLOR" == "blue" ]; then
    NEW_COLOR="green"
else
    NEW_COLOR="blue"
fi

echo "Deploying $NEW_COLOR environment with version $NEW_VERSION"

# Deploy new version
helm upgrade --install airflow-$NEW_COLOR ./charts/airflow \
    --namespace $NAMESPACE \
    --values environments/prod/values.yaml \
    --set deployment.color=$NEW_COLOR \
    --set image.tag=$NEW_VERSION \
    --wait

# Run health checks
echo "Running health checks..."
kubectl exec -n $NAMESPACE deploy/airflow-$NEW_COLOR-scheduler -- \
    airflow db check

# Run smoke tests
./scripts/smoke-tests.sh $NEW_COLOR

# Switch traffic
echo "Switching traffic to $NEW_COLOR"
kubectl patch service airflow-webserver -n $NAMESPACE \
    -p '{"spec":{"selector":{"color":"'$NEW_COLOR'"}}}'

# Monitor for 5 minutes
echo "Monitoring new deployment..."
sleep 300

# Check error rates
ERROR_RATE=$(kubectl exec -n $NAMESPACE deploy/prometheus -- \
    promtool query instant 'rate(airflow_dag_failure_total[5m])' | \
    jq '.data.result[0].value[1]')

if (( $(echo "$ERROR_RATE > 0.1" | bc -l) )); then
    echo "High error rate detected, rolling back..."
    kubectl patch service airflow-webserver -n $NAMESPACE \
        -p '{"spec":{"selector":{"color":"'$CURRENT_COLOR'"}}}'
    exit 1
fi

echo "Deployment successful. Cleaning up old deployment in 24 hours..."
echo "kubectl delete deployment airflow-$CURRENT_COLOR-scheduler -n $NAMESPACE" | at now + 24 hours
```

### **Canary Deployment**

```yaml
# k8s/canary/virtual-service.yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: airflow-canary
  namespace: airflow-prod
spec:
  hosts:
    - airflow.example.com
  http:
    - match:
        - headers:
            canary:
              exact: "true"
      route:
        - destination:
            host: airflow-webserver
            subset: canary
          weight: 100
    - route:
        - destination:
            host: airflow-webserver
            subset: stable
          weight: 90
        - destination:
            host: airflow-webserver
            subset: canary
          weight: 10
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: airflow-webserver
  namespace: airflow-prod
spec:
  host: airflow-webserver
  subsets:
    - name: stable
      labels:
        version: stable
    - name: canary
      labels:
        version: canary
```

### **Progressive Rollout with Flagger**

```yaml
# k8s/flagger/canary.yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: airflow
  namespace: airflow-prod
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: airflow-webserver
  progressDeadlineSeconds: 600
  service:
    port: 8080
    targetPort: 8080
    gateways:
      - public-gateway.istio-system.svc.cluster.local
    hosts:
      - airflow.example.com
  analysis:
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 10
    metrics:
      - name: request-success-rate
        thresholdRange:
          min: 99
        interval: 1m
      - name: request-duration
        thresholdRange:
          max: 500
        interval: 1m
    webhooks:
      - name: load-test
        url: http://flagger-loadtester/
        timeout: 5s
        metadata:
          cmd: "hey -z 1m -q 10 -c 2 http://airflow.example.com/"
```

## 🏗️ Infrastructure as Code

### **Terraform Configuration**

```hcl
# terraform/main.tf
terraform {
  required_version = ">= 1.0"

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "terraform-state-airflow"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
    dynamodb_table = "terraform-locks"
    encrypt = true
  }
}

# EKS Cluster
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = var.cluster_name
  cluster_version = "1.28"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    general = {
      desired_size = 3
      min_size     = 3
      max_size     = 10

      instance_types = ["m5.xlarge"]

      k8s_labels = {
        Environment = var.environment
        Application = "airflow"
      }
    }

    workers = {
      desired_size = 5
      min_size     = 5
      max_size     = 20

      instance_types = ["m5.2xlarge"]

      k8s_labels = {
        Environment = var.environment
        Application = "airflow"
        NodeType    = "worker"
      }

      taints = [
        {
          key    = "airflow-worker"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
      ]
    }
  }

  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }
}

# RDS Database
module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"

  identifier = "${var.environment}-airflow-db"

  engine            = "postgres"
  engine_version    = "15.4"
  instance_class    = "db.r6g.xlarge"
  allocated_storage = 100
  storage_encrypted = true

  db_name  = "airflow"
  username = "airflow"
  password = random_password.db_password.result

  vpc_security_group_ids = [module.security_group.security_group_id]
  db_subnet_group_name   = module.vpc.database_subnet_group_name

  backup_retention_period = 30
  backup_window          = "03:00-06:00"
  maintenance_window     = "Mon:00:00-Mon:03:00"

  enabled_cloudwatch_logs_exports = ["postgresql"]

  multi_az               = true
  deletion_protection    = true
  skip_final_snapshot    = false
  final_snapshot_identifier = "${var.environment}-airflow-db-final-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  tags = {
    Environment = var.environment
    Application = "airflow"
  }
}

# S3 Buckets
resource "aws_s3_bucket" "airflow_logs" {
  bucket = "${var.environment}-airflow-logs"

  tags = {
    Environment = var.environment
    Application = "airflow"
  }
}

resource "aws_s3_bucket_versioning" "airflow_logs" {
  bucket = aws_s3_bucket.airflow_logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "airflow_logs" {
  bucket = aws_s3_bucket.airflow_logs.id

  rule {
    id = "delete-old-logs"

    expiration {
      days = 90
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 60
      storage_class = "GLACIER"
    }

    status = "Enabled"
  }
}

# Helm Release
resource "helm_release" "airflow" {
  name       = "airflow"
  namespace  = "airflow-${var.environment}"
  repository = "https://airflow.apache.org"
  chart      = "airflow"
  version    = var.airflow_chart_version

  values = [
    templatefile("${path.module}/values.yaml.tpl", {
      environment      = var.environment
      image_tag       = var.airflow_image_tag
      database_host   = module.rds.db_instance_address
      database_password = random_password.db_password.result
      s3_logs_bucket  = aws_s3_bucket.airflow_logs.id
    })
  ]

  depends_on = [
    module.eks,
    module.rds
  ]
}
```

### **Helm Values Template**

```yaml
# charts/airflow/values.yaml
replicaCount:
  scheduler: {{ .Values.scheduler.replicas }}
  webserver: {{ .Values.webserver.replicas }}
  worker: {{ .Values.worker.replicas }}

image:
  repository: {{ .Values.image.repository }}
  tag: {{ .Values.image.tag | default .Chart.AppVersion }}
  pullPolicy: IfNotPresent

airflow:
  config:
    AIRFLOW__CORE__EXECUTOR: KubernetesExecutor
    AIRFLOW__CORE__LOAD_EXAMPLES: "False"
    AIRFLOW__WEBSERVER__EXPOSE_CONFIG: "False"
    AIRFLOW__CORE__DAGS_FOLDER: /opt/airflow/dags
    AIRFLOW__LOGGING__REMOTE_LOGGING: "True"
    AIRFLOW__LOGGING__REMOTE_BASE_LOG_FOLDER: s3://{{ .Values.logging.s3Bucket }}/logs

database:
  type: postgres
  host: {{ .Values.database.host }}
  port: {{ .Values.database.port }}
  database: {{ .Values.database.name }}
  user: {{ .Values.database.user }}
  passwordSecret: airflow-database-password
  passwordSecretKey: password

redis:
  enabled: {{ eq .Values.executor "CeleryExecutor" }}
  persistence:
    enabled: true
    size: 10Gi

persistence:
  enabled: true
  dags:
    enabled: true
    size: 10Gi
    storageClassName: gp3
    accessMode: ReadWriteMany
  logs:
    enabled: true
    size: 100Gi
    storageClassName: gp3
    accessMode: ReadWriteMany

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
  hosts:
    - host: {{ .Values.ingress.hostname }}
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: airflow-tls
      hosts:
        - {{ .Values.ingress.hostname }}

resources:
  scheduler:
    requests:
      cpu: {{ .Values.scheduler.resources.requests.cpu }}
      memory: {{ .Values.scheduler.resources.requests.memory }}
    limits:
      cpu: {{ .Values.scheduler.resources.limits.cpu }}
      memory: {{ .Values.scheduler.resources.limits.memory }}

  webserver:
    requests:
      cpu: {{ .Values.webserver.resources.requests.cpu }}
      memory: {{ .Values.webserver.resources.requests.memory }}
    limits:
      cpu: {{ .Values.webserver.resources.limits.cpu }}
      memory: {{ .Values.webserver.resources.limits.memory }}

  worker:
    requests:
      cpu: {{ .Values.worker.resources.requests.cpu }}
      memory: {{ .Values.worker.resources.requests.memory }}
    limits:
      cpu: {{ .Values.worker.resources.limits.cpu }}
      memory: {{ .Values.worker.resources.limits.memory }}

autoscaling:
  enabled: {{ .Values.autoscaling.enabled }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  targetCPUUtilizationPercentage: {{ .Values.autoscaling.targetCPU }}
  targetMemoryUtilizationPercentage: {{ .Values.autoscaling.targetMemory }}

monitoring:
  enabled: {{ .Values.monitoring.enabled }}
  serviceMonitor:
    enabled: true
    interval: 30s
  prometheusRule:
    enabled: true
```

## 🔐 Secret Management

### **Sealed Secrets**

```yaml
# k8s/sealed-secrets/database-secret.yaml
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: airflow-database
  namespace: airflow-prod
spec:
  encryptedData:
    connection: AgBvA7Q6F2Z... # Encrypted database connection string
    password: AgCmN9P3K8X...   # Encrypted password
  template:
    metadata:
      name: airflow-database
      namespace: airflow-prod
    type: Opaque
```

### **HashiCorp Vault Integration**

```python
# plugins/secrets/vault_backend.py
from airflow.secrets import BaseSecretsBackend
import hvac

class VaultSecretsBackend(BaseSecretsBackend):
    """HashiCorp Vault secrets backend"""

    def __init__(
        self,
        vault_url="http://vault:8200",
        auth_type="kubernetes",
        role="airflow",
        mount_point="airflow",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.client = hvac.Client(url=vault_url)

        if auth_type == "kubernetes":
            with open("/var/run/secrets/kubernetes.io/serviceaccount/token") as f:
                jwt = f.read()
            self.client.auth.kubernetes.login(role=role, jwt=jwt)

        self.mount_point = mount_point

    def get_connection(self, conn_id):
        """Get connection from Vault"""
        path = f"{self.mount_point}/connections/{conn_id}"
        response = self.client.secrets.kv.v2.read_secret_version(path=path)

        if response:
            secret = response["data"]["data"]
            return self._format_connection(secret)
        return None

    def get_variable(self, key):
        """Get variable from Vault"""
        path = f"{self.mount_point}/variables/{key}"
        response = self.client.secrets.kv.v2.read_secret_version(path=path)

        if response:
            return response["data"]["data"]["value"]
        return None
```

## 🔄 Rollback Procedures

### **Automated Rollback**

```bash
#!/bin/bash
# scripts/rollback.sh

set -e

NAMESPACE=$1
RELEASE_NAME=$2
ROLLBACK_VERSION=${3:-0}  # Default to previous version

echo "Rolling back $RELEASE_NAME in namespace $NAMESPACE"

# Get current version
CURRENT_VERSION=$(helm list -n $NAMESPACE -o json | \
    jq -r ".[] | select(.name==\"$RELEASE_NAME\") | .revision")

echo "Current version: $CURRENT_VERSION"

# Check health before rollback
kubectl exec -n $NAMESPACE deploy/${RELEASE_NAME}-scheduler -- \
    airflow db check || echo "Database check failed"

# Perform rollback
helm rollback $RELEASE_NAME $ROLLBACK_VERSION -n $NAMESPACE --wait

# Verify rollback
NEW_VERSION=$(helm list -n $NAMESPACE -o json | \
    jq -r ".[] | select(.name==\"$RELEASE_NAME\") | .revision")

echo "Rolled back from version $CURRENT_VERSION to $NEW_VERSION"

# Run health checks
./scripts/health-check.sh $NAMESPACE $RELEASE_NAME

# Send notification
curl -X POST $SLACK_WEBHOOK_URL \
    -H 'Content-Type: application/json' \
    -d "{\"text\":\"🔄 Rollback completed: $RELEASE_NAME from v$CURRENT_VERSION to v$NEW_VERSION\"}"
```

## 📊 Deployment Monitoring

### **Deployment Dashboard**

```python
# monitoring/deployment_metrics.py
from prometheus_client import Gauge, Counter, Histogram
import time

# Deployment metrics
deployment_duration = Histogram(
    'deployment_duration_seconds',
    'Time taken to complete deployment',
    ['environment', 'strategy']
)

deployment_success = Counter(
    'deployment_success_total',
    'Successful deployments',
    ['environment', 'version']
)

deployment_failure = Counter(
    'deployment_failure_total',
    'Failed deployments',
    ['environment', 'version', 'reason']
)

rollback_count = Counter(
    'deployment_rollback_total',
    'Number of rollbacks',
    ['environment', 'from_version', 'to_version']
)

active_version = Gauge(
    'deployment_active_version',
    'Currently active version',
    ['environment', 'component']
)

class DeploymentMonitor:
    """Monitor deployment metrics"""

    def track_deployment(self, environment, version, strategy):
        """Track deployment metrics"""
        start_time = time.time()

        try:
            # Deployment logic here
            yield

            # Record success
            duration = time.time() - start_time
            deployment_duration.labels(
                environment=environment,
                strategy=strategy
            ).observe(duration)

            deployment_success.labels(
                environment=environment,
                version=version
            ).inc()

            active_version.labels(
                environment=environment,
                component='airflow'
            ).set(float(version.replace('.', '')))

        except Exception as e:
            # Record failure
            deployment_failure.labels(
                environment=environment,
                version=version,
                reason=str(e)
            ).inc()
            raise
```

## 🛡️ Disaster Recovery

### **Backup Strategy**

```bash
#!/bin/bash
# scripts/backup.sh

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/$TIMESTAMP"
S3_BUCKET="s3://airflow-backups"

echo "Starting backup at $TIMESTAMP"

# Backup database
kubectl exec -n airflow-prod deploy/postgres -- \
    pg_dump -U airflow airflow | \
    gzip > $BACKUP_DIR/database.sql.gz

# Backup DAGs
kubectl cp airflow-prod/airflow-scheduler:/opt/airflow/dags \
    $BACKUP_DIR/dags/

# Backup connections and variables
kubectl exec -n airflow-prod deploy/airflow-scheduler -- \
    airflow connections export /tmp/connections.json

kubectl cp airflow-prod/airflow-scheduler:/tmp/connections.json \
    $BACKUP_DIR/connections.json

kubectl exec -n airflow-prod deploy/airflow-scheduler -- \
    airflow variables export /tmp/variables.json

kubectl cp airflow-prod/airflow-scheduler:/tmp/variables.json \
    $BACKUP_DIR/variables.json

# Upload to S3
aws s3 sync $BACKUP_DIR $S3_BUCKET/$TIMESTAMP/

# Clean up old backups (keep last 30 days)
aws s3 ls $S3_BUCKET/ | \
    awk '{print $2}' | \
    head -n -30 | \
    xargs -I {} aws s3 rm --recursive $S3_BUCKET/{}

echo "Backup completed successfully"
```

### **Restore Procedure**

```bash
#!/bin/bash
# scripts/restore.sh

set -e

BACKUP_DATE=$1
S3_BUCKET="s3://airflow-backups"
RESTORE_DIR="/tmp/restore"

echo "Restoring from backup: $BACKUP_DATE"

# Download backup
aws s3 sync $S3_BUCKET/$BACKUP_DATE/ $RESTORE_DIR/

# Restore database
gunzip < $RESTORE_DIR/database.sql.gz | \
    kubectl exec -i -n airflow-prod deploy/postgres -- \
    psql -U airflow airflow

# Restore DAGs
kubectl cp $RESTORE_DIR/dags/ \
    airflow-prod/airflow-scheduler:/opt/airflow/dags/

# Restore connections
kubectl cp $RESTORE_DIR/connections.json \
    airflow-prod/airflow-scheduler:/tmp/connections.json

kubectl exec -n airflow-prod deploy/airflow-scheduler -- \
    airflow connections import /tmp/connections.json

# Restore variables
kubectl cp $RESTORE_DIR/variables.json \
    airflow-prod/airflow-scheduler:/tmp/variables.json

kubectl exec -n airflow-prod deploy/airflow-scheduler -- \
    airflow variables import /tmp/variables.json

# Restart components
kubectl rollout restart deployment/airflow-scheduler -n airflow-prod
kubectl rollout restart deployment/airflow-webserver -n airflow-prod

echo "Restore completed successfully"
```

## 💡 Deployment Checklist

### **Pre-Deployment**
- [ ] All tests passing (unit, integration, E2E)
- [ ] Security scans completed
- [ ] Code review approved
- [ ] Documentation updated
- [ ] Database migrations tested
- [ ] Rollback plan prepared
- [ ] Monitoring alerts configured
- [ ] Load testing completed

### **During Deployment**
- [ ] Backup current state
- [ ] Deploy to staging first
- [ ] Run smoke tests
- [ ] Monitor metrics
- [ ] Check error rates
- [ ] Verify data processing
- [ ] Test critical paths

### **Post-Deployment**
- [ ] Monitor for 24 hours
- [ ] Check performance metrics
- [ ] Review error logs
- [ ] Update runbook
- [ ] Document lessons learned
- [ ] Clean up old resources
- [ ] Send deployment report

---

*This completes the comprehensive documentation suite for the Astronomer Airflow platform.*