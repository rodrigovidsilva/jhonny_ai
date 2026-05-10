param(
    [string]$ResourceGroup = "rg-jhonny-retail-poc",
    [string]$Location = "westeurope",
    [string]$AcrName = "acrjhonnyretailpoc",
    [string]$EnvironmentName = "cae-jhonny-retail-poc",
    [string]$BackendAppName = "jhonny-retail-api",
    [string]$FrontendAppName = "jhonny-retail-web",
    [string]$ImageTag = "latest"
)

$ErrorActionPreference = "Stop"

$azCommand = Get-Command az -ErrorAction SilentlyContinue
if ($azCommand) {
    $script:AzExecutable = $azCommand.Source
} else {
    $script:AzExecutable = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
    if (-not (Test-Path $script:AzExecutable)) {
        throw "Azure CLI was not found. Install it from https://learn.microsoft.com/cli/azure/install-azure-cli-windows"
    }
}

function az {
    & $script:AzExecutable @args
    if ($LASTEXITCODE -ne 0) {
        throw "Azure CLI command failed: az $($args -join ' ')"
    }
}

function Read-DotEnv {
    param([string]$Path)

    $values = @{}
    if (-not (Test-Path $Path)) {
        throw "Missing .env file at $Path"
    }

    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            return
        }
        $parts = $line.Split("=", 2)
        $key = $parts[0].Trim()
        $value = $parts[1].Trim().Trim('"').Trim("'")
        $values[$key] = $value
    }
    return $values
}

function Require-Env {
    param(
        [hashtable]$Env,
        [string[]]$Names
    )

    $missing = @()
    foreach ($name in $Names) {
        if (-not $Env.ContainsKey($name) -or -not $Env[$name] -or $Env[$name].StartsWith("replace-with")) {
            $missing += $name
        }
    }
    if ($missing.Count -gt 0) {
        throw "Missing or placeholder values in .env: $($missing -join ', ')"
    }
}

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envValues = Read-DotEnv -Path (Join-Path $root ".env")
Require-Env -Env $envValues -Names @(
    "ODOO_URL",
    "ODOO_DB",
    "ODOO_USERNAME",
    "ODOO_API_KEY",
    "OPENAI_API_KEY",
    "APP_AUTH_TOKEN"
)

az account show --output none
az extension add --name containerapp --upgrade --output none
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait
az provider register --namespace Microsoft.ContainerRegistry --wait

az group create `
    --name $ResourceGroup `
    --location $Location `
    --output none

az acr create `
    --resource-group $ResourceGroup `
    --name $AcrName `
    --sku Basic `
    --admin-enabled true `
    --output none

$acrLoginServer = az acr show `
    --resource-group $ResourceGroup `
    --name $AcrName `
    --query loginServer `
    --output tsv
$acrUsername = az acr credential show `
    --resource-group $ResourceGroup `
    --name $AcrName `
    --query username `
    --output tsv
$acrPassword = az acr credential show `
    --resource-group $ResourceGroup `
    --name $AcrName `
    --query "passwords[0].value" `
    --output tsv

az containerapp env create `
    --resource-group $ResourceGroup `
    --name $EnvironmentName `
    --location $Location `
    --output none

$backendImage = "$acrLoginServer/$BackendAppName`:$ImageTag"
$frontendImage = "$acrLoginServer/$FrontendAppName`:$ImageTag"
$backendBuildContext = Join-Path ([System.IO.Path]::GetTempPath()) "jhonny-retail-api-build"
if (Test-Path $backendBuildContext) {
    Remove-Item $backendBuildContext -Recurse -Force
}
New-Item -ItemType Directory -Path $backendBuildContext | Out-Null
Copy-Item -Path (Join-Path $root "Dockerfile") -Destination (Join-Path $backendBuildContext "Dockerfile")
Copy-Item -Path (Join-Path $root "requirements.txt") -Destination (Join-Path $backendBuildContext "requirements.txt")
Copy-Item -Path (Join-Path $root "src") -Destination (Join-Path $backendBuildContext "src") -Recurse
Copy-Item -Path (Join-Path $root "scripts") -Destination (Join-Path $backendBuildContext "scripts") -Recurse
$openAiModel = "gpt-4o-mini"
if ($envValues.ContainsKey("OPENAI_MODEL") -and $envValues["OPENAI_MODEL"]) {
    $openAiModel = $envValues["OPENAI_MODEL"]
}
$whatsappAllowedNumbers = ""
if ($envValues.ContainsKey("WHATSAPP_ALLOWED_NUMBERS")) {
    $whatsappAllowedNumbers = $envValues["WHATSAPP_ALLOWED_NUMBERS"]
}
$whatsappRateLimit = "20"
if ($envValues.ContainsKey("WHATSAPP_RATE_LIMIT_PER_MINUTE") -and $envValues["WHATSAPP_RATE_LIMIT_PER_MINUTE"]) {
    $whatsappRateLimit = $envValues["WHATSAPP_RATE_LIMIT_PER_MINUTE"]
}

az acr build `
    --registry $AcrName `
    --image "$BackendAppName`:$ImageTag" `
    --file (Join-Path $backendBuildContext "Dockerfile") `
    $backendBuildContext

az containerapp create `
    --resource-group $ResourceGroup `
    --name $BackendAppName `
    --environment $EnvironmentName `
    --image $backendImage `
    --registry-server $acrLoginServer `
    --registry-username $acrUsername `
    --registry-password $acrPassword `
    --target-port 8000 `
    --ingress external `
    --secrets `
        "odoo-url=$($envValues['ODOO_URL'])" `
        "odoo-db=$($envValues['ODOO_DB'])" `
        "odoo-username=$($envValues['ODOO_USERNAME'])" `
        "odoo-api-key=$($envValues['ODOO_API_KEY'])" `
        "openai-api-key=$($envValues['OPENAI_API_KEY'])" `
        "app-auth-token=$($envValues['APP_AUTH_TOKEN'])" `
    --env-vars `
        "ODOO_URL=secretref:odoo-url" `
        "ODOO_DB=secretref:odoo-db" `
        "ODOO_USERNAME=secretref:odoo-username" `
        "ODOO_API_KEY=secretref:odoo-api-key" `
        "OPENAI_API_KEY=secretref:openai-api-key" `
        "OPENAI_MODEL=$openAiModel" `
        "APP_AUTH_TOKEN=secretref:app-auth-token" `
        "WHATSAPP_ALLOWED_NUMBERS=$whatsappAllowedNumbers" `
        "WHATSAPP_RATE_LIMIT_PER_MINUTE=$whatsappRateLimit" `
    --output none

$backendUrl = "https://" + (az containerapp show `
    --resource-group $ResourceGroup `
    --name $BackendAppName `
    --query properties.configuration.ingress.fqdn `
    --output tsv)

az acr build `
    --registry $AcrName `
    --image "$FrontendAppName`:$ImageTag" `
    --file (Join-Path $root "frontend/Dockerfile") `
    --build-arg "NEXT_PUBLIC_API_BASE_URL=$backendUrl" `
    (Join-Path $root "frontend")

az containerapp create `
    --resource-group $ResourceGroup `
    --name $FrontendAppName `
    --environment $EnvironmentName `
    --image $frontendImage `
    --registry-server $acrLoginServer `
    --registry-username $acrUsername `
    --registry-password $acrPassword `
    --target-port 3000 `
    --ingress external `
    --env-vars "NEXT_PUBLIC_API_BASE_URL=$backendUrl" `
    --output none

$frontendUrl = "https://" + (az containerapp show `
    --resource-group $ResourceGroup `
    --name $FrontendAppName `
    --query properties.configuration.ingress.fqdn `
    --output tsv)

az containerapp update `
    --resource-group $ResourceGroup `
    --name $BackendAppName `
    --set-env-vars "APP_CORS_ORIGINS=$frontendUrl" `
    --output none

Write-Host "Backend URL: $backendUrl"
Write-Host "Frontend URL: $frontendUrl"
Write-Host "Share the frontend URL with Jhonny and send APP_AUTH_TOKEN separately."
