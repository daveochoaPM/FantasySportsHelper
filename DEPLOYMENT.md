# Azure Deployment Guide - Fantasy Sports Helper

Complete step-by-step guide to deploy the Fantasy Sports Helper to Azure.

## Deployment Options

### Option 1: One-Click Deploy to Azure (Recommended)

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FDaveOchoa%2FFantasySportsHelper%2Fmain%2Finfra%2Fazuredeploy.json)

This automated deployment provisions all required Azure resources with a single click.

**What gets deployed:**
- Resource Group with unique naming
- Cosmos DB (serverless) for data storage
- Function App (Python 3.10, Linux Consumption)
- Static Web App for admin dashboard
- Key Vault for secure secret management
- Application Insights for monitoring
- Storage Account for Function App runtime

**Post-deployment steps:**
1. Set GitHub repository variables: `RESOURCE_GROUP`, `FUNCTION_APP_NAME`, `SWA_NAME`
2. Add OAuth secrets to Key Vault (Yahoo, Google, OpenAI)
3. Configure Azure AD app registration for Static Web App
4. Set up GitHub Actions OIDC authentication

### Option 2: GitHub Actions Infrastructure Provisioning

Use the manual workflow to deploy infrastructure:

1. Go to **Actions** → **Provision Infrastructure**
2. Click **Run workflow**
3. Fill in parameters:
   - Resource Group Name
   - Azure Region
   - Name Prefix for Resources
   - Azure AD Tenant ID
4. Click **Run workflow**

### Option 3: Manual Deployment (Legacy)

Use the PowerShell/Bash scripts for manual deployment.

## GitHub Actions CI/CD Setup

### Configure OpenID Connect (OIDC) Authentication

1. **Create Azure AD App Registration:**
   ```bash
   # Create app registration
   az ad app create --display-name "Fantasy Helper GitHub Actions"
   
   # Note the Application (client) ID
   CLIENT_ID="<your-client-id>"
   ```

2. **Create Federated Credential:**
   - Go to Azure Portal → Azure Active Directory → App registrations
   - Find your app → Certificates & secrets → Federated credentials
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
     - `AZURE_CLIENT_ID`: The app registration client ID from step 1

4. **Set Repository Variables (after infrastructure deployment):**
   - Go to GitHub repository → Settings → Secrets and variables → Actions
   - Add variables:
     - `RESOURCE_GROUP`: Resource group name from deployment
     - `FUNCTION_APP_NAME`: Function app name from deployment
     - `SWA_NAME`: Static web app name from deployment

### Automatic Deployment Workflow

Once configured, the repository will automatically:
- Deploy Azure Functions on push to `main` branch
- Deploy Static Web App admin interface
- Use OIDC authentication (no stored secrets)

### Manual Infrastructure Provisioning

Use the "Provision Infrastructure" workflow for one-time setup:
1. Go to Actions → Provision Infrastructure
2. Click "Run workflow"
3. Provide required parameters
4. Monitor deployment progress

## Prerequisites

- Azure subscription with contributor access
- Azure CLI installed (`az --version`) (for manual deployment)
- Git configured
- Local development environment set up

## Step 1: Create Azure Resources

### 1.1 Create Resource Group
```bash
# Set variables
RESOURCE_GROUP="fantasyhelperrg"
LOCATION="westus2"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION
```

### 1.2 Create Cosmos DB Account
```bash
# Set variables
COSMOS_ACCOUNT="fantasyhelpercosmos"
DATABASE_NAME="fantasy_helper"

# Create Cosmos DB account
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
  --name $DATABASE_NAME
```

### 1.3 Create Storage Account (for Function App)
```bash
# Set variables
STORAGE_ACCOUNT="fantasyhelperstorage"

# Create storage account
az storage account create \
  --resource-group $RESOURCE_GROUP \
  --name $STORAGE_ACCOUNT \
  --location $LOCATION \
  --sku Standard_LRS
```

### 1.4 Create Function App
```bash
# Set variables
FUNCTION_APP="fantasyhelperfunctions"
PYTHON_VERSION="3.9"

# Create Function App
az functionapp create \
  --resource-group $RESOURCE_GROUP \
  --consumption-plan-location $LOCATION \
  --runtime python \
  --runtime-version $PYTHON_VERSION \
  --functions-version 4 \
  --name $FUNCTION_APP \
  --storage-account $STORAGE_ACCOUNT \
  --os-type Linux
```

### 1.5 Create Static Web App
```bash
# Set variables
SWA_NAME="fantasyhelperadmin"
SWA_SOURCE="https://github.com/DaveOchoa/FantasySportsHelper"

# Create Static Web App
az staticwebapp create \
  --name $SWA_NAME \
  --resource-group $RESOURCE_GROUP \
  --source $SWA_SOURCE \
  --location $LOCATION \
  --branch main \
  --app-location "/admin" \
  --output-location "/admin"
```

## Step 2: Configure Azure AD Authentication

### 2.1 Create Azure AD App Registration
```bash
# Create app registration
az ad app create \
  --display-name "Fantasy Helper Admin" \
  --sign-in-audience AzureADMyOrg

# Note the Application (client) ID from the output
CLIENT_ID="<your-client-id>"
```

### 2.2 Configure App Registration
1. Go to Azure Portal → Azure Active Directory → App registrations
2. Find your app → Authentication
3. Add platform: **Single-page application**
4. Add redirect URI: `https://<your-swa-name>.azurestaticapps.net/.auth/login/aad/callback`
5. Enable **Access tokens** and **ID tokens**
6. Save configuration

### 2.3 Create App Roles
1. In your app registration → App roles
2. Click "Create app role"
3. **Display name**: `Admin`
4. **Allowed member types**: `Users/Groups`
5. **Value**: `admin`
6. **Description**: `Fantasy Helper Administrator`
7. Save

### 2.4 Assign Roles to Users
1. Go to Azure AD → Enterprise applications
2. Find your app → Users and groups
3. Add user/group and assign "Admin" role

## Step 3: Configure Application Settings

### 3.1 Function App Settings
```bash
# Get Cosmos DB connection string
COSMOS_CONNECTION_STRING=$(az cosmosdb keys list \
  --resource-group $RESOURCE_GROUP \
  --name $COSMOS_ACCOUNT \
  --type connection-strings \
  --query 'connectionStrings[0].connectionString' -o tsv)

# Configure Function App settings
az functionapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP \
  --settings \
    COSMOS_ENDPOINT="https://$COSMOS_ACCOUNT.documents.azure.com:443/" \
    COSMOS_KEY="$(az cosmosdb keys list --resource-group $RESOURCE_GROUP --name $COSMOS_ACCOUNT --type keys --query 'primaryMasterKey' -o tsv)" \
    COSMOS_DB="$DATABASE_NAME" \
    FUNCTIONS_WORKER_RUNTIME="python" \
    WEBSITE_RUN_FROM_PACKAGE="1"
```

### 3.2 OAuth Application Settings
```bash
# Configure OAuth settings (replace with your actual values)
az functionapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP \
  --settings \
    YAHOO_CLIENT_ID="<your-yahoo-client-id>" \
    YAHOO_CLIENT_SECRET="<your-yahoo-client-secret>" \
    YAHOO_REDIRECT_URI="https://$FUNCTION_APP.azurewebsites.net/api/auth/yahoo/callback" \
    GOOGLE_CLIENT_ID="<your-google-client-id>" \
    GOOGLE_CLIENT_SECRET="<your-google-client-secret>" \
    GMAIL_REDIRECT_URI="https://$FUNCTION_APP.azurewebsites.net/api/auth/google/callback" \
    OPENAI_API_KEY="<your-openai-key-if-using>"
```

### 3.3 Static Web App Settings
```bash
# Configure SWA settings
az staticwebapp appsettings set \
  --name $SWA_NAME \
  --setting-names \
    SWA_AAD_CLIENT_ID="$CLIENT_ID" \
    SWA_AAD_TENANT_ID="$(az account show --query tenantId -o tsv)"
```

## Step 4: Deploy Code

### 4.1 Deploy Function App
```bash
# Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4 --unsafe-perm true

# Deploy Function App
func azure functionapp publish $FUNCTION_APP --python
```

### 4.2 Deploy Static Web App
```bash
# Deploy admin UI
az staticwebapp appsettings set \
  --name $SWA_NAME \
  --setting-names \
    SWA_AAD_CLIENT_ID="$CLIENT_ID"
```

## Step 5: Configure Managed Identity

### 5.1 Enable Managed Identity for Function App
```bash
# Enable system-assigned managed identity
az functionapp identity assign \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP

# Get the principal ID
PRINCIPAL_ID=$(az functionapp identity show \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP \
  --query principalId -o tsv)
```

### 5.2 Assign Cosmos DB Role
```bash
# Get Cosmos DB resource ID
COSMOS_ID=$(az cosmosdb show \
  --resource-group $RESOURCE_GROUP \
  --name $COSMOS_ACCOUNT \
  --query id -o tsv)

# Assign Cosmos DB Data Contributor role
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Cosmos DB Built-in Data Contributor" \
  --scope $COSMOS_ID
```

## Step 6: Update Configuration Files

### 6.1 Update staticwebapp.config.json
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

### 6.2 Update local.settings.json for Production
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "DefaultEndpointsProtocol=https;AccountName=<STORAGE_ACCOUNT>;AccountKey=<KEY>;EndpointSuffix=core.windows.net",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "COSMOS_ENDPOINT": "https://<COSMOS_ACCOUNT>.documents.azure.com:443/",
    "COSMOS_KEY": "<COSMOS_KEY>",
    "COSMOS_DB": "fantasy_helper",
    "OPENAI_API_KEY": "<OPENAI_KEY>",
    "YAHOO_CLIENT_ID": "<YAHOO_CLIENT_ID>",
    "YAHOO_CLIENT_SECRET": "<YAHOO_CLIENT_SECRET>",
    "YAHOO_REDIRECT_URI": "https://<FUNCTION_APP>.azurewebsites.net/api/auth/yahoo/callback",
    "GOOGLE_CLIENT_ID": "<GOOGLE_CLIENT_ID>",
    "GOOGLE_CLIENT_SECRET": "<GOOGLE_CLIENT_SECRET>",
    "GMAIL_REDIRECT_URI": "https://<FUNCTION_APP>.azurewebsites.net/api/auth/google/callback"
  }
}
```

## Step 7: OAuth Provider Setup

### 7.1 Yahoo Fantasy API Setup
1. Go to https://developer.yahoo.com/fantasysports/
2. Create new app
3. Set redirect URI: `https://<FUNCTION_APP>.azurewebsites.net/api/auth/yahoo/callback`
4. Note Client ID and Secret

### 7.2 Google Gmail API Setup
1. Go to https://console.developers.google.com/
2. Create new project
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Set redirect URI: `https://<FUNCTION_APP>.azurewebsites.net/api/auth/google/callback`
6. Note Client ID and Secret

## Step 8: Test Deployment

### 8.1 Test Authentication
```bash
# Test Yahoo OAuth
curl https://<FUNCTION_APP>.azurewebsites.net/api/auth/yahoo/login

# Test Google OAuth
curl https://<FUNCTION_APP>.azurewebsites.net/api/auth/google/login
```

### 8.2 Test Admin UI
1. Navigate to `https://<SWA_NAME>.azurestaticapps.net/admin`
2. Sign in with Azure AD account that has `admin` role
3. Test adding a league and manager
4. Test the run-now functionality

### 8.3 Test API Endpoints
```bash
# Test league sync
curl -X POST https://<FUNCTION_APP>.azurewebsites.net/api/league/<LEAGUE_ID>/sync

# Test admin endpoints (requires authentication)
curl -X GET https://<FUNCTION_APP>.azurewebsites.net/api/admin/league
```

## Step 9: Production Monitoring

### 9.1 Enable Application Insights
```bash
# Create Application Insights
az monitor app-insights component create \
  --resource-group $RESOURCE_GROUP \
  --app $FUNCTION_APP-insights \
  --location $LOCATION \
  --kind web

# Get instrumentation key
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --resource-group $RESOURCE_GROUP \
  --app $FUNCTION_APP-insights \
  --query instrumentationKey -o tsv)

# Configure Function App with Application Insights
az functionapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP \
  --settings \
    APPINSIGHTS_INSTRUMENTATIONKEY="$INSTRUMENTATION_KEY"
```

### 9.2 Set Up Alerts
```bash
# Create alert for function errors
az monitor metrics alert create \
  --name "Function Errors" \
  --resource-group $RESOURCE_GROUP \
  --scopes "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/sites/$FUNCTION_APP" \
  --condition "count 'exceptions' > 5" \
  --description "Alert when function exceptions exceed 5"
```

## Step 10: Backup and Recovery

### 10.1 Enable Cosmos DB Backup
```bash
# Enable continuous backup
az cosmosdb sql database update \
  --resource-group $RESOURCE_GROUP \
  --account-name $COSMOS_ACCOUNT \
  --name $DATABASE_NAME \
  --enable-continuous-backup true
```

### 10.2 Export Configuration
```bash
# Export all settings for backup
az functionapp config appsettings list \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP \
  --output json > function-app-settings.json
```

## Troubleshooting

### Common Issues
1. **Authentication fails**: Check Azure AD app registration redirect URIs
2. **Cosmos DB access denied**: Verify managed identity role assignment
3. **OAuth redirect errors**: Ensure redirect URIs match exactly
4. **Function timeouts**: Check Cosmos DB connection strings

### Useful Commands
```bash
# Check Function App logs
az functionapp logs tail --resource-group $RESOURCE_GROUP --name $FUNCTION_APP

# Test Function App locally
func start --python

# Check Cosmos DB connectivity
az cosmosdb check-name-exists --name $COSMOS_ACCOUNT
```

## Cost Optimization

### Estimated Monthly Costs (West US)
- **Function App (Consumption)**: ~$5-20/month
- **Cosmos DB (Serverless)**: ~$10-50/month  
- **Static Web App**: Free tier
- **Storage Account**: ~$1-5/month
- **Application Insights**: ~$5-15/month

**Total**: ~$20-90/month depending on usage

## Security Checklist

- ✅ Azure AD authentication configured
- ✅ Admin role assignments completed
- ✅ Managed identity for Cosmos DB
- ✅ HTTPS enforced on all endpoints
- ✅ Security headers configured
- ✅ OAuth redirect URIs secured
- ✅ Function-level authorization implemented

## Next Steps

1. **Test thoroughly** with your Yahoo Fantasy league
2. **Set up monitoring** and alerts
3. **Configure backup** strategies
4. **Train users** on the admin interface
5. **Schedule regular** maintenance windows

Your Fantasy Sports Helper is now deployed and ready for production use! 🚀
