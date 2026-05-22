param(
  [string]$EnvFile = "..\..\backend\.env",
  [string]$Region = "us-west-2",
  [string]$SecretId = ""
)

$ErrorActionPreference = "Stop"

if (!(Test-Path -LiteralPath $EnvFile)) {
  throw "Env file not found: $EnvFile"
}

if ($SecretId -eq "") {
  $SecretId = terraform output -raw app_secret_arn
}

$envValues = @{}

Get-Content -LiteralPath $EnvFile | ForEach-Object {
  $line = $_.Trim()
  if ($line -eq "" -or $line.StartsWith("#")) {
    return
  }

  $separatorIndex = $line.IndexOf("=")
  if ($separatorIndex -lt 1) {
    return
  }

  $key = $line.Substring(0, $separatorIndex).Trim()
  $value = $line.Substring($separatorIndex + 1).Trim()
  $envValues[$key] = $value
}

function Get-EnvValue {
  param([string]$Key)
  if ($envValues.ContainsKey($Key)) {
    return $envValues[$Key]
  }
  return ""
}

$secretPayload = [ordered]@{
  SECRET_KEY        = Get-EnvValue "SECRET_KEY"
  JWT_SECRET_KEY    = Get-EnvValue "JWT_SECRET_KEY"
  OPENAI_API_KEY    = Get-EnvValue "OPENAI_API_KEY"
  TAVILY_API_KEY    = Get-EnvValue "TAVILY_API_KEY"
  NEWSAPI_KEY       = Get-EnvValue "NEWSAPI_KEY"
  QDRANT_URL        = Get-EnvValue "QDRANT_URL"
  QDRANT_API_KEY    = Get-EnvValue "QDRANT_API_KEY"
  GEMINI_API_KEY    = Get-EnvValue "GEMINI_API_KEY"
  ANTHROPIC_API_KEY = Get-EnvValue "ANTHROPIC_API_KEY"
}

$tempPath = Join-Path $env:TEMP "tech-news-app-secret.json"
$secretPayload | ConvertTo-Json -Compress | Set-Content -LiteralPath $tempPath -Encoding ascii

aws secretsmanager put-secret-value `
  --region $Region `
  --secret-id $SecretId `
  --secret-string "file://$tempPath"

Remove-Item -LiteralPath $tempPath -Force
Write-Host "Updated app secret in Secrets Manager: $SecretId"
