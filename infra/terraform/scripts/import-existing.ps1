param(
  [string]$Region = "us-west-2",
  [string]$TablePrefix = "tech-news-",
  [string]$S3Bucket = "tech-news-articles-381492273521"
)

$ErrorActionPreference = "Stop"

$tables = @(
  @{ Name = "users"; Resource = "aws_dynamodb_table.users[0]" },
  @{ Name = "articles"; Resource = "aws_dynamodb_table.articles[0]" },
  @{ Name = "comments"; Resource = "aws_dynamodb_table.comments[0]" },
  @{ Name = "user_saves"; Resource = "aws_dynamodb_table.user_saves[0]" },
  @{ Name = "user_likes"; Resource = "aws_dynamodb_table.user_likes[0]" },
  @{ Name = "user_preferences"; Resource = "aws_dynamodb_table.user_preferences[0]" },
  @{ Name = "news_sources"; Resource = "aws_dynamodb_table.news_sources[0]" },
  @{ Name = "pending-searches"; Resource = "aws_dynamodb_table.pending_searches[0]" },
  @{ Name = "trending_articles"; Resource = "aws_dynamodb_table.trending_articles[0]" },
  @{ Name = "submissions"; Resource = "aws_dynamodb_table.submissions[0]" }
)

function Test-TerraformStateResource {
  param([string]$Resource)
  $previousPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    & terraform state show $Resource *> $null
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

foreach ($table in $tables) {
  $fullName = "$TablePrefix$($table.Name)"
  if (Test-DynamoTable -Name $fullName) {
    if (Test-TerraformStateResource -Resource $table.Resource) {
      Write-Host "Already in Terraform state: $fullName"
    } else {
      Write-Host "Importing existing DynamoDB table: $fullName"
      terraform import $table.Resource $fullName
    }
  } else {
    Write-Host "DynamoDB table not found, Terraform will create: $fullName"
  }
}

if ($S3Bucket -ne "") {
  if (Test-S3Bucket -Name $S3Bucket) {
    if (Test-TerraformStateResource -Resource 'aws_s3_bucket.articles[0]') {
      Write-Host "Already in Terraform state: $S3Bucket"
    } else {
      Write-Host "Importing existing S3 bucket: $S3Bucket"
      terraform import 'aws_s3_bucket.articles[0]' $S3Bucket
    }
  } else {
    Write-Host "S3 bucket not found, Terraform will create: $S3Bucket"
  }
}
