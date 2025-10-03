# Fantasy Sports Helper - Azure Deployment Script (PowerShell)
# Run this script to deploy the complete application to Azure

param(
    [string]$ResourceGroup = "fantasyhelperrg",
    [string]$Location = "westus",
    [string]$CosmosAccount = "fantasyhelpercosmos",
    [string]$FunctionApp = "fantasyhelperfunctions",
    [string]$SwaName = "fantasyhelperadmin",
    [string]$StorageAccount = "fantasyhelperstorage"
)

Write-Host "🚀 Starting Fantasy Sports Helper deployment to Azure..." -ForegroundColor Green

# Step 1: Create Resource Group
Write-Host "📦 Creating resource group..." -ForegroundColor Yellow
az group create --name $ResourceGroup --location $Location

# Step 2: Create Cosmos DB
Write-Host "🗄️ Creating Cosmos DB account..." -ForegroundColor Yellow
az cosmosdb create `
  --resource-group $ResourceGroup `
  --name $CosmosAccount `
  --kind GlobalDocumentDB `
  --locations regionName=$Location failoverPriority=0 isZoneRedundant=False `
  --capabilities EnableServerless

# Create database
az cosmosdb sql database create `
  --resource-group $ResourceGroup `
  --account-name $CosmosAccount `
  --name "fantasy_helper"

# Step 3: Create Storage Account
Write-Host "💾 Creating storage account..." -ForegroundColor Yellow
az storage account create `
  --resource-group $ResourceGroup `
  --name $StorageAccount `
  --location $Location `
  --sku Standard_LRS

# Step 4: Create Function App
Write-Host "⚡ Creating Function App..." -ForegroundColor Yellow
az functionapp create `
  --resource-group $ResourceGroup `
  --consumption-plan-location $Location `
  --runtime python `
  --runtime-version 3.9 `
  --functions-version 4 `
  --name $FunctionApp `
  --storage-account $StorageAccount `
  --os-type Linux

# Step 5: Enable Managed Identity
Write-Host "🔐 Enabling managed identity..." -ForegroundColor Yellow
az functionapp identity assign `
  --resource-group $ResourceGroup `
  --name $FunctionApp

# Get principal ID
$PrincipalId = az functionapp identity show `
  --resource-group $ResourceGroup `
  --name $FunctionApp `
  --query principalId -o tsv

# Step 6: Assign Cosmos DB Role
Write-Host "🔑 Assigning Cosmos DB permissions..." -ForegroundColor Yellow
$CosmosId = az cosmosdb show `
  --resource-group $ResourceGroup `
  --name $CosmosAccount `
  --query id -o tsv

az role assignment create `
  --assignee $PrincipalId `
  --role "Cosmos DB Built-in Data Contributor" `
  --scope $CosmosId

# Step 7: Create Static Web App
Write-Host "🌐 Creating Static Web App..." -ForegroundColor Yellow
az staticwebapp create `
  --name $SwaName `
  --resource-group $ResourceGroup `
  --source "https://github.com/DaveOchoa/FantasySportsHelper" `
  --location $Location `
  --branch main `
  --app-location "/admin" `
  --output-location "/admin"

# Step 8: Configure Function App Settings
Write-Host "⚙️ Configuring Function App settings..." -ForegroundColor Yellow

# Get Cosmos DB settings
$CosmosEndpoint = "https://$CosmosAccount.documents.azure.com:443/"
$CosmosKey = az cosmosdb keys list `
  --resource-group $ResourceGroup `
  --name $CosmosAccount `
  --type keys `
  --query 'primaryMasterKey' -o tsv

# Configure basic settings
az functionapp config appsettings set `
  --resource-group $ResourceGroup `
  --name $FunctionApp `
  --settings `
    COSMOS_ENDPOINT="$CosmosEndpoint" `
    COSMOS_KEY="$CosmosKey" `
    COSMOS_DB="fantasy_helper" `
    FUNCTIONS_WORKER_RUNTIME="python" `
    WEBSITE_RUN_FROM_PACKAGE="1"

Write-Host "✅ Basic infrastructure deployed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "🔧 Next steps:" -ForegroundColor Cyan
Write-Host "1. Configure OAuth applications (Yahoo and Google)"
Write-Host "2. Set OAuth credentials in Function App settings:"
Write-Host "   az functionapp config appsettings set --resource-group $ResourceGroup --name $FunctionApp --settings YAHOO_CLIENT_ID='<your-id>' YAHOO_CLIENT_SECRET='<your-secret>'"
Write-Host "3. Deploy your code:"
Write-Host "   func azure functionapp publish $FunctionApp --python"
Write-Host "4. Create Static Web App for admin UI"
Write-Host "5. Configure Azure AD authentication"
Write-Host ""
Write-Host "📋 Resources created:" -ForegroundColor Cyan
Write-Host "   - Resource Group: $ResourceGroup"
Write-Host "   - Cosmos DB: $CosmosAccount"
Write-Host "   - Function App: $FunctionApp"
Write-Host "   - Storage Account: $StorageAccount"
Write-Host "   - Static Web App: $SwaName"
Write-Host ""
Write-Host "🔗 URLs:" -ForegroundColor Blue
Write-Host "   - Function App: https://$FunctionApp.azurewebsites.net"
Write-Host "   - Admin UI: https://$SwaName.azurestaticapps.net/admin"
Write-Host ""
Write-Host "See DEPLOYMENT.md for complete setup instructions." -ForegroundColor Yellow