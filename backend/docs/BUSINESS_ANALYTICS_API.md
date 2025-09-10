# Business Analytics API Documentation

## PW-ANALYTICS-ADD-001: Business KPIs Analytics

This API provides business outcome analytics for pressure washing companies, replacing vanity metrics with actionable KPIs that track the lead → quote → job → revenue pipeline.

### Endpoints

#### GET /api/analytics/business

Get comprehensive business analytics for the organization.

**Authentication:** Required  
**Permissions:** `analytics.read`

##### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `from_date` | date | 30 days ago | Start date (ISO format: YYYY-MM-DD) |
| `to_date` | date | today | End date (ISO format: YYYY-MM-DD) |
| `group_by` | string | "day" | Time grouping: "day", "week", "month" |
| `platform` | string | null | Filter by platform: "facebook", "instagram", "twitter" |
| `service_type` | string | null | Filter by service type: "pressure_washing", "roof_cleaning", etc. |

##### Response Schema

```json
{
  "totals": {
    "leads": 150,
    "quotes": 85,
    "quotes_accepted": 42,
    "jobs_scheduled": 38,
    "jobs_completed": 35,
    "revenue": 87500.0,
    "avg_ticket": 2500.0,
    "acceptance_rate": 0.494,
    "completion_rate": 0.921,
    "lead_to_quote_rate": 0.567,
    "quote_to_job_rate": 0.905
  },
  "time_series": [
    {
      "period": "2025-01-15",
      "leads": 5,
      "quotes": 3,
      "quotes_accepted": 2,
      "jobs_scheduled": 2,
      "jobs_completed": 1,
      "revenue": 2500.0
    }
  ],
  "platform_breakdown": [
    {
      "platform": "facebook",
      "leads": 80,
      "quotes": 45,
      "quotes_accepted": 22,
      "jobs_completed": 20,
      "revenue": 50000.0
    }
  ],
  "service_type_breakdown": [
    {
      "service_type": "pressure_washing",
      "jobs_scheduled": 25,
      "jobs_completed": 23,
      "revenue": 57500.0,
      "avg_ticket": 2500.0
    }
  ]
}
```

##### Business Metrics Definitions

- **leads**: Total leads generated from social media DMs
- **quotes**: Total quotes sent to prospects
- **quotes_accepted**: Quotes accepted by customers
- **jobs_scheduled**: Jobs scheduled from accepted quotes
- **jobs_completed**: Jobs completed successfully
- **revenue**: Total revenue from completed jobs (uses actual_cost when available, falls back to estimated_cost)
- **avg_ticket**: Average revenue per completed job
- **acceptance_rate**: quotes_accepted / quotes
- **completion_rate**: jobs_completed / jobs_scheduled  
- **lead_to_quote_rate**: quotes / leads
- **quote_to_job_rate**: jobs_scheduled / quotes_accepted

##### Example Requests

```bash
# Basic analytics for last 30 days
curl -X GET "https://api.example.com/api/analytics/business" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Analytics for specific date range with daily grouping
curl -X GET "https://api.example.com/api/analytics/business?from_date=2025-01-01&to_date=2025-01-31&group_by=day" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Facebook-only analytics with weekly grouping
curl -X GET "https://api.example.com/api/analytics/business?platform=facebook&group_by=week" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Pressure washing jobs analytics with monthly grouping
curl -X GET "https://api.example.com/api/analytics/business?service_type=pressure_washing&group_by=month" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

#### GET /api/analytics/business/summary

Get high-level business summary with period-over-period comparison.

**Authentication:** Required  
**Permissions:** `analytics.read`

##### Response Schema

```json
{
  "period": {
    "start_date": "2025-01-15",
    "end_date": "2025-02-14",
    "days": 30
  },
  "current": {
    "leads": 150,
    "quotes": 85,
    "quotes_accepted": 42,
    "jobs_completed": 35,
    "revenue": 87500.0,
    "avg_ticket": 2500.0,
    "acceptance_rate": 0.494,
    "completion_rate": 0.921
  },
  "previous": {
    "leads": 120,
    "quotes": 70,
    "quotes_accepted": 35,
    "jobs_completed": 32,
    "revenue": 80000.0,
    "avg_ticket": 2500.0
  },
  "growth": {
    "leads": 25.0,
    "quotes": 21.4,
    "quotes_accepted": 20.0,
    "jobs_completed": 9.4,
    "revenue": 9.4,
    "avg_ticket": 0.0
  }
}
```

##### Example Request

```bash
curl -X GET "https://api.example.com/api/analytics/business/summary" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

#### GET /api/analytics/health

Health check endpoint for monitoring analytics service availability.

**Authentication:** Not required

##### Response Schema

```json
{
  "status": "healthy",
  "timestamp": "2025-09-09T12:35:00.000Z"
}
```

---

### Error Responses

#### 400 Bad Request
```json
{
  "detail": "Invalid group_by value. Must be 'day', 'week', or 'month'"
}
```

#### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

#### 403 Forbidden
```json
{
  "detail": "Insufficient permissions. Required: analytics.read"
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Failed to compute business analytics"
}
```

---

### Performance Considerations

The analytics API includes several performance optimizations:

1. **Database Indexes**: Composite indexes on org_id + created_at + status for fast time-range queries
2. **Query Optimization**: Single queries with aggregate functions to minimize database round-trips
3. **Date Range Limits**: Maximum 2-year date ranges to prevent excessive queries
4. **Multi-tenant Isolation**: All queries are automatically scoped to the user's organization

### Rate Limits

- **Standard tier**: 100 requests per hour
- **Pro tier**: 500 requests per hour  
- **Enterprise tier**: Unlimited

### Data Freshness

Analytics data is computed in real-time from the transactional database. For high-traffic organizations, consider implementing caching strategies or data warehouse synchronization.

### Use Cases

#### Dashboard Widgets
```javascript
// Monthly business overview
const monthlyAnalytics = await fetch('/api/analytics/business/summary');

// Platform performance comparison
const platformAnalytics = await fetch('/api/analytics/business?group_by=week');
```

#### Business Reporting
```javascript
// Quarterly business review
const quarterlyData = await fetch('/api/analytics/business?from_date=2025-01-01&to_date=2025-03-31&group_by=month');

// Service type profitability
const serviceAnalytics = await fetch('/api/analytics/business?group_by=month');
const { service_type_breakdown } = await serviceAnalytics.json();
```

#### Performance Monitoring
```javascript
// Track conversion funnel health
const { totals } = await (await fetch('/api/analytics/business')).json();
const funnelHealth = {
  lead_quality: totals.lead_to_quote_rate,
  sales_effectiveness: totals.acceptance_rate,
  operational_excellence: totals.completion_rate
};
```

### Multi-tenant Data Isolation

All analytics queries are automatically scoped to the authenticated user's organization using the `X-Organization-ID` header or JWT claims. This ensures:

- **Data Privacy**: Organizations can only see their own metrics
- **Performance**: Queries are optimized with organization_id in WHERE clauses
- **Compliance**: Meets data isolation requirements for multi-tenant SaaS

### Integration Examples

#### React Dashboard Component
```jsx
import { useState, useEffect } from 'react';

function BusinessAnalyticsDashboard() {
  const [analytics, setAnalytics] = useState(null);
  const [dateRange, setDateRange] = useState('30d');
  
  useEffect(() => {
    fetch(`/api/analytics/business?group_by=day`)
      .then(res => res.json())
      .then(setAnalytics);
  }, [dateRange]);
  
  if (!analytics) return <div>Loading...</div>;
  
  return (
    <div className="analytics-dashboard">
      <div className="metrics-grid">
        <MetricCard 
          title="Total Revenue" 
          value={`$${analytics.totals.revenue.toLocaleString()}`}
          growth={analytics.growth?.revenue}
        />
        <MetricCard 
          title="Jobs Completed" 
          value={analytics.totals.jobs_completed}
          growth={analytics.growth?.jobs_completed}
        />
        <MetricCard 
          title="Quote Acceptance Rate" 
          value={`${(analytics.totals.acceptance_rate * 100).toFixed(1)}%`}
        />
      </div>
      <TimeSeriesChart data={analytics.time_series} />
    </div>
  );
}
```

#### Python Analytics Script
```python
import requests
import pandas as pd

def get_business_analytics(from_date, to_date, group_by='day'):
    response = requests.get(
        'https://api.example.com/api/analytics/business',
        params={
            'from_date': from_date,
            'to_date': to_date,
            'group_by': group_by
        },
        headers={'Authorization': f'Bearer {token}'}
    )
    return response.json()

# Generate monthly business report
analytics = get_business_analytics('2025-01-01', '2025-01-31', 'day')
df = pd.DataFrame(analytics['time_series'])

print(f"Total Revenue: ${analytics['totals']['revenue']:,.2f}")
print(f"Average Ticket: ${analytics['totals']['avg_ticket']:,.2f}")
print(f"Quote Acceptance Rate: {analytics['totals']['acceptance_rate']*100:.1f}%")
```