#!/bin/bash

# Fantasy Sports Helper - Azure Deployment Script (Bash)
# This script automates the deployment of the Fantasy Sports Helper to Azure

# Default values
SUBSCRIPTION_ID=""
RESOURCE_GROUP_NAME="fantasyhelperrg"
LOCATION=""
FUNCTION_APP_NAME="fantasyhelperfunc"
STATIC_WEB_APP_NAME="fantasyhelperweb"
COSMOS_ACCOUNT_NAME="fantasyhelpercosmos"
STORAGE_ACCOUNT_NAME="fantasyhelperstorage"
GITHUB_REPO="https://github.com/yourusername/FantasySportsHelper"
GITHUB_BRANCH="main"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --subscription-id)
            SUBSCRIPTION_ID="$2"
            shift 2
            ;;
        --resource-group)
            RESOURCE_GROUP_NAME="$2"
            shift 2
            ;;
        --location)
            LOCATION="$2"
            shift 2
            ;;
        --function-app)
            FUNCTION_APP_NAME="$2"
            shift 2
            ;;
        --static-web-app)
            STATIC_WEB_APP_NAME="$2"
            shift 2
            ;;
        --cosmos-account)
            COSMOS_ACCOUNT_NAME="$2"
            shift 2
            ;;
        --storage-account)
            STORAGE_ACCOUNT_NAME="$2"
            shift 2
            ;;
        --github-repo)
            GITHUB_REPO="$2"
            shift 2
            ;;
        --github-branch)
            GITHUB_BRANCH="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --subscription-id ID     Azure subscription ID"
            echo "  --resource-group NAME    Resource group name (default: fantasyhelperrg)"
            echo "  --location LOCATION      Azure location (default: West US)"
            echo "  --function-app NAME      Function App name (default: fantasyhelperfunc)"
            echo "  --static-web-app NAME    Static Web App name (default: fantasyhelperweb)"
            echo "  --cosmos-account NAME    Cosmos DB account name (default: fantasyhelpercosmos)"
            echo "  --storage-account NAME  Storage account name (default: fantasyhelperstorage)"
            echo "  --github-repo URL        GitHub repository URL"
            echo "  --github-branch BRANCH   GitHub branch (default: main)"
            echo "  -h, --help               Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "Fantasy Sports Helper - Azure Deployment"
echo "========================================="

# Function to check if a command succeeded
check_command() {
    local command="$1"
    local error_message="$2"
    if [ $? -ne 0 ]; then
        echo "❌ Error: $error_message"
        echo "Command failed: $command"
        read -p "Do you want to continue anyway? (y/n): " continue_choice
        if [[ $continue_choice != "y" && $continue_choice != "Y" ]]; then
            exit 1
        fi
    fi
}

# Function to validate Azure resource exists
check_azure_resource() {
    local resource_type="$1"
    local resource_name="$2"
    local resource_group="$3"
    
    if az resource show --name "$resource_name" --resource-group "$resource_group" --resource-type "$resource_type" --output tsv >/dev/null 2>&1; then
        echo "✅ $resource_type '$resource_name' exists"
        return 0
    else
        echo "❌ $resource_type '$resource_name' not found"
        return 1
    fi
}

# Check if Azure CLI is installed
echo "Checking Azure CLI installation..."
if ! command -v az &> /dev/null; then
    echo "❌ Error: Azure CLI is not installed or not in PATH"
    echo "Please install Azure CLI from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

az_version=$(az version --output tsv 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "✅ Azure CLI version: $az_version"
else
    echo "❌ Error: Failed to get Azure CLI version"
    exit 1
fi

# Validate and set location
if [ -z "$LOCATION" ]; then
    echo "Available regions for Static Web Apps:"
    echo "1. westus2 (West US 2)"
    echo "2. centralus (Central US)"
    echo "3. eastus2 (East US 2)"
    echo "4. westeurope (West Europe)"
    echo "5. eastasia (East Asia)"
    echo ""
    read -p "Select region (1-5) or enter custom region name: " choice
    
    case $choice in
        1) LOCATION="westus2" ;;
        2) LOCATION="centralus" ;;
        3) LOCATION="eastus2" ;;
        4) LOCATION="westeurope" ;;
        5) LOCATION="eastasia" ;;
        *) LOCATION="$choice" ;;
    esac
    
    if [ -z "$LOCATION" ]; then
        echo "❌ Error: Location is required. Exiting."
        exit 1
    fi
fi

echo "✅ Selected region: $LOCATION"

# Check if user is logged in
echo "Checking Azure authentication..."
if ! az account show --output tsv >/dev/null 2>&1; then
    echo "❌ Not logged in to Azure CLI"
    echo "Please log in to Azure CLI first:"
    echo "az login"
    read -p "Press Enter after logging in, or type 'exit' to quit: " login_choice
    if [[ $login_choice == "exit" ]]; then
        exit 1
    fi
    
    # Re-check login
    if ! az account show --output tsv >/dev/null 2>&1; then
        echo "❌ Still not logged in. Exiting."
        exit 1
    fi
fi

account=$(az account show --query "user.name" --output tsv)
echo "✅ Logged in as: $account"

# Set subscription if provided
if [ -n "$SUBSCRIPTION_ID" ]; then
    echo "Setting subscription to: $SUBSCRIPTION_ID"
    az account set --subscription "$SUBSCRIPTION_ID"
    check_command "az account set --subscription $SUBSCRIPTION_ID" "Failed to set subscription"
fi

# Check if resource group already exists
echo "Checking if resource group '$RESOURCE_GROUP_NAME' already exists..."
if check_azure_resource "Microsoft.Resources/resourceGroups" "$RESOURCE_GROUP_NAME" "$RESOURCE_GROUP_NAME"; then
    read -p "Resource group already exists. Do you want to continue and update existing resources? (y/n): " overwrite_choice
    if [[ $overwrite_choice != "y" && $overwrite_choice != "Y" ]]; then
        echo "Exiting. Please choose a different resource group name."
        exit 1
    fi
fi

# Check if resource names are available
echo "Checking resource name availability..."
echo "This helps avoid conflicts with existing Azure resources."

# Check Static Web App name availability
if az staticwebapp show --name "$STATIC_WEB_APP_NAME" --resource-group "$RESOURCE_GROUP_NAME" --output tsv >/dev/null 2>&1; then
    echo "⚠️  Static Web App name '$STATIC_WEB_APP_NAME' may already exist in this resource group."
    read -p "Do you want to use a different Static Web App name? (y/n): " change_swa
    if [[ $change_swa == "y" || $change_swa == "Y" ]]; then
        read -p "Enter a new Static Web App name: " STATIC_WEB_APP_NAME
    fi
fi

# Check Function App name availability
if az functionapp show --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP_NAME" --output tsv >/dev/null 2>&1; then
    echo "⚠️  Function App name '$FUNCTION_APP_NAME' may already exist in this resource group."
    read -p "Do you want to use a different Function App name? (y/n): " change_func
    if [[ $change_func == "y" || $change_func == "Y" ]]; then
        read -p "Enter a new Function App name: " FUNCTION_APP_NAME
    fi
fi

# Check Cosmos DB name availability
if az cosmosdb show --name "$COSMOS_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP_NAME" --output tsv >/dev/null 2>&1; then
    echo "⚠️  Cosmos DB name '$COSMOS_ACCOUNT_NAME' may already exist in this resource group."
    read -p "Do you want to use a different Cosmos DB name? (y/n): " change_cosmos
    if [[ $change_cosmos == "y" || $change_cosmos == "Y" ]]; then
        read -p "Enter a new Cosmos DB name: " COSMOS_ACCOUNT_NAME
    fi
fi

# Check Storage Account name availability
if az storage account show --name "$STORAGE_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP_NAME" --output tsv >/dev/null 2>&1; then
    echo "⚠️  Storage Account name '$STORAGE_ACCOUNT_NAME' may already exist in this resource group."
    read -p "Do you want to use a different Storage Account name? (y/n): " change_storage
    if [[ $change_storage == "y" || $change_storage == "Y" ]]; then
        read -p "Enter a new Storage Account name: " STORAGE_ACCOUNT_NAME
    fi
fi

echo "Using the following resource names:"
echo "  Static Web App: $STATIC_WEB_APP_NAME"
echo "  Function App: $FUNCTION_APP_NAME"
echo "  Cosmos DB: $COSMOS_ACCOUNT_NAME"
echo "  Storage Account: $STORAGE_ACCOUNT_NAME"
echo ""

# Create resource group
echo "Creating resource group: $RESOURCE_GROUP_NAME"
az group create --name "$RESOURCE_GROUP_NAME" --location "$LOCATION"
check_command "az group create --name $RESOURCE_GROUP_NAME --location $LOCATION" "Failed to create resource group"

# Verify resource group was created
if ! check_azure_resource "Microsoft.Resources/resourceGroups" "$RESOURCE_GROUP_NAME" "$RESOURCE_GROUP_NAME"; then
    echo "❌ Resource group creation failed. Exiting."
    exit 1
fi

# Create Cosmos DB account (provisioned for free tier)
echo "Creating Cosmos DB account: $COSMOS_ACCOUNT_NAME"
az cosmosdb create --name "$COSMOS_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP_NAME" --locations regionName="$LOCATION"
check_command "az cosmosdb create --name $COSMOS_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME --locations regionName=$LOCATION" "Failed to create Cosmos DB account"

# Verify Cosmos DB was created
if ! check_azure_resource "Microsoft.DocumentDB/databaseAccounts" "$COSMOS_ACCOUNT_NAME" "$RESOURCE_GROUP_NAME"; then
    echo "❌ Cosmos DB creation failed. Exiting."
    exit 1
fi

# Create Cosmos DB database and containers
echo "Creating Cosmos DB database and containers"
cosmos_key=$(az cosmosdb keys list --name "$COSMOS_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP_NAME" --type keys --query primaryMasterKey --output tsv)
if [ -z "$cosmos_key" ]; then
    echo "❌ Failed to retrieve Cosmos DB key. Exiting."
    exit 1
fi
cosmos_endpoint="https://$COSMOS_ACCOUNT_NAME.documents.azure.com:443/"

# Create database
az cosmosdb sql database create --account-name "$COSMOS_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP_NAME" --name fantasyhelper
check_command "az cosmosdb sql database create --account-name $COSMOS_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME --name fantasyhelper" "Failed to create database"

# Create containers
az cosmosdb sql container create --account-name "$COSMOS_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP_NAME" --database-name fantasyhelper --name leagues --partition-key-path "/id"
check_command "az cosmosdb sql container create --account-name $COSMOS_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME --database-name fantasyhelper --name leagues --partition-key-path /id" "Failed to create leagues container"

az cosmosdb sql container create --account-name "$COSMOS_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP_NAME" --database-name fantasyhelper --name managers --partition-key-path "/id"
check_command "az cosmosdb sql container create --account-name $COSMOS_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME --database-name fantasyhelper --name managers --partition-key-path /id" "Failed to create managers container"

az cosmosdb sql container create --account-name "$COSMOS_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP_NAME" --database-name fantasyhelper --name schedules --partition-key-path "/id"
check_command "az cosmosdb sql container create --account-name $COSMOS_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME --database-name fantasyhelper --name schedules --partition-key-path /id" "Failed to create schedules container"

az cosmosdb sql container create --account-name "$COSMOS_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP_NAME" --database-name fantasyhelper --name tokens --partition-key-path "/id"
check_command "az cosmosdb sql container create --account-name $COSMOS_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME --database-name fantasyhelper --name tokens --partition-key-path /id" "Failed to create tokens container"

# Create storage account
echo "Creating storage account: $STORAGE_ACCOUNT_NAME"
az storage account create --name "$STORAGE_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP_NAME" --location "$LOCATION" --sku Standard_LRS
check_command "az storage account create --name $STORAGE_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME --location $LOCATION --sku Standard_LRS" "Failed to create storage account"

# Verify storage account was created
if ! check_azure_resource "Microsoft.Storage/storageAccounts" "$STORAGE_ACCOUNT_NAME" "$RESOURCE_GROUP_NAME"; then
    echo "❌ Storage account creation failed. Exiting."
    exit 1
fi

# Create Function App
echo "Creating Function App: $FUNCTION_APP_NAME"
az functionapp create --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP_NAME" --storage-account "$STORAGE_ACCOUNT_NAME" --runtime python --runtime-version 3.9 --consumption-plan-location "$LOCATION"
check_command "az functionapp create --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP_NAME --storage-account $STORAGE_ACCOUNT_NAME --runtime python --runtime-version 3.9 --consumption-plan-location $LOCATION" "Failed to create Function App"

# Verify Function App was created
if ! check_azure_resource "Microsoft.Web/sites" "$FUNCTION_APP_NAME" "$RESOURCE_GROUP_NAME"; then
    echo "❌ Function App creation failed. Exiting."
    exit 1
fi

# Configure Function App settings
echo "Configuring Function App settings"
az functionapp config appsettings set --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP_NAME" --settings COSMOS_ENDPOINT="$cosmos_endpoint" COSMOS_KEY="$cosmos_key"
check_command "az functionapp config appsettings set --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP_NAME --settings COSMOS_ENDPOINT=$cosmos_endpoint COSMOS_KEY=$cosmos_key" "Failed to configure Function App settings"

# Enable Managed Identity
echo "Enabling Managed Identity for Function App"
az functionapp identity assign --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP_NAME"
check_command "az functionapp identity assign --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP_NAME" "Failed to enable Managed Identity"

# Get Function App identity
function_identity=$(az functionapp identity show --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP_NAME" --query principalId --output tsv)
if [ -z "$function_identity" ]; then
    echo "❌ Failed to get Function App identity. Exiting."
    exit 1
fi

# Assign Cosmos DB permissions
echo "Assigning Cosmos DB permissions to Function App"
az cosmosdb sql role assignment create --account-name "$COSMOS_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP_NAME" --role-definition-id "00000000-0000-0000-0000-000000000002" --principal-id "$function_identity" --scope "/"
check_command "az cosmosdb sql role assignment create --account-name $COSMOS_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME --role-definition-id 00000000-0000-0000-0000-000000000002 --principal-id $function_identity --scope /" "Failed to assign Cosmos DB permissions"

# Create Static Web App
echo "Creating Static Web App: $STATIC_WEB_APP_NAME"
az staticwebapp create --name "$STATIC_WEB_APP_NAME" --resource-group "$RESOURCE_GROUP_NAME" --location "$LOCATION" --source "$GITHUB_REPO" --branch "$GITHUB_BRANCH" --app-location "/" --output-location "admin"
check_command "az staticwebapp create --name $STATIC_WEB_APP_NAME --resource-group $RESOURCE_GROUP_NAME --location $LOCATION --source $GITHUB_REPO --branch $GITHUB_BRANCH --app-location / --output-location admin" "Failed to create Static Web App"

# Verify Static Web App was created
if ! check_azure_resource "Microsoft.Web/staticSites" "$STATIC_WEB_APP_NAME" "$RESOURCE_GROUP_NAME"; then
    echo "❌ Static Web App creation failed. Exiting."
    exit 1
fi

# Get Static Web App details
echo "Retrieving Static Web App details..."
swa_details=$(az staticwebapp show --name "$STATIC_WEB_APP_NAME" --resource-group "$RESOURCE_GROUP_NAME" --query "{defaultHostname:defaultHostname,deploymentToken:deploymentToken}" --output json)
if [ -z "$swa_details" ]; then
    echo "❌ Failed to retrieve Static Web App details. Exiting."
    exit 1
fi

swa_hostname=$(echo "$swa_details" | jq -r '.defaultHostname')
swa_token=$(echo "$swa_details" | jq -r '.deploymentToken')

if [ -z "$swa_hostname" ] || [ -z "$swa_token" ]; then
    echo "❌ Failed to parse Static Web App details. Exiting."
    exit 1
fi

# Verify Static Web App URL is accessible
echo "Verifying Static Web App URL accessibility..."
swa_url="https://$swa_hostname"
swa_url_valid=false
if curl -s --head --max-time 30 "$swa_url" >/dev/null 2>&1; then
    echo "✅ Static Web App URL is accessible: $swa_url"
    swa_url_valid=true
else
    echo "⚠️  Static Web App URL may not be ready yet: $swa_url"
    echo "  This is normal for new deployments. It may take a few minutes to become accessible."
fi

# If URL is not accessible, offer alternatives
if [ "$swa_url_valid" = false ]; then
    echo "The Static Web App URL is not accessible. This could be due to:"
    echo "1. The deployment is still in progress (wait a few minutes)"
    echo "2. The hostname is not available (try a different name)"
    echo "3. There's a configuration issue"
    echo ""
    read -p "Do you want to try a different Static Web App name? (y/n): " retry_swa
    if [[ $retry_swa == "y" || $retry_swa == "Y" ]]; then
        read -p "Enter a new Static Web App name (or press Enter to keep '$STATIC_WEB_APP_NAME'): " new_swa_name
        if [ -n "$new_swa_name" ]; then
            echo "You can create a new Static Web App with a different name using:"
            echo "az staticwebapp create --name '$new_swa_name' --resource-group '$RESOURCE_GROUP_NAME' --location '$LOCATION' --source '$GITHUB_REPO' --branch '$GITHUB_BRANCH' --app-location '/' --output-location 'admin'"
        fi
    fi
fi

# Get Function App URL
echo "Retrieving Function App details..."
function_app_details=$(az functionapp show --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP_NAME" --query "{defaultHostName:defaultHostName}" --output json)
if [ -n "$function_app_details" ]; then
    function_hostname=$(echo "$function_app_details" | jq -r '.defaultHostName')
    if [ -n "$function_hostname" ] && [ "$function_hostname" != "null" ]; then
        function_url="https://$function_hostname"
        echo "✅ Function App URL: $function_url"
        
        # Test Function App health endpoint
        echo "Testing Function App health..."
        if curl -s --max-time 30 "$function_url/api/health" >/dev/null 2>&1; then
            echo "✅ Function App is responding: $function_url"
        else
            echo "⚠️  Function App may not be ready yet: $function_url"
            echo "  This is normal for new deployments. It may take a few minutes to become accessible."
        fi
    fi
fi

# Configure Static Web App settings
echo "Configuring Static Web App settings"
az staticwebapp appsettings set --name "$STATIC_WEB_APP_NAME" --resource-group "$RESOURCE_GROUP_NAME" --setting-names COSMOS_ENDPOINT="$cosmos_endpoint" COSMOS_KEY="$cosmos_key"
check_command "az staticwebapp appsettings set --name $STATIC_WEB_APP_NAME --resource-group $RESOURCE_GROUP_NAME --setting-names COSMOS_ENDPOINT=$cosmos_endpoint COSMOS_KEY=$cosmos_key" "Failed to configure Static Web App settings"

# Deploy Function App code
echo "Deploying Function App code"
if [ -f "functions.zip" ]; then
    az functionapp deployment source config-zip --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP_NAME" --src "functions.zip"
    check_command "az functionapp deployment source config-zip --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP_NAME --src functions.zip" "Failed to deploy Function App code"
else
    echo "⚠️  Warning: functions.zip not found. Skipping Function App deployment."
    echo "You can deploy the Function App code later using:"
    echo "az functionapp deployment source config-zip --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP_NAME --src functions.zip"
fi

echo "Deployment completed successfully!"
echo "========================================="
echo "Resource Group: $RESOURCE_GROUP_NAME"
echo "Function App: $FUNCTION_APP_NAME"
echo "Static Web App: $STATIC_WEB_APP_NAME"
echo "Cosmos DB: $COSMOS_ACCOUNT_NAME"
echo "Storage Account: $STORAGE_ACCOUNT_NAME"
echo ""
echo "Free Tier Benefits:"
echo "✓ Function App: 1M requests/month free"
echo "✓ Cosmos DB: 25 RU/s + 25 GB storage/month free"
echo "✓ Static Web App: 100 GB bandwidth/month free"
echo "✓ Storage Account: 5 GB storage/month free"
echo "========================================="
echo "URLS:"
if [ "$swa_url_valid" = true ]; then
    echo "✅ Static Web App URL (VERIFIED): $swa_url"
else
    echo "⚠️  Static Web App URL (NOT VERIFIED): $swa_url"
    echo "  This URL may not be accessible yet. Wait a few minutes and try again."
fi
if [ -n "$function_url" ]; then
    if [ "$function_url_valid" = true ]; then
        echo "✅ Function App URL (VERIFIED): $function_url"
    else
        echo "⚠️  Function App URL (NOT VERIFIED): $function_url"
        echo "  This URL may not be accessible yet. Wait a few minutes and try again."
    fi
fi
echo "Deployment Token: $swa_token"
echo "========================================="
echo "Next Steps:"
echo "1. Configure OAuth applications (Yahoo and Google)"
echo "2. Set up Azure AD authentication"
echo "3. Configure environment variables"
echo "4. Test the application"
echo "See DEPLOYMENT.md for complete setup instructions."