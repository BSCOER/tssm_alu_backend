# Analytics API Documentation

## Overview
Analytics endpoints provide data for admin dashboard visualizations including charts, graphs, and statistics.

## Authentication
All analytics endpoints require admin authentication. Include JWT token in Authorization header:
```
Authorization: Bearer <admin-jwt-token>
```

## Endpoints

### 1. User Growth Data
Get monthly user growth data for line chart visualization.

**Endpoint:** `GET /api/v1/admin/analytics/user-growth`

**Response:**
```json
{
  "data": [
    {
      "month": "Jan",
      "totalUsers": 120,
      "newUsers": 15
    },
    {
      "month": "Feb",
      "totalUsers": 145,
      "newUsers": 25
    }
  ]
}
```

**Use Case:** Line chart showing total users and new registrations over time

---

### 2. Category Distribution
Get article distribution by category for pie chart.

**Endpoint:** `GET /api/v1/admin/analytics/category-distribution`

**Response:**
```json
{
  "data": [
    {
      "name": "Technology",
      "value": 45
    },
    {
      "name": "Business",
      "value": 32
    }
  ]
}
```

**Use Case:** Pie chart showing article categories

---

### 3. Engagement Metrics
Get monthly engagement metrics (views, reactions, comments) for bar chart.

**Endpoint:** `GET /api/v1/admin/analytics/engagement-metrics`

**Response:**
```json
{
  "data": [
    {
      "month": "Jan",
      "views": 1250,
      "reactions": 320,
      "comments": 145
    },
    {
      "month": "Feb",
      "views": 1580,
      "reactions": 410,
      "comments": 198
    }
  ]
}
```

**Use Case:** Bar chart showing engagement trends

---

### 4. Alumni by Graduation Year
Get alumni distribution by graduation year for bar chart.

**Endpoint:** `GET /api/v1/admin/analytics/alumni-by-year`

**Response:**
```json
{
  "data": [
    {
      "year": "2019",
      "count": 45
    },
    {
      "year": "2020",
      "count": 52
    }
  ]
}
```

**Use Case:** Bar chart showing alumni by graduation year

---

### 5. Department Distribution
Get alumni distribution by department for pie chart.

**Endpoint:** `GET /api/v1/admin/analytics/department-distribution`

**Response:**
```json
{
  "data": [
    {
      "name": "Computer Science",
      "value": 85
    },
    {
      "name": "Electrical Engineering",
      "value": 62
    },
    {
      "name": "Other",
      "value": 23
    }
  ]
}
```

**Use Case:** Pie chart showing department distribution

---

### 6. Recent Activity Feed
Get recent activity for dashboard feed.

**Endpoint:** `GET /api/v1/admin/analytics/recent-activity`

**Response:**
```json
{
  "activity": [
    {
      "icon": "user-plus",
      "text": "15 new registrations in 7 days",
      "time": "This week"
    },
    {
      "icon": "newspaper",
      "text": "5 articles pending approval",
      "time": "Today"
    },
    {
      "icon": "calendar-alt",
      "text": "3 upcoming events",
      "time": "This month"
    }
  ]
}
```

**Use Case:** Activity feed on dashboard

---

### 7. Stats Summary
Get summary statistics for stat cards.

**Endpoint:** `GET /api/v1/admin/analytics/stats-summary`

**Response:**
```json
{
  "total_users": 290,
  "total_articles": 156,
  "engagement_rate": 85.3,
  "recent_registrations": 15,
  "active_users": 142,
  "growth_percentage": 12.5
}
```

**Use Case:** Stat cards on dashboard

---

### 8. Top Articles
Get top performing articles by views and reactions.

**Endpoint:** `GET /api/v1/admin/analytics/top-articles`

**Response:**
```json
{
  "top_by_views": [
    {
      "_id": "article_id",
      "title": "Article Title",
      "views": 1250,
      "reaction_count": 85,
      "submitted_at": "2024-01-15T10:30:00Z"
    }
  ],
  "top_by_reactions": [
    {
      "_id": "article_id",
      "title": "Article Title",
      "views": 850,
      "reaction_count": 120,
      "submitted_at": "2024-01-20T14:20:00Z"
    }
  ]
}
```

**Use Case:** Top articles list

---

### 9. User Activity Heatmap
Get user activity heatmap data (day of week and hour).

**Endpoint:** `GET /api/v1/admin/analytics/user-activity-heatmap`

**Response:**
```json
{
  "heatmap": {
    "Monday": [0, 0, 0, 0, 0, 5, 12, 25, 35, 42, 38, 30, 28, 32, 40, 45, 38, 30, 20, 15, 10, 5, 2, 0],
    "Tuesday": [0, 0, 0, 0, 0, 6, 15, 28, 38, 45, 40, 32, 30, 35, 42, 48, 40, 32, 22, 16, 12, 6, 3, 0],
    ...
  }
}
```

**Use Case:** Heatmap showing user activity patterns

---

### 10. Content Performance
Get content performance metrics.

**Endpoint:** `GET /api/v1/admin/analytics/content-performance`

**Response:**
```json
{
  "avg_views_per_article": 125.5,
  "total_views": 15680,
  "max_views": 1250,
  "avg_reactions_per_article": 32.8,
  "total_reactions": 4096,
  "avg_comments_per_article": 8.5,
  "total_comments": 1062
}
```

**Use Case:** Content performance metrics

---

## Frontend Integration

### Example: Fetching User Growth Data

```typescript
// In your admin service
export const getAnalytics = {
  userGrowth: async () => {
    const response = await api.get('/api/v1/admin/analytics/user-growth');
    return response.data;
  },
  
  categoryDistribution: async () => {
    const response = await api.get('/api/v1/admin/analytics/category-distribution');
    return response.data;
  },
  
  engagementMetrics: async () => {
    const response = await api.get('/api/v1/admin/analytics/engagement-metrics');
    return response.data;
  },
  
  alumniByYear: async () => {
    const response = await api.get('/api/v1/admin/analytics/alumni-by-year');
    return response.data;
  },
  
  departmentDistribution: async () => {
    const response = await api.get('/api/v1/admin/analytics/department-distribution');
    return response.data;
  },
  
  recentActivity: async () => {
    const response = await api.get('/api/v1/admin/analytics/recent-activity');
    return response.data;
  },
  
  statsSummary: async () => {
    const response = await api.get('/api/v1/admin/analytics/stats-summary');
    return response.data;
  }
};
```

### Example: Using in Admin Component

```typescript
import { useEffect, useState } from 'react';
import { getAnalytics } from '../services/apiService';

export default function AdminDashboard() {
  const [userGrowthData, setUserGrowthData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnalytics();
  }, []);

  const loadAnalytics = async () => {
    try {
      const data = await getAnalytics.userGrowth();
      setUserGrowthData(data.data);
    } catch (error) {
      console.error('Failed to load analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ChartContainer title="User Growth">
      <LineChart
        data={userGrowthData}
        dataKeys={['totalUsers', 'newUsers']}
        xAxisKey="month"
      />
    </ChartContainer>
  );
}
```

## Data Refresh

- Analytics data is calculated in real-time from the database
- No caching is applied to ensure fresh data
- For better performance in production, consider:
  - Caching with short TTL (5-10 minutes)
  - Background jobs to pre-calculate metrics
  - Redis for caching aggregated data

## Performance Considerations

- All endpoints use MongoDB aggregation pipelines for efficiency
- Indexes are created on frequently queried fields
- Limit results to reasonable ranges (last 6 months, top 10, etc.)
- Consider pagination for large datasets

## Error Handling

All endpoints return standard error responses:

```json
{
  "error": "Error message description"
}
```

HTTP Status Codes:
- `200` - Success
- `403` - Forbidden (not admin)
- `500` - Server error

---

**Note:** Replace mock data in frontend with these real API endpoints for production-ready analytics dashboard.
