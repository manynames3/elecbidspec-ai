#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="${APP_NAME:-elecbidspec-ai}"
AWS_REGION="${AWS_REGION:-$(aws configure get region 2>/dev/null || true)}"
AWS_REGION="${AWS_REGION:-us-east-1}"
FRONTEND_ORIGIN="${FRONTEND_ORIGIN:-https://elecbidspec-ai.pages.dev}"
LAMBDA_PYTHON_VERSION="${LAMBDA_PYTHON_VERSION:-3.12}"
BOOTSTRAP_DATABASE_ON_STARTUP="${BOOTSTRAP_DATABASE_ON_STARTUP:-true}"
RUN_MIGRATIONS_ON_STARTUP="${RUN_MIGRATIONS_ON_STARTUP:-true}"
SEED_DATABASE_ON_STARTUP="${SEED_DATABASE_ON_STARTUP:-true}"
BEDROCK_PROPOSALS_ENABLED="${BEDROCK_PROPOSALS_ENABLED:-false}"
BEDROCK_MODEL_ID="${BEDROCK_MODEL_ID:-anthropic.claude-3-haiku-20240307-v1:0}"
SAM_GOV_API_KEY="${SAM_GOV_API_KEY:-}"

: "${DATABASE_URL:?Set DATABASE_URL to the Neon pooled Postgres connection string before deploying.}"

BUILD_ROOT="${ROOT_DIR}/.build"
BUILD_DIR="${BUILD_ROOT}/lambda"
ZIP_PATH="${BUILD_ROOT}/${APP_NAME}-backend.zip"
TF_DIR="${ROOT_DIR}/infra/aws-lambda/terraform"
LAMBDA_REQUIREMENTS_FILE="${LAMBDA_REQUIREMENTS_FILE:-${ROOT_DIR}/backend/requirements-lambda.txt}"

if ! command -v terraform >/dev/null 2>&1; then
  echo "terraform is required. Install Terraform, then rerun this script." >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required for reproducible Lambda dependency packaging. Install uv, then rerun this script." >&2
  exit 1
fi

rm -rf "$BUILD_DIR" "$ZIP_PATH"
mkdir -p "$BUILD_DIR"

uv pip install \
  --python-version "$LAMBDA_PYTHON_VERSION" \
  --python-platform x86_64-manylinux2014 \
  --only-binary=:all: \
  --target "$BUILD_DIR" \
  -r "$LAMBDA_REQUIREMENTS_FILE"

rsync -a --exclude "__pycache__" "${ROOT_DIR}/backend/app" "$BUILD_DIR/"
rsync -a --exclude "__pycache__" "${ROOT_DIR}/backend/alembic" "$BUILD_DIR/"
cp "${ROOT_DIR}/backend/alembic.ini" "$BUILD_DIR/"
find "$BUILD_DIR" -name "*.pyc" -delete
find "$BUILD_DIR" -name "__pycache__" -type d -prune -exec rm -rf {} +

(cd "$BUILD_DIR" && zip -qr "$ZIP_PATH" .)

export TF_VAR_app_name="$APP_NAME"
export TF_VAR_aws_region="$AWS_REGION"
export TF_VAR_frontend_origin="$FRONTEND_ORIGIN"
export TF_VAR_lambda_zip_path="$ZIP_PATH"
export TF_VAR_database_url="$DATABASE_URL"
export TF_VAR_bootstrap_database_on_startup="$BOOTSTRAP_DATABASE_ON_STARTUP"
export TF_VAR_run_migrations_on_startup="$RUN_MIGRATIONS_ON_STARTUP"
export TF_VAR_seed_database_on_startup="$SEED_DATABASE_ON_STARTUP"
export TF_VAR_bedrock_proposals_enabled="$BEDROCK_PROPOSALS_ENABLED"
export TF_VAR_bedrock_model_id="$BEDROCK_MODEL_ID"
export TF_VAR_sam_gov_api_key="$SAM_GOV_API_KEY"

terraform -chdir="$TF_DIR" init
terraform -chdir="$TF_DIR" apply -auto-approve
terraform -chdir="$TF_DIR" output
