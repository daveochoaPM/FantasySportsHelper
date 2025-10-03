#!/bin/bash

# Fantasy Sports Helper - Azure Deployment Script
# Run this script to deploy the complete application to Azure

set -e  # Exit on any error

# Configuration - Update these values
RESOURCE_GROUP="fantasyhelperrg"
LOCATION="westus"
COSMOS_ACCOUNT="fantasyhelpercosmos"
FUNCTION_APP="fantasyhelperfunctions"
SWA_NAME="fantasyhelperadmin"
STORAGE_ACCOUNT="fantasyhelperstorage"

echo "🚀 Starting Fantasy Sports Helper deployment to Azure..."

# Step 1: Create Resource Group
echo "📦 Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# Step 2: Create Cosmos DB
echo "🗄️ Creating Cosmos DB account..."
az cosmosdb create \
  --resource-group $RESOURCE_GROUP \
  --name $COSMOS_ACCOUNT \
  --kind GlobalDocumentDB \
  --locations regionName=$LOCATION failoverPriority=0 isZoneRedundant=False \
  --capabilities EnableServerless

# Create database
az cosmosdb sql database create \
  --resource-group $RESOURCE_GROUP \
  --account-name $COSMOS_ACCOUNT \
  --name "fantasy_helper"

# Step 3: Create Storage Account
echo "💾 Creating storage account..."
az storage account create \
  --resource-group $RESOURCE_GROUP \
  --name $STORAGE_ACCOUNT \
  --location $LOCATION \
  --sku Standard_LRS

# Step 4: Create Function App
echo "⚡ Creating Function App..."
az functionapp create \
  --resource-group $RESOURCE_GROUP \
  --consumption-plan-location $LOCATION \
  --runtime python \
  --runtime-version 3.9 \
  --functions-version 4 \
  --name $FUNCTION_APP \
  --storage-account $STORAGE_ACCOUNT \
  --os-type Linux

# Step 5: Enable Managed Identity
echo "🔐 Enabling managed identity..."
az functionapp identity assign \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP

# Get principal ID
PRINCIPAL_ID=$(az functionapp identity show \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP \
  --query principalId -o tsv)

# Step 6: Assign Cosmos DB Role
echo "🔑 Assigning Cosmos DB permissions..."
COSMOS_ID=$(az cosmosdb show \
  --resource-group $RESOURCE_GROUP \
  --name $COSMOS_ACCOUNT \
  --query id -o tsv)

az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Cosmos DB Built-in Data Contributor" \
  --scope $COSMOS_ID

# Step 7: Create Static Web App
echo "🌐 Creating Static Web App..."
az staticwebapp create \
  --name $SWA_NAME \
  --resource-group $RESOURCE_GROUP \
  --source "https://github.com/DaveOchoa/FantasySportsHelper" \
  --location $LOCATION \
  --branch main \
  --app-location "/admin" \
  --output-location "/admin"

# Step 8: Configure Function App Settings
echo "⚙️ Configuring Function App settings..."

# Get Cosmos DB settings
COSMOS_ENDPOINT="https://$COSMOS_ACCOUNT.documents.azure.com:443/"
COSMOS_KEY=$(az cosmosdb keys list \
  --resource-group $RESOURCE_GROUP \
  --name $COSMOS_ACCOUNT \
  --type keys \
  --query 'primaryMasterKey' -o tsv)

# Configure basic settings
az functionapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP \
  --settings \
    COSMOS_ENDPOINT="$COSMOS_ENDPOINT" \
    COSMOS_KEY="$COSMOS_KEY" \
    COSMOS_DB="fantasy_helper" \
    FUNCTIONS_WORKER_RUNTIME="python" \
    WEBSITE_RUN_FROM_PACKAGE="1"

echo "✅ Basic infrastructure deployed successfully!"
echo ""
echo "🔧 Next steps:"
echo "1. Configure OAuth applications (Yahoo and Google)"
echo "2. Set OAuth credentials in Function App settings:"
echo "   az functionapp config appsettings set --resource-group $RESOURCE_GROUP --name $FUNCTION_APP --settings YAHOO_CLIENT_ID='<your-id>' YAHOO_CLIENT_SECRET='<your-secret>'"
echo "3. Deploy your code:"
echo "   func azure functionapp publish $FUNCTION_APP --python"
echo "4. Create Static Web App for admin UI"
echo "5. Configure Azure AD authentication"
echo ""
echo "📋 Resources created:"
echo "   - Resource Group: $RESOURCE_GROUP"
echo "   - Cosmos DB: $COSMOS_ACCOUNT"
echo "   - Function App: $FUNCTION_APP"
echo "   - Storage Account: $STORAGE_ACCOUNT"
echo "   - Static Web App: $SWA_NAME"
echo ""
echo "🔗 URLs:"
echo "   - Function App: https://$FUNCTION_APP.azurewebsites.net"
echo "   - Admin UI: https://$SWA_NAME.azurestaticapps.net/admin"
echo ""
echo "See DEPLOYMENT.md for complete setup instructions."
