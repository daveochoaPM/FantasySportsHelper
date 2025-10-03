
# PRD — Fantasy Sports Helper Production Requirements

## Security & Authentication
- **Admin UI**: Azure Static Web Apps with role-based access (`admin` role required)
- **Backend**: Azure Functions with function-level keys (Easy Auth recommended for production)
- **Database**: Cosmos DB with Entra RBAC; Function App managed identity for data-plane access
- **OAuth Providers**: 
  - Yahoo Fantasy: `fspt-r` scope for league/roster access
  - Google Gmail: `gmail.send` scope for email delivery
- **Token Storage**: OAuth tokens stored in Cosmos DB with provider-specific partitions

## League Scoring Integration
- **Dynamic Scoring**: Fetch league settings via Yahoo API to understand scoring categories
- **Tailored Guidance**: Recommendations adapt to league type:
  - Goals/Assists leagues: Focus on scoring opportunities
  - Shots leagues: Emphasize shot volume
  - Hits/Blocks leagues: Highlight physical play opportunities
- **Transparency**: All guidance includes `sourceSeason` and `scoringType` for context

## Fallback Logic & Data Quality
- **Current Season Priority**: Use current season data when sample size ≥ threshold
  - Skaters: 8-10 games played minimum
  - Goalies: 5 games started minimum
- **Historical Fallback**: Last season player-vs-team stats when current insufficient
- **Team-Level Fallback**: Team-vs-team profiles as final fallback
- **Blended Approach**: 30% current + 70% prior season until sufficient sample (Thanksgiving cutoff)
- **Transparency**: Every recommendation includes `sourceSeason` and `fallbackReason`

## Extensibility Design
- **Provider Abstraction**: Clean interface for Yahoo/ESPN/NFL providers
- **Sport Flexibility**: NHL-first with NFL expansion path
- **Delivery Channels**: Gmail primary, Slack ready for future
- **Scoring Systems**: Category-based scoring with custom league support

## Production Considerations
- **Error Handling**: Comprehensive logging and graceful degradation
- **Rate Limiting**: Respect Yahoo/Google API limits with retry logic
- **Data Freshness**: Nightly sync with on-demand updates
- **Monitoring**: Application Insights integration for production monitoring
