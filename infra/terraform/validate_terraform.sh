#!/bin/bash
# Terraform syntax validation script for TASK-CHT-003

set -e

echo "================================"
echo "Terraform Syntax Validation"
echo "================================"
echo ""

cd "$(dirname "$0")"

echo "Validating iam.tf..."
if terraform validate iam.tf >/dev/null 2>&1; then
    echo "✓ iam.tf valid"
else
    echo "✗ iam.tf invalid"
    terraform validate iam.tf
    exit 1
fi

echo "Validating network.tf..."
if terraform validate network.tf >/dev/null 2>&1; then
    echo "✓ network.tf valid"
else
    echo "✗ network.tf invalid"
    terraform validate network.tf
    exit 1
fi

echo "Validating ecs.tf..."
if terraform validate ecs.tf >/dev/null 2>&1; then
    echo "✓ ecs.tf valid"
else
    echo "✗ ecs.tf invalid"
    terraform validate ecs.tf
    exit 1
fi

echo ""
echo "✓ All Terraform files are syntactically valid"
