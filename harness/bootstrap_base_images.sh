#!/usr/bin/env bash

set -euo pipefail

for command_name in aws docker; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "missing required command: $command_name" >&2
        exit 1
    fi
done

XAI_ECR_REGION="${XAI_ECR_REGION:-us-east-1}"
XAI_ECR_REGISTRY="${XAI_ECR_REGISTRY:-237343249281.dkr.ecr.us-east-1.amazonaws.com}"

aws_command=(aws)
if [ -n "${XAI_AWS_PROFILE:-}" ]; then
    aws_command+=(--profile "$XAI_AWS_PROFILE")
fi

echo "Logging in to $XAI_ECR_REGISTRY in $XAI_ECR_REGION"
"${aws_command[@]}" ecr get-login-password --region "$XAI_ECR_REGION" \
    | docker login --username AWS --password-stdin "$XAI_ECR_REGISTRY"

# local name | private ECR repository | immutable runnable-image digest
images=(
    "loangenus-repo|rl-images/loangenus-repo|sha256:da41baf58bb7142349bd8c76a5998d04b5f9dcb3453fb0b78f2da01238f99481"
    "fiu-repo|rl-images/fiu-repo|sha256:fb48c7d461041e0420e044b36dcfc772ee2fb54c3c335de68e6180e084e80672"
    "txenrich-repo|rl-images/txenrich-repo|sha256:8c2983a115729f662626e804854ccaf7f7d06e59b0372c4bd721e7d63c4f3e01"
    "bank-statement-parser-repo|rl-images/bank-statement-parser-repo|sha256:f01f1a1ccb0e1e13f329c88bbb4045c9dc576b97a0871e14fbcf281cc8e07242"
    "enterprise-backend-eng504-billing-base|rl-images/enterprise-backend-eng504-billing-base|sha256:3ac4857029083506c3945264a9f5e877cec7b2d9833fca573e714b4b7c83db60"
    "enterprise-backend-eng504-identity-base|rl-images/enterprise-backend-eng504-identity-base|sha256:9cba1b8f5f99f48fa43c56a8b7d058bbcea91a3b1c58808cb439c95817de4fb7"
    "enterprise-backend-eng830-base|rl-images/enterprise-backend-eng830-base|sha256:a5c9c0cc3b13a68e2bfb4f35f31e9fe3ffea6e87ec9b7865b805ae1febf839ca"
    "enterprise-backend-eng1167-base|rl-images/enterprise-backend-eng1167-base|sha256:dfd162b2f78a8db2ebbe7b92ee430578a178a6c32c2277c40624880404288ca2"
    "enterprise-backend-eng411-base|rl-images/enterprise-backend-eng411-base|sha256:cc22566e17bc39efc310b7d3141633c81d61b1c6fcf8eed49ebaa87771f6a20d"
    "enterprise-state-machine-email2197-base|rl-images/enterprise-state-machine-email2197-base|sha256:ce3cec478d144ff3750c5c8e69101f76f760d8e3face8af74c2a984d78f5f784"
    "enterprise-bank-parser-base|rl-images/enterprise-bank-parser-base|sha256:c077a0bffbc77f41447ba66d14d79436b3fcd3bdf42d9a21cd8567ab5b23ac3c"
    "enterprise-google-cloud-storage-base|rl-images/enterprise-google-cloud-storage-base|sha256:c08265e733f2d6490faf2700854c6c7951c47d6da8bad2afa67065cb0d358c34"
)

for item in "${images[@]}"; do
    IFS='|' read -r local_name repository digest <<<"$item"
    remote_reference="$XAI_ECR_REGISTRY/$repository@$digest"
    echo "Pulling $local_name from $repository@$digest"
    docker pull --platform linux/amd64 "$remote_reference"
    docker tag "$remote_reference" "$local_name:v1"

    architecture=$(docker image inspect "$local_name:v1" --format '{{.Architecture}}')
    if [ "$architecture" != "amd64" ]; then
        echo "$local_name:v1 has architecture $architecture, expected amd64" >&2
        exit 1
    fi
done

echo
echo "Installed 12 sealed linux/amd64 base images:"
for item in "${images[@]}"; do
    IFS='|' read -r local_name _ _ <<<"$item"
    architecture=$(docker image inspect "$local_name:v1" --format '{{.Architecture}}')
    image_id=$(docker image inspect "$local_name:v1" --format '{{.Id}}')
    printf '  %s:v1  %s  %s\n' "$local_name" "$architecture" "$image_id"
done
