# Template Deployment Guide - Fantasy Sports Helper

Complete guide for deploying the Fantasy Sports Helper using the ARM template with the new configuration interface.

## 🚀 **Template Deployment Options**

### **Option 1: Deploy with Key Vault (Recommended for Production)**

```powershell
# Deploy template with Key Vault enabled
az deployment group create `
  --resource-group "FSH-NHL" `
  --template-file "infra/azuredeploy.json" `
  --parameters enableKeyVault=true
```

**What gets deployed:**
- ✅ **Resource Group** with unique naming
- ✅ **Cosmos DB** (serverless) for data storage
- ✅ **Function App** (Python 3.10, Linux Consumption)
- ✅ **Static Web App** for admin dashboard
- ✅ **Key Vault** for secure secret management
- ✅ **Storage Account** for Function App runtime
- ✅ **Role Assignments** for Key Vault access

### **Option 2: Deploy without Key Vault (Free Tier)**

```powershell
# Deploy template without Key Vault (default)
az deployment group create `
  --resource-group "FSH-NHL" `
  --template-file "infra/azuredeploy.json"
```

**What gets deployed:**
- ✅ **Resource Group** with unique naming
- ✅ **Cosmos DB** (serverless) for data storage
- ✅ **Function App** (Python 3.10, Linux Consumption)
- ✅ **Static Web App** for admin dashboard
- ✅ **Storage Account** for Function App runtime
- ❌ **No Key Vault** (saves costs)

## 🔧 **Post-Deployment Configuration**

### **Step 1: Access Admin Dashboard**

1. **Get your Static Web App URL:**
   ```powershell
   # Get the Static Web App URL
   $SWA_URL = az staticwebapp show --name "your-swa-name" --resource-group "FSH-NHL" --query "defaultHostname" -o tsv
   echo "Admin Dashboard: https://$SWA_URL/admin"
   ```

2. **Navigate to admin dashboard** and sign in with Azure AD

### **Step 2: Configure API Keys**

1. **Go to Configuration tab** in the admin interface
2. **Add your OAuth credentials:**
   - Yahoo Fantasy Client ID & Secret
   - Google OAuth Client ID & Secret
   - OpenAI API Key (optional)
3. **Click "Save Configuration"**

**The system automatically:**
- ✅ **Stores secrets in Key Vault** (if enabled)
- ✅ **Updates Function App settings** (if no Key Vault)
- ✅ **Shows configuration status**
- ✅ **Provides OAuth setup instructions**

### **Step 3: Test Your Configuration**

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

### **Step 3: Set Up OAuth Providers**

#### **Yahoo Fantasy Setup:**
1. Go to [Yahoo Developer Console](https://developer.yahoo.com/fantasysports/)
2. Create new application
3. Set redirect URI to: `https://your-function-app.azurewebsites.net/api/auth/yahoo/callback`
4. Copy Client ID and Secret to admin interface

#### **Google Gmail Setup:**
1. Go to [Google Cloud Console](https://console.developers.google.com/)
2. Create new project or select existing
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Set redirect URI to: `https://your-function-app.azurewebsites.net/api/auth/google/callback`
6. Copy Client ID and Secret to admin interface

## 🔐 **Key Vault vs No Key Vault Comparison**

| Feature | With Key Vault | Without Key Vault |
|---------|----------------|-------------------|
| **Security** | ✅ Enterprise-grade | ⚠️ Basic (Function App settings) |
| **Cost** | 💰 ~$0.03/10k operations | ✅ Free |
| **Admin Interface** | ✅ Full configuration | ⚠️ Manual Azure Portal |
| **Secret Rotation** | ✅ Easy via admin interface | ❌ Manual process |
| **Audit Trail** | ✅ Key Vault logs | ❌ No audit trail |
| **Best For** | Production, Enterprise | Development, Testing |

## 🎯 **Template Configuration Logic**

The template uses smart conditional logic:

```json
{
  "name": "YAHOO_CLIENT_ID",
  "value": "[if(parameters('enableKeyVault'), 
    concat('@Microsoft.KeyVault(SecretUri=https://', variables('keyVaultName'), '.vault.azure.net/secrets/YAHOO-CLIENT-ID/)'), 
    '')]"
}
```

**This means:**
- **If Key Vault enabled**: Uses `@Microsoft.KeyVault(SecretUri=...)` references
- **If Key Vault disabled**: Uses empty strings `''`

## 🚀 **Complete Deployment Workflow**

### **1. Deploy Infrastructure**
```powershell
# Choose your deployment option
az deployment group create `
  --resource-group "FSH-NHL" `
  --template-file "infra/azuredeploy.json" `
  --parameters enableKeyVault=true  # or false for free tier
```

### **2. Configure Azure AD Authentication**
```powershell
# Get Static Web App name from deployment output
$SWA_NAME = "your-swa-name"

# Configure Azure AD app registration
az staticwebapp appsettings set `
  --name $SWA_NAME `
  --setting-names `
    SWA_AAD_CLIENT_ID="your-client-id" `
    SWA_AAD_TENANT_ID="your-tenant-id"
```

### **3. Access Admin Interface**
1. Go to `https://your-swa.azurestaticapps.net/admin`
2. Sign in with Azure AD (admin role required)
3. Configure API keys in the Configuration tab
4. Test OAuth flows

### **4. Generate Reports (Optional)**

1. **Upload League Logo** (Optional but recommended):
   - Go to the Generate Reports tab
   - Upload your league logo (PNG/JPG, max 2MB, 300x100px recommended)
   - Logo will appear on all reports and emails

2. **Generate Professional Reports:**
   - Select league ID and week
   - Choose format: **PDF (Professional)** or HTML (Web View)
   - Choose report options (rosters, schedule, stats, guidance)
   - Set custom title
   - Generate reports for all team managers

3. **Report Features:**
   - **Centered logo header** (if uploaded)
   - **Team name prominently displayed**
   - **Fantasy recommendations and guidance**
   - **Professional PDF formatting** for printing
   - **One page per team** for easy distribution

**Perfect for:**
- 📄 **Monday morning distribution** - Print reports for all managers
- 🖨️ **Physical handouts** - One page per team manager
- 📊 **League meetings** - Share insights with all managers
- 🎯 **Getting started** - Test the system before email automation
- 📧 **Email consistency** - Same formatting as automated emails

### **5. Test Your Setup**
```powershell
# Test authentication endpoints
curl "https://your-function-app.azurewebsites.net/api/auth/yahoo/login"
curl "https://your-function-app.azurewebsites.net/api/auth/google/login"

# Test admin endpoints
curl "https://your-function-app.azurewebsites.net/api/admin/config"
```

## 🔧 **Troubleshooting Template Deployment**

### **Common Issues:**

1. **Key Vault Access Denied**
   ```powershell
   # Check role assignments
   az role assignment list --scope "/subscriptions/your-sub-id/resourceGroups/FSH-NHL/providers/Microsoft.KeyVault/vaults/your-keyvault"
   ```

2. **Function App Can't Access Key Vault**
   ```powershell
   # Reassign Key Vault access
   az role assignment create `
     --assignee $FUNCTION_PRINCIPAL_ID `
     --role "Key Vault Secrets User" `
     --scope $KEY_VAULT_ID
   ```

3. **Admin Interface Not Loading**
   - Check Azure AD app registration
   - Verify redirect URIs
   - Ensure user has admin role

### **Useful Commands:**

```powershell
# Check deployment status
az deployment group show --resource-group "FSH-NHL" --name "your-deployment-name"

# Get Function App settings
az functionapp config appsettings list --resource-group "FSH-NHL" --name "your-function-app"

# Check Key Vault secrets
az keyvault secret list --vault-name "your-keyvault"
```

## 💰 **Cost Estimation**

### **With Key Vault (Production):**
- **Function App**: Free tier (1M requests/month)
- **Cosmos DB**: Free tier (25 RU/s, 25 GB storage/month)
- **Static Web App**: Free tier (100GB bandwidth/month)
- **Storage Account**: Free tier (5GB/month)
- **Key Vault**: ~$0.03 per 10,000 operations
- **Total**: ~$0-5/month depending on usage

### **Without Key Vault (Free Tier):**
- **Function App**: Free tier (1M requests/month)
- **Cosmos DB**: Free tier (25 RU/s, 25 GB storage/month)
- **Static Web App**: Free tier (100GB bandwidth/month)
- **Storage Account**: Free tier (5GB/month)
- **Total**: ~$0/month (100% free tier)

## 🎯 **Recommendations**

### **For Development/Testing:**
- Use template without Key Vault
- Configure secrets manually in Function App settings
- Focus on functionality over security

### **For Production:**
- Use template with Key Vault enabled
- Use admin interface for configuration
- Implement proper monitoring and backup

## 🚀 **Next Steps After Deployment**

1. **Test OAuth flows** with your Yahoo Fantasy and Google accounts
2. **Add your first league** via the admin interface
3. **Configure managers** and email mappings
4. **Test the guidance system** with the "Test Run" feature
5. **Set up monitoring** and alerts for production use

Your Fantasy Sports Helper is now deployed and ready for configuration! 🏒
