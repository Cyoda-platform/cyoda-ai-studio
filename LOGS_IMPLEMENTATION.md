# Environment Logs Access Implementation

This document describes the implementation of ELK (Elasticsearch) logs access for user environments.

## Overview

Users can now generate API keys and access their environment logs through the UI. The implementation includes:

1. **Backend API** (cyoda-ai-studio) - API key generation and log search endpoints
2. **Frontend UI** (ai-assistant-ui-react) - API key management and logs viewer interface

## Backend Implementation

### Files Modified/Created

#### 1. `/application/routes/logs.py` (NEW)
Contains three main endpoints:

- **POST `/api/v1/logs/api-key`** - Generate ELK API key
  - Requires authentication (JWT token)
  - Creates a user-specific API key with read-only access to their org's logs
  - API keys are valid for 1 year
  - Each user can only have one active key (generating new one invalidates the old)

- **POST `/api/v1/logs/search`** - Search logs
  - Requires authentication + X-API-Key header
  - Proxies requests to Elasticsearch
  - Automatically filters logs by org_id for security
  - Supports full Elasticsearch Query DSL

- **GET `/api/v1/logs/health`** - Check ELK cluster health
  - Requires authentication
  - Returns cluster status

#### 2. `/application/routes/__init__.py`
- Added `logs_bp` import and export

#### 3. `/application/app.py`
- Registered `logs_bp` blueprint

#### 4. `/.env.template`
Added ELK configuration variables:
```env
ELK_HOST=elk.kube3.cyoda.org
ELK_USER=
ELK_PASSWORD=
```

### Environment Variables Required

You need to set these in your `.env` file:

```env
ELK_HOST=elk.kube3.cyoda.org
ELK_USER=your_elk_admin_user
ELK_PASSWORD=your_elk_admin_password
```

### Security Features

1. **JWT Authentication** - All endpoints require valid JWT token
2. **Org Isolation** - Users can only access logs for their own organization
3. **Read-Only Access** - Generated API keys only have read permissions
4. **Index Filtering** - Automatic filtering by org_id prevents cross-org access
5. **Rate Limiting** - API key generation limited to 5 requests per 5 minutes

## Frontend Implementation

### Files Modified/Created

#### 1. `/packages/web/src/components/EnvironmentsPanel/LogsViewer.tsx` (NEW)

A comprehensive logs viewer component with:

- **Search & Filtering**
  - Full-text search across log messages
  - Quick filters by log level (Error, Warning, Info, Debug)
  - Advanced Query mode for custom Elasticsearch DSL
  - Configurable page size (20, 50, 100, 200 entries)

- **Log Display**
  - Time-sorted log entries (newest first)
  - Color-coded log levels
  - Click to view full log details
  - Responsive layout

- **Export Functionality**
  - Export logs to JSON file
  - Includes metadata (timestamp, total hits)

- **Log Detail Modal**
  - Full log entry view
  - Formatted JSON display
  - All log fields visible

#### 2. `/packages/web/src/components/EnvironmentsPanel/EnvironmentDetails.tsx`

Added "Logs Access" section with:

- **API Key Generation**
  - "Generate API Key" button
  - One-time view modal showing the key
  - Warning that key cannot be viewed again
  - Copy to clipboard functionality

- **Logs Viewer Access**
  - "View Logs" button (appears after key generation)
  - Opens full-screen logs viewer
  - Maintains API key in session state

### User Flow

1. User navigates to Cloud panel → Development Environment
2. In "Logs Access" section, clicks "Generate API Key"
3. Modal appears showing the API key with warning
4. User copies and saves the API key securely
5. User clicks "View Logs" to open the logs viewer
6. User can search, filter, and export logs
7. If user generates a new key, the old one is invalidated

## API Examples

### Generate API Key

```bash
curl -X POST "https://your-api.com/api/v1/logs/api-key" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "api_key": "ZGpXSTRKb0JKYmhrVHhDeHFZRGQ6ODlVVG9IYTRURktScXdHRkVCZlBMUQ==",
  "name": "logs-reader-orgid",
  "created": true,
  "message": "API key generated. Save it securely - you won't be able to see it again.",
  "expires_in_days": 365
}
```

### Search Logs

```bash
curl -X POST "https://your-api.com/api/v1/logs/search" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-API-Key: YOUR_ELK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "match": {
        "message": "error"
      }
    },
    "size": 50,
    "sort": [{"@timestamp": {"order": "desc"}}]
  }'
```

## Elasticsearch Query Examples

### Match All Logs
```json
{
  "query": {
    "match_all": {}
  },
  "size": 50
}
```

### Search by Message
```json
{
  "query": {
    "query_string": {
      "query": "error OR exception",
      "default_field": "message"
    }
  }
}
```

### Filter by Level
```json
{
  "query": {
    "bool": {
      "must": [{"match_all": {}}],
      "filter": [
        {"term": {"level": "ERROR"}}
      ]
    }
  }
}
```

### Time Range Query
```json
{
  "query": {
    "bool": {
      "filter": [
        {
          "range": {
            "@timestamp": {
              "gte": "2025-12-01T00:00:00Z",
              "lte": "2025-12-02T00:00:00Z"
            }
          }
        }
      ]
    }
  }
}
```

## Testing

### Backend Testing

1. Set ELK credentials in `.env`
2. Start the backend: `python -m application.app`
3. Test API key generation:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/logs/api-key" \
     -H "Authorization: Bearer YOUR_TEST_TOKEN"
   ```

### Frontend Testing

1. Ensure backend is running
2. Start frontend: `npm run dev`
3. Navigate to Cloud panel → Development environment
4. Click "Generate API Key"
5. Click "View Logs"
6. Test search and filtering

## Troubleshooting

### "ELK configuration incomplete" Error
- Check that `ELK_HOST`, `ELK_USER`, and `ELK_PASSWORD` are set in `.env`

### "Failed to generate API key" Error
- Verify ELK credentials are correct
- Check that ELK host is reachable
- Ensure ELK user has permission to create API keys

### "Search failed" Error
- Verify API key is valid
- Check that logs index exists in Elasticsearch
- Ensure org_id field is present in log documents

### No logs appearing
- Check that logs are being written to Elasticsearch
- Verify index pattern matches (logs-{org_id}*)
- Ensure org_id in logs matches user's org_id

## Security Considerations

1. **API Key Storage** - Users must save keys securely; they cannot be retrieved after generation
2. **HTTPS Only** - All communication with ELK must use HTTPS
3. **Org Isolation** - Backend enforces org_id filtering; never trust frontend filtering alone
4. **Rate Limiting** - Prevents API key generation abuse
5. **Token Expiration** - API keys expire after 1 year

## Future Enhancements

- [ ] API key management (list, revoke keys)
- [ ] Multiple API keys per user
- [ ] Log aggregations and visualizations
- [ ] Saved search queries
- [ ] Real-time log streaming
- [ ] Log alerts and notifications
- [ ] Export to CSV format
- [ ] Time range picker in UI
