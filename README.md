
# Fantasy Sports Helper — Production Ready

Serverless Azure project pulling Yahoo Fantasy NHL data, joining NHL schedules, computing league-specific guidance, and delivering via Gmail with a comprehensive admin interface.

## Features
- **League-Aware Guidance**: Recommendations based on your league's scoring settings (G, A, SOG, HIT, BLK, etc.)
- **Schedule Intelligence**: Back-to-back game detection and game volume analysis
- **OAuth Integration**: Yahoo Fantasy and Google Gmail authentication
- **Admin Dashboard**: Complete web interface for managing leagues, managers, and testing
- **Automated Delivery**: Nightly job orchestrates sync → guidance → email
- **Extensible Design**: Ready for ESPN/NFL expansion
- **Production Security**: Azure AD authentication with role-based access control

## Quick Start

### 1. Deploy to Azure (Automated)
```bash
# Windows PowerShell
.\deploy.ps1

# Linux/Mac
./deploy.sh
```

### 2. Configure OAuth Applications
- **Yahoo**: Create app at https://developer.yahoo.com/fantasysports/
- **Google**: Create project at https://console.developers.google.com/
- Set redirect URIs to your deployed Function App URLs

### 3. Access Admin Dashboard
1. Navigate to your Static Web App admin URL
2. Sign in with Azure AD (admin role required)
3. Use the web interface to:
   - Add leagues and managers
   - Test the system with email override
   - Monitor guidance runs

### 4. Authentication Flow
```bash
# Authenticate with Yahoo
curl https://your-function-app.azurewebsites.net/api/auth/yahoo/login

# Authenticate with Google  
curl https://your-function-app.azurewebsites.net/api/auth/google/login
```

## Admin Dashboard

The system includes a comprehensive web-based admin interface with:

### **Leagues Management**
- Add new leagues with sport and provider selection
- Sync league data (teams, rosters, scoring settings)
- View league details and current week information

### **Managers Management**
- Map team IDs to email addresses
- View all configured managers
- Update manager information

### **Test & Monitoring**
- Test run functionality with email override
- Real-time guidance generation
- System logs and activity monitoring

### **Security**
- Azure AD authentication required
- Role-based access control (admin role)
- Secure OAuth token management

## API Endpoints

### Authentication
- `GET /api/auth/yahoo/login` — Start Yahoo OAuth
- `GET /api/auth/yahoo/callback` — Yahoo OAuth callback
- `GET /api/auth/google/login` — Start Google OAuth  
- `GET /api/auth/google/callback` — Google OAuth callback

### League Management
- `POST /api/league/{leagueId}/sync` — Sync league data and settings
- `POST /api/league/{leagueId}/send?teamId={teamId}&week={week}` — Send guidance

### Admin (Protected)
- `POST /api/admin/league` — Create/update league
- `POST /api/admin/manager` — Map team to email
- `GET /api/admin/league/{leagueId}` — Get league summary
- `POST /api/admin/run-now` — Test run with email override

### Automation
- Timer trigger runs nightly at 3 AM UTC

## Architecture

### Data Model (Cosmos DB)
- `leagues` — League settings and scoring rules
- `teams` — Team info and managers
- `rosters` — Player rosters by week
- `schedules` — NHL team schedules (cached)
- `managers` — Team-to-email mappings
- `oauthTokens` — Yahoo/Google OAuth tokens
- `guidanceRuns` — Generated guidance history

### Scoring-Aware Guidance
The system fetches your league's scoring categories and tailors recommendations:
- **Goals/Assists leagues**: "More games = more scoring opportunities"
- **Shots leagues**: "More games = more shots on goal"  
- **Hits leagues**: "More games = more hits"
- **Blocks leagues**: "More games = more blocks"

### Extensibility
- Provider abstraction ready for ESPN
- Sport abstraction ready for NFL
- Delivery channels ready for Slack

## Deployment

### Local Development
```bash
pip install -r requirements.txt
func start
```

### Azure Deployment

#### Automated Deployment (Recommended)
```bash
# Windows PowerShell
.\deploy.ps1

# Linux/Mac  
./deploy.sh
```

The scripts automatically create:
- ✅ **Resource Group**: `fantasyhelperrg`
- ✅ **Cosmos DB**: `fantasyhelpercosmos` (serverless)
- ✅ **Function App**: `fantasyhelperfunctions`
- ✅ **Static Web App**: `fantasyhelperadmin` (connected to GitHub)
- ✅ **Storage Account**: For Function App runtime
- ✅ **Managed Identity**: Secure Cosmos DB access

#### Manual Deployment
1. **Create Azure Resources**: Cosmos DB, Function App, Static Web App
2. **Configure Authentication**: Azure AD app registration with admin roles
3. **Set OAuth Credentials**: Yahoo Fantasy and Google Gmail API keys
4. **Deploy Code**: Function App and Static Web App
5. **Test System**: Verify all endpoints and authentication

📋 **Complete deployment guide**: See `DEPLOYMENT.md` for step-by-step instructions

## Security

### Authentication & Authorization
- **Azure Static Web Apps**: Role-based access control with Azure AD integration
- **Admin Protection**: All admin endpoints require `admin` role
- **OAuth 2.0**: Yahoo Fantasy and Google Gmail authentication
- **Function Security**: Server-side role validation in all admin functions

### Security Configuration
```json
// staticwebapp.config.json
{
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
    }
  ]
}
```

### Production Security Checklist
- ✅ **Azure AD Integration**: Configure tenant ID and client ID
- ✅ **Role Assignment**: Assign `admin` role to authorized users
- ✅ **HTTPS Only**: All traffic encrypted in transit
- ✅ **Security Headers**: XSS protection, content type validation
- ✅ **Function Authorization**: Server-side role checks
- ✅ **Managed Identity**: Cosmos DB access without stored keys

### Setup Instructions
1. **Configure Azure AD**: Set up app registration with `SWA_AAD_CLIENT_ID`
2. **Assign Roles**: Add users to `admin` role in Azure AD
3. **Deploy**: Static Web App automatically enforces security rules
4. **Test**: Verify unauthorized users cannot access admin functions

### Cost Estimation (West US)
- **Function App (Consumption)**: ~$5-20/month
- **Cosmos DB (Serverless)**: ~$10-50/month
- **Static Web App**: Free tier
- **Storage + Monitoring**: ~$5-15/month
- **Total**: ~$20-90/month depending on usage

### Files Overview
- `deploy.ps1` / `deploy.sh` — Automated Azure deployment scripts
- `DEPLOYMENT.md` — Complete deployment guide
- `admin/index.html` — Admin dashboard interface
- `functions/` — Azure Functions (API endpoints)
- `libs/` — API clients and utilities
- `engine/` — Guidance computation and email templates

See `PRD.md` for detailed security and fallback logic.
