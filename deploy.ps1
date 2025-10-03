# Fantasy Sports Helper - Azure Deployment Script (PowerShell)
# This script automates the deployment of the Fantasy Sports Helper to Azure

param(
    [string]$SubscriptionId = "",
    [string]$ResourceGroupName = "fantasyhelperrg",
    [string]$Location = "West US",
    [string]$FunctionAppName = "fantasyhelperfunc",
    [string]$StaticWebAppName = "fantasyhelperweb",
    [string]$CosmosAccountName = "fantasyhelpercosmos",
    [string]$StorageAccountName = "fantasyhelperstorage",
    [string]$GitHubRepo = "https://github.com/yourusername/FantasySportsHelper",
    [string]$GitHubBranch = "main"
)

Write-Host "Fantasy Sports Helper - Azure Deployment" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green

# Function to check if a command succeeded
function Test-CommandSuccess {
    param([string]$Command, [string]$ErrorMessage)
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: $ErrorMessage" -ForegroundColor Red
        Write-Host "Command failed: $Command" -ForegroundColor Yellow
        $continue = Read-Host "Do you want to continue anyway? (y/n)"
        if ($continue -ne "y" -and $continue -ne "Y") {
            exit 1
        }
    }
}

# Function to validate Azure resource exists
function Test-AzureResource {
    param([string]$ResourceType, [string]$ResourceName, [string]$ResourceGroup)
    try {
        $resource = az resource show --name $ResourceName --resource-group $ResourceGroup --resource-type $ResourceType --output tsv 2>$null
        if ($LASTEXITCODE -eq 0 -and $resource) {
            Write-Host "✓ $ResourceType '$ResourceName' exists" -ForegroundColor Green
            return $true
        } else {
            Write-Host "✗ $ResourceType '$ResourceName' not found" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "✗ Error checking $ResourceType '$ResourceName'" -ForegroundColor Red
        return $false
    }
}

# Check if Azure CLI is installed
Write-Host "Checking Azure CLI installation..." -ForegroundColor Yellow
try {
    $azVersion = az version --output tsv 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Azure CLI not found"
    }
    Write-Host "✓ Azure CLI version: $azVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Error: Azure CLI is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Azure CLI from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli" -ForegroundColor Yellow
    exit 1
}

# Check if user is logged in
Write-Host "Checking Azure authentication..." -ForegroundColor Yellow
try {
    $account = az account show --output tsv 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Not logged in"
    }
    Write-Host "✓ Logged in as: $account" -ForegroundColor Green
} catch {
    Write-Host "✗ Not logged in to Azure CLI" -ForegroundColor Red
    Write-Host "Please log in to Azure CLI first:" -ForegroundColor Yellow
    Write-Host "az login" -ForegroundColor White
    $login = Read-Host "Press Enter after logging in, or type 'exit' to quit"
    if ($login -eq "exit") {
        exit 1
    }
    
    # Re-check login
    $account = az account show --output tsv 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Still not logged in. Exiting." -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Now logged in as: $account" -ForegroundColor Green
}

# Set subscription if provided
if ($SubscriptionId) {
    Write-Host "Setting subscription to: $SubscriptionId" -ForegroundColor Yellow
    az account set --subscription $SubscriptionId
    Test-CommandSuccess "az account set --subscription $SubscriptionId" "Failed to set subscription"
}

# Check if resource group already exists
Write-Host "Checking if resource group '$ResourceGroupName' already exists..." -ForegroundColor Yellow
$rgExists = Test-AzureResource "Microsoft.Resources/resourceGroups" $ResourceGroupName $ResourceGroupName
if ($rgExists) {
    $overwrite = Read-Host "Resource group already exists. Do you want to continue and update existing resources? (y/n)"
    if ($overwrite -ne "y" -and $overwrite -ne "Y") {
        Write-Host "Exiting. Please choose a different resource group name." -ForegroundColor Yellow
        exit 1
    }
}

# Check if resource names are available
Write-Host "Checking resource name availability..." -ForegroundColor Yellow
Write-Host "This helps avoid conflicts with existing Azure resources." -ForegroundColor White

# Check Static Web App name availability
$swaExists = $false
az staticwebapp show --name $StaticWebAppName --resource-group $ResourceGroupName --output tsv 2>$null
if ($LASTEXITCODE -eq 0) {
    $swaExists = $true
    Write-Host "⚠ Static Web App name '$StaticWebAppName' may already exist in this resource group." -ForegroundColor Yellow
    $changeSwa = Read-Host "Do you want to use a different Static Web App name? (y/n)"
    if ($changeSwa -eq "y" -or $changeSwa -eq "Y") {
        $StaticWebAppName = Read-Host "Enter a new Static Web App name"
    }
}

# Check Function App name availability
$funcExists = $false
az functionapp show --name $FunctionAppName --resource-group $ResourceGroupName --output tsv 2>$null
if ($LASTEXITCODE -eq 0) {
    $funcExists = $true
    Write-Host "⚠ Function App name '$FunctionAppName' may already exist in this resource group." -ForegroundColor Yellow
    $changeFunc = Read-Host "Do you want to use a different Function App name? (y/n)"
    if ($changeFunc -eq "y" -or $changeFunc -eq "Y") {
        $FunctionAppName = Read-Host "Enter a new Function App name"
    }
}

# Check Cosmos DB name availability
$cosmosExists = $false
az cosmosdb show --name $CosmosAccountName --resource-group $ResourceGroupName --output tsv 2>$null
if ($LASTEXITCODE -eq 0) {
    $cosmosExists = $true
    Write-Host "⚠ Cosmos DB name '$CosmosAccountName' may already exist in this resource group." -ForegroundColor Yellow
    $changeCosmos = Read-Host "Do you want to use a different Cosmos DB name? (y/n)"
    if ($changeCosmos -eq "y" -or $changeCosmos -eq "Y") {
        $CosmosAccountName = Read-Host "Enter a new Cosmos DB name"
    }
}

# Check Storage Account name availability
$storageExists = $false
az storage account show --name $StorageAccountName --resource-group $ResourceGroupName --output tsv 2>$null
if ($LASTEXITCODE -eq 0) {
    $storageExists = $true
    Write-Host "⚠ Storage Account name '$StorageAccountName' may already exist in this resource group." -ForegroundColor Yellow
    $changeStorage = Read-Host "Do you want to use a different Storage Account name? (y/n)"
    if ($changeStorage -eq "y" -or $changeStorage -eq "Y") {
        $StorageAccountName = Read-Host "Enter a new Storage Account name"
    }
}

Write-Host "Using the following resource names:" -ForegroundColor Green
Write-Host "  Static Web App: $StaticWebAppName" -ForegroundColor White
Write-Host "  Function App: $FunctionAppName" -ForegroundColor White
Write-Host "  Cosmos DB: $CosmosAccountName" -ForegroundColor White
Write-Host "  Storage Account: $StorageAccountName" -ForegroundColor White

# Show summary of existing resources
$existingResources = @()
if ($swaExists) { $existingResources += "Static Web App" }
if ($funcExists) { $existingResources += "Function App" }
if ($cosmosExists) { $existingResources += "Cosmos DB" }
if ($storageExists) { $existingResources += "Storage Account" }

if ($existingResources.Count -gt 0) {
    Write-Host "⚠ The following resources may already exist: $($existingResources -join ', ')" -ForegroundColor Yellow
    Write-Host "  This could cause conflicts during deployment." -ForegroundColor White
} else {
    Write-Host "✓ All resource names appear to be available." -ForegroundColor Green
}
Write-Host ""

# Create resource group
Write-Host "Creating resource group: $ResourceGroupName" -ForegroundColor Yellow
az group create --name $ResourceGroupName --location $Location
Test-CommandSuccess "az group create --name $ResourceGroupName --location $Location" "Failed to create resource group"

# Verify resource group was created
if (-not (Test-AzureResource "Microsoft.Resources/resourceGroups" $ResourceGroupName $ResourceGroupName)) {
    Write-Host "✗ Resource group creation failed. Exiting." -ForegroundColor Red
    exit 1
}

# Create Cosmos DB account
Write-Host "Creating Cosmos DB account: $CosmosAccountName" -ForegroundColor Yellow
az cosmosdb create --name $CosmosAccountName --resource-group $ResourceGroupName --locations regionName=$Location
Test-CommandSuccess "az cosmosdb create --name $CosmosAccountName --resource-group $ResourceGroupName --locations regionName=$Location" "Failed to create Cosmos DB account"

# Verify Cosmos DB was created
if (-not (Test-AzureResource "Microsoft.DocumentDB/databaseAccounts" $CosmosAccountName $ResourceGroupName)) {
    Write-Host "✗ Cosmos DB creation failed. Exiting." -ForegroundColor Red
    exit 1
}

# Create Cosmos DB database and containers
Write-Host "Creating Cosmos DB database and containers" -ForegroundColor Yellow
$cosmosKey = az cosmosdb keys list --name $CosmosAccountName --resource-group $ResourceGroupName --type keys --query primaryMasterKey --output tsv
if (-not $cosmosKey) {
    Write-Host "✗ Failed to retrieve Cosmos DB key. Exiting." -ForegroundColor Red
    exit 1
}
$cosmosEndpoint = "https://$CosmosAccountName.documents.azure.com:443/"

# Create database
az cosmosdb sql database create --account-name $CosmosAccountName --resource-group $ResourceGroupName --name fantasyhelper
Test-CommandSuccess "az cosmosdb sql database create --account-name $CosmosAccountName --resource-group $ResourceGroupName --name fantasyhelper" "Failed to create database"

# Create containers
az cosmosdb sql container create --account-name $CosmosAccountName --resource-group $ResourceGroupName --database-name fantasyhelper --name leagues --partition-key-path "/id"
Test-CommandSuccess "az cosmosdb sql container create --account-name $CosmosAccountName --resource-group $ResourceGroupName --database-name fantasyhelper --name leagues --partition-key-path '/id'" "Failed to create leagues container"

az cosmosdb sql container create --account-name $CosmosAccountName --resource-group $ResourceGroupName --database-name fantasyhelper --name managers --partition-key-path "/id"
Test-CommandSuccess "az cosmosdb sql container create --account-name $CosmosAccountName --resource-group $ResourceGroupName --database-name fantasyhelper --name managers --partition-key-path '/id'" "Failed to create managers container"

az cosmosdb sql container create --account-name $CosmosAccountName --resource-group $ResourceGroupName --database-name fantasyhelper --name schedules --partition-key-path "/id"
Test-CommandSuccess "az cosmosdb sql container create --account-name $CosmosAccountName --resource-group $ResourceGroupName --database-name fantasyhelper --name schedules --partition-key-path '/id'" "Failed to create schedules container"

az cosmosdb sql container create --account-name $CosmosAccountName --resource-group $ResourceGroupName --database-name fantasyhelper --name tokens --partition-key-path "/id"
Test-CommandSuccess "az cosmosdb sql container create --account-name $CosmosAccountName --resource-group $ResourceGroupName --database-name fantasyhelper --name tokens --partition-key-path '/id'" "Failed to create tokens container"

# Create storage account
Write-Host "Creating storage account: $StorageAccountName" -ForegroundColor Yellow
az storage account create --name $StorageAccountName --resource-group $ResourceGroupName --location $Location --sku Standard_LRS
Test-CommandSuccess "az storage account create --name $StorageAccountName --resource-group $ResourceGroupName --location $Location --sku Standard_LRS" "Failed to create storage account"

# Verify storage account was created
if (-not (Test-AzureResource "Microsoft.Storage/storageAccounts" $StorageAccountName $ResourceGroupName)) {
    Write-Host "✗ Storage account creation failed. Exiting." -ForegroundColor Red
    exit 1
}

# Create Function App
Write-Host "Creating Function App: $FunctionAppName" -ForegroundColor Yellow
az functionapp create --name $FunctionAppName --resource-group $ResourceGroupName --storage-account $StorageAccountName --runtime python --runtime-version 3.9 --consumption-plan-location $Location
Test-CommandSuccess "az functionapp create --name $FunctionAppName --resource-group $ResourceGroupName --storage-account $StorageAccountName --runtime python --runtime-version 3.9 --consumption-plan-location $Location" "Failed to create Function App"

# Verify Function App was created
if (-not (Test-AzureResource "Microsoft.Web/sites" $FunctionAppName $ResourceGroupName)) {
    Write-Host "✗ Function App creation failed. Exiting." -ForegroundColor Red
    exit 1
}

# Configure Function App settings
Write-Host "Configuring Function App settings" -ForegroundColor Yellow
az functionapp config appsettings set --name $FunctionAppName --resource-group $ResourceGroupName --settings COSMOS_ENDPOINT=$cosmosEndpoint COSMOS_KEY=$cosmosKey
Test-CommandSuccess "az functionapp config appsettings set --name $FunctionAppName --resource-group $ResourceGroupName --settings COSMOS_ENDPOINT=$cosmosEndpoint COSMOS_KEY=$cosmosKey" "Failed to configure Function App settings"

# Enable Managed Identity
Write-Host "Enabling Managed Identity for Function App" -ForegroundColor Yellow
az functionapp identity assign --name $FunctionAppName --resource-group $ResourceGroupName
Test-CommandSuccess "az functionapp identity assign --name $FunctionAppName --resource-group $ResourceGroupName" "Failed to enable Managed Identity"

# Get Function App identity
$functionIdentity = az functionapp identity show --name $FunctionAppName --resource-group $ResourceGroupName --query principalId --output tsv
if (-not $functionIdentity) {
    Write-Host "✗ Failed to get Function App identity. Exiting." -ForegroundColor Red
    exit 1
}

# Assign Cosmos DB permissions
Write-Host "Assigning Cosmos DB permissions to Function App" -ForegroundColor Yellow
az cosmosdb sql role assignment create --account-name $CosmosAccountName --resource-group $ResourceGroupName --role-definition-id "00000000-0000-0000-0000-000000000002" --principal-id $functionIdentity --scope "/"
Test-CommandSuccess "az cosmosdb sql role assignment create --account-name $CosmosAccountName --resource-group $ResourceGroupName --role-definition-id '00000000-0000-0000-0000-000000000002' --principal-id $functionIdentity --scope '/'" "Failed to assign Cosmos DB permissions"

# Create Static Web App
Write-Host "Creating Static Web App: $StaticWebAppName" -ForegroundColor Yellow
az staticwebapp create --name $StaticWebAppName --resource-group $ResourceGroupName --location $Location --source $GitHubRepo --branch $GitHubBranch --app-location "/" --output-location "admin"
Test-CommandSuccess "az staticwebapp create --name $StaticWebAppName --resource-group $ResourceGroupName --location $Location --source $GitHubRepo --branch $GitHubBranch --app-location '/' --output-location 'admin'" "Failed to create Static Web App"

# Verify Static Web App was created
if (-not (Test-AzureResource "Microsoft.Web/staticSites" $StaticWebAppName $ResourceGroupName)) {
    Write-Host "✗ Static Web App creation failed. Exiting." -ForegroundColor Red
    exit 1
}

# Get Static Web App details
Write-Host "Retrieving Static Web App details..." -ForegroundColor Yellow
$swaDetails = az staticwebapp show --name $StaticWebAppName --resource-group $ResourceGroupName --query '{"defaultHostname":defaultHostname,"deploymentToken":deploymentToken}' --output json
if (-not $swaDetails) {
    Write-Host "✗ Failed to retrieve Static Web App details. Exiting." -ForegroundColor Red
    exit 1
}

$swaHostname = ($swaDetails | ConvertFrom-Json).defaultHostname
$swaToken = ($swaDetails | ConvertFrom-Json).deploymentToken

if (-not $swaHostname -or -not $swaToken) {
    Write-Host "✗ Failed to parse Static Web App details. Exiting." -ForegroundColor Red
    exit 1
}

# Verify Static Web App URL is accessible
Write-Host "Verifying Static Web App URL accessibility..." -ForegroundColor Yellow
$swaUrl = "https://$swaHostname"
$swaUrlValid = $false
try {
    $response = Invoke-WebRequest -Uri $swaUrl -Method Head -TimeoutSec 30 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "✓ Static Web App URL is accessible: $swaUrl" -ForegroundColor Green
        $swaUrlValid = $true
    } else {
        Write-Host "⚠ Static Web App URL returned status $($response.StatusCode): $swaUrl" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ Static Web App URL may not be ready yet: $swaUrl" -ForegroundColor Yellow
    Write-Host "  This is normal for new deployments. It may take a few minutes to become accessible." -ForegroundColor White
}

# If URL is not accessible, offer alternatives
if (-not $swaUrlValid) {
    Write-Host "The Static Web App URL is not accessible. This could be due to:" -ForegroundColor Yellow
    Write-Host "1. The deployment is still in progress (wait a few minutes)" -ForegroundColor White
    Write-Host "2. The hostname is not available (try a different name)" -ForegroundColor White
    Write-Host "3. There's a configuration issue" -ForegroundColor White
    Write-Host ""
    $retry = Read-Host "Do you want to try a different Static Web App name? (y/n)"
    if ($retry -eq "y" -or $retry -eq "Y") {
        $newSwaName = Read-Host "Enter a new Static Web App name (or press Enter to keep '$StaticWebAppName')"
        if ($newSwaName) {
            Write-Host "You can create a new Static Web App with a different name using:" -ForegroundColor Yellow
            Write-Host "az staticwebapp create --name '$newSwaName' --resource-group '$ResourceGroupName' --location '$Location' --source '$GitHubRepo' --branch '$GitHubBranch' --app-location '/' --output-location 'admin'" -ForegroundColor White
        }
    }
}

# Get Function App URL
Write-Host "Retrieving Function App details..." -ForegroundColor Yellow
$functionAppDetails = az functionapp show --name $FunctionAppName --resource-group $ResourceGroupName --query '{"defaultHostName":defaultHostName}' --output json
$functionUrl = $null
$functionUrlValid = $false
if ($functionAppDetails) {
    $functionHostname = ($functionAppDetails | ConvertFrom-Json).defaultHostName
    if ($functionHostname) {
        $functionUrl = "https://$functionHostname"
        Write-Host "✓ Function App URL: $functionUrl" -ForegroundColor Green
        
        # Test Function App health endpoint
        Write-Host "Testing Function App health..." -ForegroundColor Yellow
        try {
            $healthResponse = Invoke-WebRequest -Uri "$functionUrl/api/health" -Method Get -TimeoutSec 30 -ErrorAction Stop
            if ($healthResponse.StatusCode -eq 200) {
                Write-Host "✓ Function App is responding: $functionUrl" -ForegroundColor Green
                $functionUrlValid = $true
            } else {
                Write-Host "⚠ Function App returned status $($healthResponse.StatusCode): $functionUrl" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "⚠ Function App may not be ready yet: $functionUrl" -ForegroundColor Yellow
            Write-Host "  This is normal for new deployments. It may take a few minutes to become accessible." -ForegroundColor White
        }
    }
}

# If Function App URL is not accessible, offer alternatives
if ($functionUrl -and -not $functionUrlValid) {
    Write-Host "The Function App URL is not accessible. This could be due to:" -ForegroundColor Yellow
    Write-Host "1. The deployment is still in progress (wait a few minutes)" -ForegroundColor White
    Write-Host "2. The hostname is not available (try a different name)" -ForegroundColor White
    Write-Host "3. There's a configuration issue" -ForegroundColor White
    Write-Host ""
    $retry = Read-Host "Do you want to try a different Function App name? (y/n)"
    if ($retry -eq "y" -or $retry -eq "Y") {
        $newFuncName = Read-Host "Enter a new Function App name (or press Enter to keep '$FunctionAppName')"
        if ($newFuncName) {
            Write-Host "You can create a new Function App with a different name using:" -ForegroundColor Yellow
            Write-Host "az functionapp create --name '$newFuncName' --resource-group '$ResourceGroupName' --storage-account '$StorageAccountName' --runtime python --runtime-version 3.9 --consumption-plan-location '$Location'" -ForegroundColor White
        }
    }
}

# Configure Static Web App settings
Write-Host "Configuring Static Web App settings" -ForegroundColor Yellow
az staticwebapp appsettings set --name $StaticWebAppName --resource-group $ResourceGroupName --setting-names COSMOS_ENDPOINT=$cosmosEndpoint COSMOS_KEY=$cosmosKey
Test-CommandSuccess "az staticwebapp appsettings set --name $StaticWebAppName --resource-group $ResourceGroupName --setting-names COSMOS_ENDPOINT=$cosmosEndpoint COSMOS_KEY=$cosmosKey" "Failed to configure Static Web App settings"

# Deploy Function App code
Write-Host "Deploying Function App code" -ForegroundColor Yellow
if (Test-Path "functions.zip") {
    az functionapp deployment source config-zip --name $FunctionAppName --resource-group $ResourceGroupName --src "functions.zip"
    Test-CommandSuccess "az functionapp deployment source config-zip --name $FunctionAppName --resource-group $ResourceGroupName --src 'functions.zip'" "Failed to deploy Function App code"
} else {
    Write-Host "⚠ Warning: functions.zip not found. Skipping Function App deployment." -ForegroundColor Yellow
    Write-Host "You can deploy the Function App code later using:" -ForegroundColor White
    Write-Host "az functionapp deployment source config-zip --name $FunctionAppName --resource-group $ResourceGroupName --src 'functions.zip'" -ForegroundColor White
}

Write-Host "Deployment completed successfully!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host "Resource Group: $ResourceGroupName" -ForegroundColor White
Write-Host "Function App: $FunctionAppName" -ForegroundColor White
Write-Host "Static Web App: $StaticWebAppName" -ForegroundColor White
Write-Host "Cosmos DB: $CosmosAccountName" -ForegroundColor White
Write-Host "Storage Account: $StorageAccountName" -ForegroundColor White
Write-Host "=========================================" -ForegroundColor Green
Write-Host "URLS:" -ForegroundColor Yellow
if ($swaUrlValid) {
    Write-Host "✓ Static Web App URL (VERIFIED): $swaUrl" -ForegroundColor Green
} else {
    Write-Host "⚠ Static Web App URL (NOT VERIFIED): $swaUrl" -ForegroundColor Yellow
    Write-Host "  This URL may not be accessible yet. Wait a few minutes and try again." -ForegroundColor White
}
if ($functionUrl) {
    if ($functionUrlValid) {
        Write-Host "✓ Function App URL (VERIFIED): $functionUrl" -ForegroundColor Green
    } else {
        Write-Host "⚠ Function App URL (NOT VERIFIED): $functionUrl" -ForegroundColor Yellow
        Write-Host "  This URL may not be accessible yet. Wait a few minutes and try again." -ForegroundColor White
    }
}
Write-Host "Deployment Token: $swaToken" -ForegroundColor White
Write-Host "=========================================" -ForegroundColor Green
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Configure OAuth applications (Yahoo and Google)" -ForegroundColor White
Write-Host "2. Set up Azure AD authentication" -ForegroundColor White
Write-Host "3. Configure environment variables" -ForegroundColor White
Write-Host "4. Test the application" -ForegroundColor White
Write-Host "See DEPLOYMENT.md for complete setup instructions." -ForegroundColor Yellow
