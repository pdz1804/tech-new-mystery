param(
  [Parameter(Mandatory = $true)]
  [string]$Bucket,

  [string]$LockTable = "tech-news-mystery-terraform-locks",
  [string]$Region = "us-west-2"
)

$ErrorActionPreference = "Stop"

function Test-S3Bucket {
  param([string]$Name)
  $previousPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    & aws s3api head-bucket --bucket $Name *> $null
    return $LASTEXITCODE -eq 0
  } catch {
    return $false
  } finally {
    $ErrorActionPreference = $previousPreference
  }
}

function Test-DynamoTable {
  param([string]$Name)
  $previousPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    & aws dynamodb describe-table --region $Region --table-name $Name *> $null
    return $LASTEXITCODE -eq 0
  } catch {
    return $false
  } finally {
    $ErrorActionPreference = $previousPreference
  }
}

if (Test-S3Bucket -Name $Bucket) {
  Write-Host "State bucket already exists: $Bucket"
} else {
  Write-Host "Creating state bucket: $Bucket"
  aws s3api create-bucket `
    --bucket $Bucket `
    --region $Region `
    --create-bucket-configuration LocationConstraint=$Region
}

Write-Host "Applying state bucket versioning, encryption, and public access block: $Bucket"

aws s3api put-bucket-versioning `
  --bucket $Bucket `
  --versioning-configuration Status=Enabled

$encryptionConfigPath = Join-Path $env:TEMP "terraform-state-bucket-encryption-$Bucket.json"
@'
{
  "Rules": [
    {
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }
  ]
}
'@ | Set-Content -LiteralPath $encryptionConfigPath -Encoding ascii

aws s3api put-bucket-encryption `
  --bucket $Bucket `
  --server-side-encryption-configuration "file://$encryptionConfigPath"

Remove-Item -LiteralPath $encryptionConfigPath -Force

aws s3api put-public-access-block `
  --bucket $Bucket `
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

if (Test-DynamoTable -Name $LockTable) {
  Write-Host "Lock table already exists: $LockTable"
} else {
  Write-Host "Creating lock table: $LockTable"
  aws dynamodb create-table `
    --region $Region `
    --table-name $LockTable `
    --attribute-definitions AttributeName=LockID,AttributeType=S `
    --key-schema AttributeName=LockID,KeyType=HASH `
    --billing-mode PAY_PER_REQUEST

  aws dynamodb wait table-exists --region $Region --table-name $LockTable
}

Write-Host "Terraform backend bootstrap complete."
