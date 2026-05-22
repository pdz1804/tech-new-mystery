param(
  [Parameter(Mandatory = $true)]
  [string]$Bucket,

  [string]$LockTable = "tech-news-mystery-terraform-locks",
  [string]$Region = "us-west-2",
  [string]$StateKey = "tech-news-mystery/prod/terraform.tfstate"
)

$ErrorActionPreference = "Stop"

terraform init -reconfigure `
  -backend-config="bucket=$Bucket" `
  -backend-config="key=$StateKey" `
  -backend-config="region=$Region" `
  -backend-config="dynamodb_table=$LockTable" `
  -backend-config="encrypt=true"
