# Deployment Guide: AWS + Neon PostgreSQL

This guide explains how to deploy the Student Complaint Management System backend to **AWS App Runner** (recommended serverless container service) connected to your **Neon PostgreSQL** database, and configure a continuous deployment pipeline using **GitHub Actions**.

---

## Step 1: Set up Amazon ECR (Elastic Container Registry)
Amazon ECR will store your built Docker images.

1. Open the [Amazon ECR Console](https://console.aws.amazon.com/ecr/).
2. Click **Create Repository**.
3. Select **Private** settings.
4. Enter a name (e.g. `student-complaint-backend`).
5. Leave other settings as default and click **Create repository**.
6. Copy the repository URL (e.g., `123456789012.dkr.ecr.us-east-1.amazonaws.com/student-complaint-backend`).

---

## Step 2: Set up AWS App Runner Service
AWS App Runner pulls your container from ECR, runs it, creates an HTTPS link, and scales up/down automatically.

1. Open the [AWS App Runner Console](https://console.aws.amazon.com/apprunner/).
2. Click **Create service**.
3. Under **Source**:
   - Repository type: Select **Container registry**.
   - Provider: Select **Amazon ECR**.
   - Container image URI: Click **Browse** and select your ECR repository and the `latest` tag.
4. Under **Deployment settings**:
   - Select **Automatic** (to redeploy every time a new image is pushed to ECR).
   - Set up or select an IAM connection role (typically `AppRunnerECRAccessRole` which allows App Runner to read from ECR). Click **Next**.
5. Under **Service configuration**:
   - **Service name**: `student-complaint-service`
   - **Virtual CPU & Memory**: `1 vCPU, 2 GB` (sufficient for MVP).
   - **Port**: `8000` (FastAPI Docker port).
   - **Environment variables**: Add the following:
     - `DATABASE_URL`: `postgresql://neondb_owner:npg_7YDLsP5VWMHJ@ep-plain-credit-ahlsd0mc-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`
     - `SECRET_KEY`: `7ba72f4e0c7a52fbd1e712a768d4a9d70deef5f6a61eb3d1544a0378e9185a3c` *(Use a custom secret key in production)*
     - `ALGORITHM`: `HS256`
     - `ACCESS_TOKEN_EXPIRE_MINUTES`: `30`
     - `REFRESH_TOKEN_EXPIRE_DAYS`: `7`
6. Click **Next**, review the configuration, and click **Create & Deploy**.
7. Once created, copy the **Service ARN** and the **Default domain** URL (e.g., `https://xxxxxx.us-east-1.awsapprunner.com`).

---

## Step 3: Configure GitHub Repo Secrets
To enable automated deployments via GitHub Actions, add these secrets to your repository.

1. Go to your GitHub Repository -> **Settings** -> **Secrets and variables** -> **Actions**.
2. Click **New repository secret** and add the following:

| Secret Name | Description / Value |
| :--- | :--- |
| `AWS_ACCESS_KEY_ID` | Your AWS IAM User access key |
| `AWS_SECRET_ACCESS_KEY` | Your AWS IAM User secret access key |
| `AWS_REGION` | e.g., `us-east-1` (same region as ECR/App Runner) |
| `ECR_REPOSITORY_NAME` | e.g., `student-complaint-backend` (your repo name) |
| `AWS_APP_RUNNER_SERVICE_ARN` | The App Runner Service ARN copied in Step 2 |

Now, whenever you push code to the `main` branch, GitHub Actions will automatically run integration tests, build the Docker container, push it to ECR, and trigger an AWS App Runner deployment.

---

## Local Verification Checks

Before pushing to GitHub, you can test the production container configuration locally.

### 1. Build the Docker Image
```bash
docker build -t student-complaint-local .
```

### 2. Run the Container locally (pointing to Neon PostgreSQL DB)
```bash
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://neondb_owner:npg_7YDLsP5VWMHJ@ep-plain-credit-ahlsd0mc-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require" \
  -e SECRET_KEY="7ba72f4e0c7a52fbd1e712a768d4a9d70deef5f6a61eb3d1544a0378e9185a3c" \
  student-complaint-local
```

**What this does on boot:**
1. The container runs `entrypoint.sh`.
2. It executes `alembic upgrade head` to verify connection and migrate Neon DB schemas.
3. It seeds default departments and roles via `seed.py`.
4. It starts Gunicorn on port `8000`.

Open `http://localhost:8000/docs` in your browser to verify operations.
