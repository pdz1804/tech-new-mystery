#!/usr/bin/env bash
set -euo pipefail

terraform fmt -recursive
terraform init -backend=false
terraform validate
