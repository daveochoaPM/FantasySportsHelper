# Manual Deployment Guide - Fantasy Sports Helper

This guide provides step-by-step instructions to manually deploy your Fantasy Sports Helper application after ARM template deployment issues.

## Prerequisites

- Azure subscription with contributor access
- Azure CLI installed (`az --version`)
- Git configured
- PowerShell (Windows) or Bash (Linux/Mac)

## Step 1: Create Azure Resources Manually

### 1.1 Create Resource Group

```powershell
# Set variables
$RESOURCE_GROUP = "FSH-NHL"
$LOCATION = "westus2"  # or your preferred region

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION
```

### 1.2 Create Cosmos DB Account

```powershell
# Set variables
$COSMOS_ACCOUNT = "fantasyhelpercosmos$(Get-Random -Maximum 9999)"
$DATABASE_NAME = "fantasy_helper"

# Create Cosmos DB account
az cosmosdb create `
  --resource-group $RESOURCE_GROUP `
  --name $COSMOS_ACCOUNT `
  --kind GlobalDocumentDB `
  --locations regionName=$LOCATION failoverPriority=0 isZoneRedundant=False

# Create database
az cosmosdb sql database create `
  --resource-group $RESOURCE_GROUP `
  --account-name $COSMOS_ACCOUNT `
  --name $DATABASE_NAME

# Create container with provisioned throughput (qualifies for free tier)
az cosmosdb sql container create `
  --resource-group $RESOURCE_GROUP `
  --account-name $COSMOS_ACCOUNT `
  --database-name $DATABASE_NAME `
  --name leagues `
  --partition-key-path "/id" `
  --throughput 400
```

### 1.3 Create Storage Account

```powershell
# Set variables
$STORAGE_ACCOUNT = "fantasyhelperstorage$(Get-Random -Maximum 9999)"

# Create storage account
az storage account create `
  --resource-group $RESOURCE_GROUP `
  --name $STORAGE_ACCOUNT `
  --location $LOCATION `
  --sku Standard_LRS
```

### 1.4 Create Function App

```powershell
# Set variables
$FUNCTION_APP = "fantasyhelperfunctions$(Get-Random -Maximum 9999)"

# Create Function App
az functionapp create `
  --resource-group $RESOURCE_GROUP `
  --consumption-plan-location $LOCATION `
  --runtime python `
  --runtime-version 3.10 `
  --functions-version 4 `
  --name $FUNCTION_APP `
  --storage-account $STORAGE_ACCOUNT `
  --os-type Linux
```

### 1.5 Create Static Web App

```powershell
# Set variables
$SWA_NAME = "fantasyhelperadmin$(Get-Random -Maximum 9999)"

# Create Static Web App
az staticwebapp create `
  --name $SWA_NAME `
  --resource-group $RESOURCE_GROUP `
  --source "https://github.com/DaveOchoa/FantasySportsHelper" `
  --location $LOCATION `
  --branch main `
  --app-location "/admin" `
  --output-location "/admin"
```

## Step 2: Configure Function App Settings

### 2.1 Get Cosmos DB Connection Details

```powershell
# Get Cosmos DB endpoint and key
$COSMOS_ENDPOINT = "https://$COSMOS_ACCOUNT.documents.azure.com:443/"
$COSMOS_KEY = az cosmosdb keys list --resource-group $RESOURCE_GROUP --name $COSMOS_ACCOUNT --type keys --query 'primaryMasterKey' -o tsv
```

### 2.2 Configure Function App Application Settings

```powershell
# Configure Function App settings
az functionapp config appsettings set `
  --resource-group $RESOURCE_GROUP `
  --name $FUNCTION_APP `
  --settings `
    COSMOS_ENDPOINT="$COSMOS_ENDPOINT" `
    COSMOS_KEY="$COSMOS_KEY" `
    COSMOS_DB="$DATABASE_NAME" `
    FUNCTIONS_WORKER_RUNTIME="python" `
    WEBSITE_RUN_FROM_PACKAGE="1" `
    YAHOO_CLIENT_ID="" `
    YAHOO_CLIENT_SECRET="" `
    YAHOO_REDIRECT_URI="https://$FUNCTION_APP.azurewebsites.net/api/auth/yahoo/callback" `
    GOOGLE_CLIENT_ID="" `
    GOOGLE_CLIENT_SECRET="" `
    GMAIL_REDIRECT_URI="https://$FUNCTION_APP.azurewebsites.net/api/auth/google/callback" `
    OPENAI_API_KEY=""
```

## Step 2.5: Set Up Key Vault for Secure Secret Management (Recommended)

### 2.5.1 Create Key Vault

```powershell
# Set variables
$KEY_VAULT_NAME = "fantasyhelperkv$(Get-Random -Maximum 9999)"

# Create Key Vault
az keyvault create `
  --name $KEY_VAULT_NAME `
  --resource-group $RESOURCE_GROUP `
  --location $LOCATION `
  --enable-rbac-authorization true
```

### 2.5.2 Update Function App Settings to Use Key Vault References

```powershell
# Update Function App settings to use Key Vault references
az functionapp config appsettings set `
  --resource-group $RESOURCE_GROUP `
  --name $FUNCTION_APP `
  --settings `
    KEY_VAULT_URL="https://$KEY_VAULT_NAME.vault.azure.net/" `
    YAHOO_CLIENT_ID="@Microsoft.KeyVault(SecretUri=https://$KEY_VAULT_NAME.vault.azure.net/secrets/YAHOO-CLIENT-ID/)" `
    YAHOO_CLIENT_SECRET="@Microsoft.KeyVault(SecretUri=https://$KEY_VAULT_NAME.vault.azure.net/secrets/YAHOO-CLIENT-SECRET/)" `
    GOOGLE_CLIENT_ID="@Microsoft.KeyVault(SecretUri=https://$KEY_VAULT_NAME.vault.azure.net/secrets/GOOGLE-CLIENT-ID/)" `
    GOOGLE_CLIENT_SECRET="@Microsoft.KeyVault(SecretUri=https://$KEY_VAULT_NAME.vault.azure.net/secrets/GOOGLE-CLIENT-SECRET/)" `
    OPENAI_API_KEY="@Microsoft.KeyVault(SecretUri=https://$KEY_VAULT_NAME.vault.azure.net/secrets/OPENAI-API-KEY/)"
```

### 2.5.3 Assign Key Vault Access to Function App

```powershell
# Get Function App managed identity principal ID
$FUNCTION_PRINCIPAL_ID = az functionapp identity show `
  --resource-group $RESOURCE_GROUP `
  --name $FUNCTION_APP `
  --query principalId -o tsv

# Assign Key Vault Secrets User role
az role assignment create `
  --assignee $FUNCTION_PRINCIPAL_ID `
  --role "Key Vault Secrets User" `
  --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.KeyVault/vaults/$KEY_VAULT_NAME"
```

### 2.5.4 Add Secrets to Key Vault via Admin Portal

**Option A: Use Azure Portal**
1. Go to **Azure Portal** → **Key Vaults** → **Your Key Vault**
2. Go to **Secrets** → **Generate/Import**
3. Add these secrets:
   - `YAHOO-CLIENT-ID`: Your Yahoo Fantasy API client ID
   - `YAHOO-CLIENT-SECRET`: Your Yahoo Fantasy API client secret
   - `GOOGLE-CLIENT-ID`: Your Google OAuth client ID
   - `GOOGLE-CLIENT-SECRET`: Your Google OAuth client secret
   - `OPENAI-API-KEY`: Your OpenAI API key (if using)

**Option B: Use Azure CLI**
```powershell
# Add secrets via CLI (replace with your actual values)
az keyvault secret set --vault-name $KEY_VAULT_NAME --name "YAHOO-CLIENT-ID" --value "your-yahoo-client-id"
az keyvault secret set --vault-name $KEY_VAULT_NAME --name "YAHOO-CLIENT-SECRET" --value "your-yahoo-client-secret"
az keyvault secret set --vault-name $KEY_VAULT_NAME --name "GOOGLE-CLIENT-ID" --value "your-google-client-id"
az keyvault secret set --vault-name $KEY_VAULT_NAME --name "GOOGLE-CLIENT-SECRET" --value "your-google-client-secret"
az keyvault secret set --vault-name $KEY_VAULT_NAME --name "OPENAI-API-KEY" --value "your-openai-api-key"
```

## Step 3: Enable Managed Identity and Assign Roles

### 3.1 Enable Managed Identity for Function App

```powershell
# Enable system-assigned managed identity
az functionapp identity assign `
  --resource-group $RESOURCE_GROUP `
  --name $FUNCTION_APP

# Get the principal ID
$PRINCIPAL_ID = az functionapp identity show `
  --resource-group $RESOURCE_GROUP `
  --name $FUNCTION_APP `
  --query principalId -o tsv
```

### 3.2 Assign Cosmos DB Role

```powershell
# Get Cosmos DB resource ID
$COSMOS_ID = az cosmosdb show `
  --resource-group $RESOURCE_GROUP `
  --name $COSMOS_ACCOUNT `
  --query id -o tsv

# Assign Cosmos DB Data Contributor role
az role assignment create `
  --assignee $PRINCIPAL_ID `
  --role "Cosmos DB Built-in Data Contributor" `
  --scope $COSMOS_ID
```

## Step 4: Deploy Function App Code

### 4.1 Install Azure Functions Core Tools

```powershell
# Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4 --unsafe-perm true
```

### 4.2 Deploy Function App

```powershell
# Deploy Function App
func azure functionapp publish $FUNCTION_APP --python
```

## Step 5: Configure Azure AD Authentication

### 5.1 Create Azure AD App Registration

```powershell
# Create app registration
$APP_REGISTRATION = az ad app create `
  --display-name "Fantasy Helper Admin" `
  --sign-in-audience AzureADMyOrg

# Extract client ID
$CLIENT_ID = ($APP_REGISTRATION | ConvertFrom-Json).appId
```

### 5.2 Configure App Registration in Azure Portal

1. Go to **Azure Portal** → **Azure Active Directory** → **App registrations**
2. Find your app → **Authentication**
3. Add platform: **Single-page application**
4. Add redirect URI: `https://$SWA_NAME.azurestaticapps.net/.auth/login/aad/callback`
5. Enable **Access tokens** and **ID tokens**
6. Save configuration

### 5.3 Create App Roles

1. In your app registration → **App roles**
2. Click **Create app role**
3. **Display name**: `Admin`
4. **Allowed member types**: `Users/Groups`
5. **Value**: `admin`
6. **Description**: `Fantasy Helper Administrator`
7. Save

### 5.4 Assign Roles to Users

1. Go to **Azure AD** → **Enterprise applications**
2. Find your app → **Users and groups**
3. Add user/group and assign **Admin** role

## Step 6: Configure Static Web App

### 6.1 Update staticwebapp.config.json

Create or update the `staticwebapp.config.json` file in your repository:

```json
{
  "navigationFallback": {
    "rewrite": "/admin/index.html"
  },
  "auth": {
    "rolesSource": "token",
    "identityProviders": {
      "azureActiveDirectory": {
        "registration": {
          "openIdIssuer": "https://login.microsoftonline.com/<YOUR-TENANT-ID>/v2.0",
          "clientIdSettingName": "SWA_AAD_CLIENT_ID"
        }
      }
    }
  },
  "routes": [
    {
      "route": "/admin/*",
      "allowedRoles": ["admin"]
    },
    {
      "route": "/api/admin/*",
      "allowedRoles": ["admin"]
    },
    {
      "route": "/api/auth/*",
      "allowedRoles": ["anonymous"]
    },
    {
      "route": "/api/league/*",
      "allowedRoles": ["admin"]
    }
  ]
}
```

### 6.2 Configure Static Web App Settings

```powershell
# Get tenant ID
$TENANT_ID = az account show --query tenantId -o tsv

# Configure SWA settings
az staticwebapp appsettings set `
  --name $SWA_NAME `
  --setting-names `
    SWA_AAD_CLIENT_ID="$CLIENT_ID" `
    SWA_AAD_TENANT_ID="$TENANT_ID"
```

## Step 7: Set Up OAuth Providers

### 7.1 Yahoo Fantasy API Setup

1. Go to https://developer.yahoo.com/fantasysports/
2. Create new app
3. Set redirect URI: `https://$FUNCTION_APP.azurewebsites.net/api/auth/yahoo/callback`
4. Note Client ID and Secret

### 7.2 Google Gmail API Setup

1. Go to https://console.developers.google.com/
2. Create new project
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Set redirect URI: `https://$FUNCTION_APP.azurewebsites.net/api/auth/google/callback`
6. Note Client ID and Secret

### 7.3 Add OAuth Credentials to Key Vault

**If you're using Key Vault (recommended):**
```powershell
# Add OAuth credentials to Key Vault
az keyvault secret set --vault-name $KEY_VAULT_NAME --name "YAHOO-CLIENT-ID" --value "<your-yahoo-client-id>"
az keyvault secret set --vault-name $KEY_VAULT_NAME --name "YAHOO-CLIENT-SECRET" --value "<your-yahoo-client-secret>"
az keyvault secret set --vault-name $KEY_VAULT_NAME --name "GOOGLE-CLIENT-ID" --value "<your-google-client-id>"
az keyvault secret set --vault-name $KEY_VAULT_NAME --name "GOOGLE-CLIENT-SECRET" --value "<your-google-client-secret>"
az keyvault secret set --vault-name $KEY_VAULT_NAME --name "OPENAI-API-KEY" --value "<your-openai-key-if-using>"
```

**Alternative: Direct Function App Settings (less secure)**
```powershell
# Update Function App with OAuth credentials directly (not recommended for production)
az functionapp config appsettings set `
  --resource-group $RESOURCE_GROUP `
  --name $FUNCTION_APP `
  --settings `
    YAHOO_CLIENT_ID="<your-yahoo-client-id>" `
    YAHOO_CLIENT_SECRET="<your-yahoo-client-secret>" `
    GOOGLE_CLIENT_ID="<your-google-client-id>" `
    GOOGLE_CLIENT_SECRET="<your-google-client-secret>" `
    OPENAI_API_KEY="<your-openai-key-if-using>"
```

## Step 8: Test Your Deployment

### 8.1 Test Authentication Endpoints

```powershell
# Test Yahoo OAuth
Invoke-WebRequest -Uri "https://$FUNCTION_APP.azurewebsites.net/api/auth/yahoo/login"

# Test Google OAuth
Invoke-WebRequest -Uri "https://$FUNCTION_APP.azurewebsites.net/api/auth/google/login"
```

### 8.2 Test Admin UI

1. Navigate to `https://$SWA_NAME.azurestaticapps.net/admin`
2. Sign in with Azure AD account that has `admin` role
3. Test adding a league and manager
4. Test the run-now functionality

### 8.3 Configure API Keys via Admin Interface

1. **Navigate to Admin Dashboard**: Go to `https://$SWA_NAME.azurestaticapps.net/admin`
2. **Sign in with Azure AD** (admin role required)
3. **Go to Configuration Tab**: Click on the "Configuration" tab
4. **Add your API credentials**:
   - Yahoo Fantasy Client ID and Secret
   - Google OAuth Client ID and Secret  
   - OpenAI API Key (optional)
5. **Save Configuration**: Click "Save Configuration"

The admin interface will automatically:
- Store secrets in Key Vault (if enabled)
- Update Function App settings
- Show configuration status
- Provide OAuth setup instructions

### **Step 4: Test Your Configuration**

1. **Use the built-in test functionality:**
   - **Test Yahoo OAuth** - Validates Yahoo Fantasy credentials
   - **Test Google OAuth** - Validates Google Gmail credentials  
   - **Test OpenAI API** - Validates OpenAI API key (if configured)
   - **Test All Configuration** - Runs all tests at once

2. **Test results show:**
   - ✅ **Working** - Credentials are valid and functional
   - ❌ **Failed** - Credentials need to be fixed
   - ⚠️ **Not Configured** - Optional credentials not set

3. **Real-time feedback:**
   - Immediate validation of API keys
   - Clear error messages for troubleshooting
   - Status indicators for each service

### 8.4 Test API Endpoints

```powershell
# Test league sync (replace <LEAGUE_ID> with actual league ID)
Invoke-WebRequest -Uri "https://$FUNCTION_APP.azurewebsites.net/api/league/<LEAGUE_ID>/sync" -Method POST

# Test admin endpoints (requires authentication)
Invoke-WebRequest -Uri "https://$FUNCTION_APP.azurewebsites.net/api/admin/league"

# Test configuration endpoint
Invoke-WebRequest -Uri "https://$FUNCTION_APP.azurewebsites.net/api/admin/config"
```

## Step 9: Set Up GitHub Actions (Optional)

### 9.1 Configure OIDC Authentication

1. **Create Azure AD App Registration for GitHub Actions:**
   ```powershell
   $GITHUB_APP = az ad app create --display-name "Fantasy Helper GitHub Actions"
   $GITHUB_CLIENT_ID = ($GITHUB_APP | ConvertFrom-Json).appId
   ```

2. **Create Federated Credential:**
   - Go to Azure Portal → Azure Active Directory → App registrations
   - Find your GitHub Actions app → Certificates & secrets → Federated credentials
   - Add credential:
     - **Federated credential scenario**: GitHub Actions deploying Azure resources
     - **Organization**: `DaveOchoa` (or your GitHub org)
     - **Repository**: `FantasySportsHelper`
     - **Entity type**: Branch
     - **Branch name**: `main`
     - **Name**: `main-branch`

3. **Set Repository Secrets:**
   - Go to GitHub repository → Settings → Secrets and variables → Actions
   - Add secrets:
     - `AZURE_SUBSCRIPTION_ID`: Your Azure subscription ID
     - `AZURE_TENANT_ID`: Your Azure AD tenant ID
     - `AZURE_CLIENT_ID`: The GitHub Actions app registration client ID

4. **Set Repository Variables:**
   - Add variables:
     - `RESOURCE_GROUP`: $RESOURCE_GROUP
     - `FUNCTION_APP_NAME`: $FUNCTION_APP
     - `SWA_NAME`: $SWA_NAME

## Step 10: Production Monitoring

### 10.1 Enable Application Insights

```powershell
# Create Application Insights
az monitor app-insights component create `
  --resource-group $RESOURCE_GROUP `
  --app "$FUNCTION_APP-insights" `
  --location $LOCATION `
  --kind web

# Get instrumentation key
$INSTRUMENTATION_KEY = az monitor app-insights component show `
  --resource-group $RESOURCE_GROUP `
  --app "$FUNCTION_APP-insights" `
  --query instrumentationKey -o tsv

# Configure Function App with Application Insights
az functionapp config appsettings set `
  --resource-group $RESOURCE_GROUP `
  --name $FUNCTION_APP `
  --settings `
    APPINSIGHTS_INSTRUMENTATIONKEY="$INSTRUMENTATION_KEY"
```

## Step 11: Save Your Configuration

### 11.1 Export Configuration

```powershell
# Export all settings for backup
az functionapp config appsettings list `
  --resource-group $RESOURCE_GROUP `
  --name $FUNCTION_APP `
  --output json > function-app-settings.json

# Save resource names
@"
RESOURCE_GROUP=$RESOURCE_GROUP
FUNCTION_APP=$FUNCTION_APP
SWA_NAME=$SWA_NAME
COSMOS_ACCOUNT=$COSMOS_ACCOUNT
STORAGE_ACCOUNT=$STORAGE_ACCOUNT
CLIENT_ID=$CLIENT_ID
"@ | Out-File -FilePath "deployment-config.txt"
```

## Troubleshooting

### Common Issues

1. **Authentication fails**: Check Azure AD app registration redirect URIs
2. **Cosmos DB access denied**: Verify managed identity role assignment
3. **OAuth redirect errors**: Ensure redirect URIs match exactly
4. **Function timeouts**: Check Cosmos DB connection strings

### Useful Commands

```powershell
# Check Function App logs
az functionapp logs tail --resource-group $RESOURCE_GROUP --name $FUNCTION_APP

# Test Function App locally
func start --python

# Check Cosmos DB connectivity
az cosmosdb check-name-exists --name $COSMOS_ACCOUNT
```

## Cost Estimation

### Free Tier Benefits
- **Function App**: 1 million requests per month free
- **Cosmos DB**: 25 RU/s throughput + 25 GB storage per month free
- **Static Web App**: 100 GB bandwidth per month free
- **Storage Account**: 5 GB storage per month free

**Total**: ~$0/month for small usage (100% free tier)

## Next Steps

1. **Test thoroughly** with your Yahoo Fantasy league
2. **Set up monitoring** and alerts
3. **Configure backup** strategies
4. **Train users** on the admin interface
5. **Schedule regular** maintenance windows

Your Fantasy Sports Helper is now deployed and ready for production use! 🚀

## Quick Reference

### Your Resource Names
- **Resource Group**: `FSH-NHL`
- **Function App**: `fantasyhelperfunctions[random]`
- **Static Web App**: `fantasyhelperadmin[random]`
- **Cosmos DB**: `fantasyhelpercosmos[random]`
- **Storage Account**: `fantasyhelperstorage[random]`

### Important URLs
- **Function App**: `https://[FUNCTION_APP].azurewebsites.net`
- **Admin Dashboard**: `https://[SWA_NAME].azurestaticapps.net/admin`
- **OAuth Callbacks**: 
  - Yahoo: `https://[FUNCTION_APP].azurewebsites.net/api/auth/yahoo/callback`
  - Google: `https://[FUNCTION_APP].azurewebsites.net/api/auth/google/callback`
