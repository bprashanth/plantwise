#!/usr/bin/env bash

set -euo pipefail

LOCAL_IMAGE="plantwise:v0"

AWS_ACCOUNT_ID="${1:-}"
AWS_REGION="${2:-}"
ECR_REPOSITORY="${3:-plantwise}"

if [[ -z "${AWS_ACCOUNT_ID}" || -z "${AWS_REGION}" ]]; then
  echo "Usage: ./push.sh <AWS_ACCOUNT_ID> <AWS_REGION> [ECR_REPOSITORY_NAME]" >&2
  exit 1
fi

REMOTE_IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:v0"

echo "Ensuring ECR repository exists: ${ECR_REPOSITORY}"
aws ecr describe-repositories --repository-names "${ECR_REPOSITORY}" --region "${AWS_REGION}" >/dev/null 2>&1 || \
aws ecr create-repository --repository-name "${ECR_REPOSITORY}" --region "${AWS_REGION}" >/dev/null

echo "Logging into ECR: ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
aws ecr get-login-password --region "${AWS_REGION}" | \
docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "Tagging ${LOCAL_IMAGE} as ${REMOTE_IMAGE}"
docker tag "${LOCAL_IMAGE}" "${REMOTE_IMAGE}"

echo "Pushing ${REMOTE_IMAGE}"
docker push "${REMOTE_IMAGE}"

echo "Done: ${REMOTE_IMAGE}"
