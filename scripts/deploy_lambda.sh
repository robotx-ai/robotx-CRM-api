#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:?AWS_REGION is required}"
: "${ECR_REPOSITORY:?ECR_REPOSITORY is required}"
: "${LAMBDA_FUNCTION_NAME:?LAMBDA_FUNCTION_NAME is required}"

ACCOUNT_ID="${ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
IMAGE_TAG="${IMAGE_TAG:-${GITHUB_SHA:-$(git rev-parse --short=12 HEAD)}}"
IMAGE_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}"
DEPLOY_NOTE="main:${IMAGE_TAG}"

echo "Using image URI: ${IMAGE_URI}"

aws ecr describe-repositories --repository-names "${ECR_REPOSITORY}" --region "${AWS_REGION}" >/dev/null 2>&1 \
  || aws ecr create-repository --repository-name "${ECR_REPOSITORY}" --region "${AWS_REGION}" >/dev/null

aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com" >/dev/null

docker buildx build \
  --platform linux/amd64 \
  --provenance=false \
  --sbom=false \
  -f Dockerfile.lambda \
  -t "${IMAGE_URI}" \
  --push .

aws lambda update-function-code \
  --function-name "${LAMBDA_FUNCTION_NAME}" \
  --image-uri "${IMAGE_URI}" \
  --region "${AWS_REGION}" >/dev/null

aws lambda wait function-updated \
  --function-name "${LAMBDA_FUNCTION_NAME}" \
  --region "${AWS_REGION}"

aws lambda update-function-configuration \
  --function-name "${LAMBDA_FUNCTION_NAME}" \
  --description "${DEPLOY_NOTE}" \
  --region "${AWS_REGION}" >/dev/null

aws lambda wait function-updated \
  --function-name "${LAMBDA_FUNCTION_NAME}" \
  --region "${AWS_REGION}"

PUBLISHED_VERSION="$(
  aws lambda publish-version \
    --function-name "${LAMBDA_FUNCTION_NAME}" \
    --description "${DEPLOY_NOTE}" \
    --region "${AWS_REGION}" \
    --query 'Version' \
    --output text
)"

echo "Published Lambda version: ${PUBLISHED_VERSION}"
echo "Published image URI: ${IMAGE_URI}"

