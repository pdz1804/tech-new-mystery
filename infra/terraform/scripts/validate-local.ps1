$ErrorActionPreference = "Stop"

terraform fmt -recursive
terraform init -backend=false
terraform validate
