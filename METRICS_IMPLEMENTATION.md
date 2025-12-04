# Environment Metrics Access Implementation (Prometheus & Grafana)

This document describes the implementation of Prometheus metrics and Grafana dashboard access for user environments with namespace-based isolation.

## Overview

Users can now generate Grafana service account tokens and access metrics dashboards specific to their Kubernetes namespace. The implementation includes:

1. **Backend API** (cyoda-ai-studio) - Grafana token generation and Prometheus query proxy
2. **Frontend UI** (ai-assistant-ui-react) - Token management and Grafana access
3. **Namespace Isolation** - Automatic filtering of metrics by user's Kubernetes namespace

## Architecture

```
┌──────────────┐      ┌──────────────────┐      ┌──────────────┐
│              │      │                  │      │              │
│   Frontend   │─────▶│  AI Studio API   │─────▶│   Grafana    │
│     (UI)     │      │   (Backend)      │      │   (Viewer)   │
│              │      │                  │      │              │
└──────────────┘      └────────┬─────────┘      └──────────────┘
                               │
                               │
                               ▼
                      ┌──────────────────┐
                      │                  │
                      │   Prometheus     │
                      │  (Metrics DB)    │
                      │                  │
                      └──────────────────┘
```

### Data Flow

1. User requests Grafana token via UI
2. Backend creates Grafana service account with Viewer role
3. Backend generates service account token (1-year validity)
4. User receives token and can:
   - Open Grafana in browser
   - Access pre-configured dashboards
   - Query metrics filtered by their namespace

## Backend Implementation

### Files Modified/Created

#### 1. `/application/routes/metrics.py` (NEW)

Contains four main endpoints:

##### **POST `/api/v1/metrics/grafana-token`** - Generate Grafana Service Account Token
- Requires authentication (JWT token)
- Creates or reuses service account named `metrics-{org_id}`
- Generates long-lived token (1 year)
- Returns token, Grafana URL, and namespace info

##### **POST `/api/v1/metrics/query`** - Query Prometheus (Instant)
- Requires authentication
- Proxies PromQL queries to Prometheus
- Automatically adds namespace filter: `{namespace="client-{org_id}"}`
- Returns Prometheus instant query results

##### **POST `/api/v1/metrics/query_range`** - Query Prometheus (Range)
- Requires authentication
- Queries metrics over time range
- Automatic namespace filtering
- Returns time-series data

##### **GET `/api/v1/metrics/health`** - Health Check
- Checks Grafana API accessibility
- Checks Prometheus API accessibility
- Returns status of both services

#### 2. `/application/routes/__init__.py`
- Added `metrics_bp` import and export

#### 3. `/application/app.py`
- Registered `metrics_bp` blueprint

#### 4. `/.env.template`
Added Grafana and Prometheus configuration:
```env
GRAFANA_HOST=grafana1.kube3.cyoda.org
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=

PROMETHEUS_HOST=prometheus1.kube3.cyoda.org
PROMETHEUS_USER=
PROMETHEUS_PASSWORD=
```

### Environment Variables Required

Set these in your `.env` file:

```env
# Grafana Configuration
GRAFANA_HOST=grafana1.kube3.cyoda.org
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your_grafana_admin_password

# Prometheus Configuration
PROMETHEUS_HOST=prometheus1.kube3.cyoda.org
PROMETHEUS_USER=prometheus_user  # Optional, if basic auth enabled
PROMETHEUS_PASSWORD=prometheus_pass  # Optional
```

### Security Features

1. **JWT Authentication** - All endpoints require valid JWT token
2. **Namespace Isolation** - Metrics automatically filtered by `namespace="client-{org_id}"`
3. **Viewer-Only Access** - Service accounts created with Viewer role (read-only)
4. **Automatic Query Filtering** - PromQL queries augmented with namespace filters
5. **Rate Limiting** - Token generation limited to 5 requests per 5 minutes

### Grafana Service Account Management

The implementation uses Grafana's Service Account API:

```python
# Service account lifecycle
1. Check if service account exists: GET /api/serviceaccounts/search
2. Create if not exists: POST /api/serviceaccounts
3. Generate token: POST /api/serviceaccounts/{id}/tokens
```

**Service Account Naming**: `metrics-{org_id}`
**Token Naming**: `metrics-{org_id}-token`
**Role**: Viewer (read-only)
**Token Validity**: 365 days (31536000 seconds)

### Namespace Filtering Logic

All Prometheus queries are automatically filtered:

```python
# Original query
query = "up"

# Filtered query
query = 'up{namespace="client-alice"}'

# Complex query
query = 'sum(rate(http_requests_total[5m]))'

# Filtered
query = 'sum(rate(http_requests_total{namespace="client-alice"}[5m]))'
```

## Frontend Implementation

### Files Modified

#### `/packages/web/src/components/EnvironmentsPanel/EnvironmentDetails.tsx`

Added "Metrics & Monitoring" section with:

**Token Generation:**
- "Generate Grafana Token" button
- One-time view modal showing token, URL, and namespace
- Copy to clipboard functionality
- Security warning

**Grafana Access:**
- "Open Grafana" button (appears after token generation)
- Opens Grafana in new tab
- Quick access links to common dashboards:
  - Kubernetes Dashboard
  - Application Metrics

**State Management:**
```typescript
const [grafanaToken, setGrafanaToken] = useState<string | null>(null);
const [grafanaUrl, setGrafanaUrl] = useState<string | null>(null);
const [generatingGrafanaToken, setGeneratingGrafanaToken] = useState(false);
```

### User Flow

1. Navigate to Cloud panel → Development Environment
2. Scroll to "Metrics & Monitoring" section
3. Click "Generate Grafana Token"
4. Modal appears with token, Grafana URL, and namespace
5. User copies and saves token securely
6. User clicks "Open Grafana" to access dashboards
7. User can access pre-configured dashboards or create custom queries

## API Examples

### Generate Grafana Token

```bash
curl -X POST "https://your-api.com/api/v1/metrics/grafana-token" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "token": "glsa_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "name": "metrics-alice",
  "service_account_id": 123,
  "grafana_url": "https://grafana1.kube3.cyoda.org",
  "namespace": "client-alice",
  "message": "Token generated. Save it securely - you won't be able to see it again.",
  "expires_in_days": 365
}
```

### Query Prometheus (Instant)

```bash
curl -X POST "https://your-api.com/api/v1/metrics/query" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "up",
    "time": "2025-12-02T12:00:00Z"
  }'
```

Response (Prometheus format):
```json
{
  "status": "success",
  "data": {
    "resultType": "vector",
    "result": [
      {
        "metric": {
          "__name__": "up",
          "instance": "pod-abc",
          "namespace": "client-alice"
        },
        "value": [1733144400, "1"]
      }
    ]
  }
}
```

### Query Prometheus (Range)

```bash
curl -X POST "https://your-api.com/api/v1/metrics/query_range" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "rate(http_requests_total[5m])",
    "start": "2025-12-02T00:00:00Z",
    "end": "2025-12-02T12:00:00Z",
    "step": "1m"
  }'
```

## Prometheus Query Examples

### Basic Metrics

```promql
# All up targets in namespace
up

# CPU usage
container_cpu_usage_seconds_total

# Memory usage
container_memory_usage_bytes

# HTTP request rate
rate(http_requests_total[5m])
```

### Aggregations

```promql
# Total memory across all pods
sum(container_memory_usage_bytes)

# Average CPU by pod
avg(rate(container_cpu_usage_seconds_total[5m])) by (pod)

# Request rate by endpoint
sum(rate(http_requests_total[5m])) by (endpoint)
```

### Advanced Queries

```promql
# P95 request latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Pod restart count
sum(kube_pod_container_status_restarts_total) by (pod)

# Available vs used memory percentage
(1 - sum(container_memory_usage_bytes) / sum(container_spec_memory_limit_bytes)) * 100
```

## Grafana Dashboard Access

### Pre-configured Dashboards

Users have access to these dashboards (namespace-filtered):

| Dashboard | Description | Metrics |
|-----------|-------------|---------|
| Kubernetes Cluster | Pod, deployment, node stats | CPU, Memory, Network, Disk |
| Spring Boot Stats | Application metrics | JVM, HTTP requests, DB connections |
| Node Exporter | Host-level metrics | System resources |
| Blackbox Exporter | Endpoint health | Probe results, SSL certs |

### Using the Token in Grafana

**Option 1: Browser Access (Recommended)**
1. Click "Open Grafana" in UI
2. Grafana opens in new tab
3. Token is automatically used for authentication

**Option 2: API Access**
```bash
curl -H "Authorization: Bearer glsa_xxxx" \
  https://grafana1.kube3.cyoda.org/api/dashboards/home
```

**Option 3: Grafana CLI**
```bash
export GRAFANA_TOKEN="glsa_xxxx"
export GRAFANA_URL="https://grafana1.kube3.cyoda.org"

grafana-cli --homepath=/usr/share/grafana \
  --configOverrides "auth.token=$GRAFANA_TOKEN" \
  dashboards ls
```

## Namespace-Based Metrics Isolation

### How It Works

1. **Automatic Filtering**: Backend adds `namespace="client-{org_id}"` to all queries
2. **Kubernetes Labels**: Prometheus metrics include `namespace` label
3. **Query Rewriting**: PromQL queries are parsed and augmented:

```promql
# User submits
up

# Backend rewrites to
up{namespace="client-alice"}

# User submits
sum(rate(http_requests_total[5m]))

# Backend rewrites to
sum(rate(http_requests_total{namespace="client-alice"}[5m]))
```

### Metrics Available

All Kubernetes metrics with `namespace` label are available:

- `kube_pod_*` - Pod metrics
- `kube_deployment_*` - Deployment metrics
- `container_*` - Container metrics
- `http_*` - HTTP request metrics (if instrumented)
- Custom application metrics (if instrumented with namespace label)

## Testing

### Backend Testing

1. **Set environment variables** in `.env`:
```env
GRAFANA_HOST=grafana1.kube3.cyoda.org
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your_password
PROMETHEUS_HOST=prometheus1.kube3.cyoda.org
```

2. **Start backend**:
```bash
python -m application.app
```

3. **Test token generation**:
```bash
curl -X POST "http://localhost:8000/api/v1/metrics/grafana-token" \
  -H "Authorization: Bearer YOUR_TEST_TOKEN"
```

4. **Test Prometheus query**:
```bash
curl -X POST "http://localhost:8000/api/v1/metrics/query" \
  -H "Authorization: Bearer YOUR_TEST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "up"}'
```

### Frontend Testing

1. Start backend and frontend
2. Navigate to Cloud → Development
3. Click "Generate Grafana Token"
4. Verify token modal appears with token and URL
5. Click "Open Grafana"
6. Verify Grafana opens with dashboard access
7. Try quick access links

## Troubleshooting

### "Grafana configuration incomplete" Error
- Check `GRAFANA_HOST`, `GRAFANA_ADMIN_USER`, and `GRAFANA_ADMIN_PASSWORD` in `.env`
- Verify Grafana admin credentials are correct

### "Failed to create service account" Error
- Ensure Grafana admin user has permission to create service accounts
- Check Grafana logs: `kubectl -n grafana-ns logs deployment/grafana1`
- Verify Grafana API is accessible

### "Query failed" Error (Prometheus)
- Check `PROMETHEUS_HOST` is correct
- Verify Prometheus is accessible
- Check if basic auth credentials are required

### No metrics appearing in Grafana
- Verify namespace exists in Kubernetes
- Check if pods are running: `kubectl -n client-{org_id} get pods`
- Verify Prometheus is scraping the namespace
- Check Prometheus targets: `https://prometheus1.kube3.cyoda.org/targets`

### Token doesn't work in Grafana
- Verify token was copied correctly (no extra spaces)
- Check service account wasn't deleted
- Regenerate token if needed

## Security Considerations

1. **Token Security** - Tokens are long-lived (1 year); users must store securely
2. **HTTPS Only** - All communication uses HTTPS
3. **Namespace Isolation** - Users cannot access metrics from other namespaces
4. **Read-Only Access** - Service accounts have Viewer role only
5. **Rate Limiting** - Prevents token generation abuse
6. **JWT Authentication** - All API calls require valid authentication

## Comparison: Logs vs Metrics Access

| Feature | ELK Logs | Prometheus/Grafana Metrics |
|---------|----------|---------------------------|
| **Token Type** | Elasticsearch API Key | Grafana Service Account Token |
| **Isolation** | org_id field filter | namespace label filter |
| **Access Method** | Custom logs viewer + ELK API | Grafana UI + Prometheus API |
| **Data Type** | Text logs | Time-series metrics |
| **Query Language** | Elasticsearch DSL | PromQL |
| **Retention** | Configurable in ELK | 15 days (Prometheus default) |
| **UI** | Custom React component | Grafana dashboards |

## Integration with Existing Infrastructure

### Prometheus Configuration

From `/cyoda-ops/systems-mgmt/roles/k8s/prometheus`:

- **Namespace**: `prometheus-ns`
- **Retention**: 15 days
- **Storage**: Longhorn PVC, 14GB
- **Scrape Interval**: Default (typically 15s)

### Grafana Configuration

From `/cyoda-ops/systems-mgmt/roles/k8s/grafana`:

- **Namespace**: `grafana-ns`
- **Version**: 11.1.0
- **Plugins**: `grafana-polystat-panel`
- **Storage**: Longhorn PVC, 10Gi

## Future Enhancements

- [ ] Service account token management (list, revoke)
- [ ] Custom dashboard creation from UI
- [ ] Saved queries and favorites
- [ ] Alerting integration
- [ ] Metrics export to CSV/JSON
- [ ] Real-time metrics streaming
- [ ] Custom time range picker
- [ ] Metrics comparison across time periods
- [ ] Integration with logs (correlated view)
- [ ] Prometheus recording rules per namespace

## Related Documentation

- [Prometheus & Grafana Stack README](/cyoda-ops/systems-mgmt/roles/k8s/prometheus/docs/README.md)
- [Logs Implementation](./LOGS_IMPLEMENTATION.md)
- [Grafana Service Account API](https://grafana.com/docs/grafana/latest/developers/http_api/serviceaccount/)
- [Prometheus Query API](https://prometheus.io/docs/prometheus/latest/querying/api/)
