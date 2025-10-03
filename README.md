
# Fantasy NHL Helper — Production Ready

Serverless Azure project pulling Yahoo Fantasy NHL data, joining NHL schedules, computing league-specific guidance, and delivering via Gmail.

## Features
- **League-Aware Guidance**: Recommendations based on your league's scoring settings (G, A, SOG, HIT, BLK, etc.)
- **Schedule Intelligence**: Back-to-back game detection and game volume analysis
- **OAuth Integration**: Yahoo Fantasy and Gmail authentication
- **Admin Interface**: Test runs with email override for development
- **Automated Delivery**: Nightly job orchestrates sync → guidance → email
- **Extensible Design**: Ready for ESPN/NFL expansion

## Quick Start

### 1. Setup OAuth Applications
- **Yahoo**: Create app at https://developer.yahoo.com/fantasysports/
- **Google**: Create project at https://console.developers.google.com/
- Update `local.settings.json` with client IDs and secrets

### 2. Authentication Flow
```bash
# Authenticate with Yahoo
curl http://localhost:7071/api/auth/yahoo/login

# Authenticate with Google  
curl http://localhost:7071/api/auth/google/login
```

### 3. Configure League
```bash
# Add league
curl -X POST http://localhost:7071/api/admin/league \
  -H "Content-Type: application/json" \
  -d '{"leagueId": "123456", "sport": "nhl", "provider": "yahoo"}'

# Add manager email
curl -X POST http://localhost:7071/api/admin/manager \
  -H "Content-Type: application/json" \
  -d '{"leagueId": "123456", "teamId": "1", "email": "manager@example.com"}'
```

### 4. Test Run
```bash
# Sync league data
curl -X POST http://localhost:7071/api/league/123456/sync

# Test guidance (with email override)
curl -X POST http://localhost:7071/api/admin/run-now \
  -H "Content-Type: application/json" \
  -d '{"leagueId": "123456", "teamId": "1", "emailOverride": "test@example.com"}'
```

## API Endpoints

### Authentication
- `GET /api/auth/yahoo/login` — Start Yahoo OAuth
- `GET /api/auth/yahoo/callback` — Yahoo OAuth callback
- `GET /api/auth/google/login` — Start Google OAuth  
- `GET /api/auth/google/callback` — Google OAuth callback

### League Management
- `POST /api/league/{leagueId}/sync` — Sync league data and settings
- `POST /api/league/{leagueId}/send?teamId={teamId}&week={week}` — Send guidance

### Admin
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

#### Quick Start (Automated)
```bash
# Run the deployment script
./deploy.sh  # Linux/Mac
# or
.\deploy.ps1  # Windows PowerShell
```

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

See `PRD.md` for detailed security and fallback logic.
