param(
    [string]$ResourceGroup = "rg-jhonny-retail-poc",
    [string]$Location = "westeurope",
    [string]$PlanName = "asp-jhonny-retail-poc",
    [string]$Sku = "B1",
    [string]$BackendAppName = "",
    [string]$FrontendAppName = ""
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

function New-CleanDirectory {
    param([string]$Path)
    if (Test-Path $Path) {
        Remove-Item $Path -Recurse -Force
    }
    New-Item -ItemType Directory -Path $Path | Out-Null
}

function Copy-DirectoryContents {
    param(
        [string]$Source,
        [string]$Destination,
        [string[]]$ExcludeNames = @()
    )

    Get-ChildItem -Path $Source -Force | ForEach-Object {
        if ($ExcludeNames -contains $_.Name) {
            return
        }
        Copy-Item -Path $_.FullName -Destination (Join-Path $Destination $_.Name) -Recurse -Force
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

$accountId = az account show --query id --output tsv
$suffix = $accountId.Substring(0, 8).ToLower()
if (-not $BackendAppName) {
    $BackendAppName = "jhonny-retail-api-$suffix"
}
if (-not $FrontendAppName) {
    $FrontendAppName = "jhonny-retail-web-$suffix"
}

$openAiModel = "gpt-4o-mini"
if ($envValues.ContainsKey("OPENAI_MODEL") -and $envValues["OPENAI_MODEL"]) {
    $openAiModel = $envValues["OPENAI_MODEL"]
}

az provider register --namespace Microsoft.Web --wait
az group create --name $ResourceGroup --location $Location --output none

$planExists = $true
try {
    az appservice plan show --resource-group $ResourceGroup --name $PlanName --output none
} catch {
    $planExists = $false
}
if (-not $planExists) {
    az appservice plan create `
        --resource-group $ResourceGroup `
        --name $PlanName `
        --location $Location `
        --is-linux `
        --sku $Sku `
        --output none
}

$backendExists = $true
try {
    az webapp show --resource-group $ResourceGroup --name $BackendAppName --output none
} catch {
    $backendExists = $false
}
if (-not $backendExists) {
    az webapp create `
        --resource-group $ResourceGroup `
        --plan $PlanName `
        --name $BackendAppName `
        --runtime "PYTHON:3.12" `
        --output none
}

$backendUrl = "https://$BackendAppName.azurewebsites.net"
az webapp config appsettings set `
    --resource-group $ResourceGroup `
    --name $BackendAppName `
    --settings `
        "SCM_DO_BUILD_DURING_DEPLOYMENT=false" `
        "ENABLE_ORYX_BUILD=false" `
        "WEBSITES_PORT=8000" `
        "PYTHONPATH=/home/site/wwwroot" `
        "ODOO_URL=$($envValues['ODOO_URL'])" `
        "ODOO_DB=$($envValues['ODOO_DB'])" `
        "ODOO_USERNAME=$($envValues['ODOO_USERNAME'])" `
        "ODOO_API_KEY=$($envValues['ODOO_API_KEY'])" `
        "OPENAI_API_KEY=$($envValues['OPENAI_API_KEY'])" `
        "OPENAI_MODEL=$openAiModel" `
        "APP_AUTH_TOKEN=$($envValues['APP_AUTH_TOKEN'])" `
    --output none

az webapp config set `
    --resource-group $ResourceGroup `
    --name $BackendAppName `
    --startup-file "cd /home/site/wwwroot && python -m pip install --user -r requirements.txt && python -m uvicorn src.api:app --host 0.0.0.0 --port 8000" `
    --output none

$buildRoot = Join-Path ([System.IO.Path]::GetTempPath()) "jhonny-retail-appservice"
$backendPackage = Join-Path $buildRoot "backend"
$frontendPackage = Join-Path $buildRoot "frontend"
New-CleanDirectory -Path $buildRoot
New-Item -ItemType Directory -Path $backendPackage | Out-Null
Copy-Item -Path (Join-Path $root "requirements.txt") -Destination (Join-Path $backendPackage "requirements.txt")
Copy-Item -Path (Join-Path $root "src") -Destination (Join-Path $backendPackage "src") -Recurse
$backendZip = Join-Path $buildRoot "backend.zip"
Compress-Archive -Path (Join-Path $backendPackage "*") -DestinationPath $backendZip -Force

az webapp deployment source config-zip `
    --resource-group $ResourceGroup `
    --name $BackendAppName `
    --src $backendZip `
    --timeout 900 `
    --output none

$frontendExists = $true
try {
    az webapp show --resource-group $ResourceGroup --name $FrontendAppName --output none
} catch {
    $frontendExists = $false
}
if (-not $frontendExists) {
    az webapp create `
        --resource-group $ResourceGroup `
        --plan $PlanName `
        --name $FrontendAppName `
        --runtime "NODE:22-lts" `
        --output none
}

$frontendUrl = "https://$FrontendAppName.azurewebsites.net"
az webapp config appsettings set `
    --resource-group $ResourceGroup `
    --name $FrontendAppName `
    --settings `
        "SCM_DO_BUILD_DURING_DEPLOYMENT=true" `
        "ENABLE_ORYX_BUILD=true" `
        "WEBSITES_PORT=3000" `
        "NEXT_PUBLIC_API_BASE_URL=$backendUrl" `
    --output none

az webapp config set `
    --resource-group $ResourceGroup `
    --name $FrontendAppName `
    --startup-file "npm run start" `
    --output none

New-Item -ItemType Directory -Path $frontendPackage | Out-Null
Copy-DirectoryContents -Source (Join-Path $root "frontend") -Destination $frontendPackage -ExcludeNames @("node_modules", ".next")
$frontendZip = Join-Path $buildRoot "frontend.zip"
Compress-Archive -Path (Join-Path $frontendPackage "*") -DestinationPath $frontendZip -Force

az webapp deployment source config-zip `
    --resource-group $ResourceGroup `
    --name $FrontendAppName `
    --src $frontendZip `
    --timeout 900 `
    --output none

az webapp config appsettings set `
    --resource-group $ResourceGroup `
    --name $BackendAppName `
    --settings "APP_CORS_ORIGINS=$frontendUrl" `
    --output none

Write-Host "Backend URL: $backendUrl"
Write-Host "Frontend URL: $frontendUrl"
Write-Host "Share the frontend URL with Jhonny and send APP_AUTH_TOKEN separately."
