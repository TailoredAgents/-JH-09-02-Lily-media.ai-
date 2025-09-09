# Social Inbox Organization Scoping and RBAC

## Overview

The social inbox has been updated to enforce proper organization-scoped access control with role-based permissions. This ensures tenant isolation and enables shared team workflows in multi-tenant deployments.

## Key Changes (PW-DM-REPLACE-002)

### Organization-Scoped Queries
- All inbox endpoints now filter by organization context via the `X-Organization-ID` header
- Queries join through `SocialPlatformConnection` to access the organization relationship:
  ```sql
  SocialInteraction -> SocialPlatformConnection -> organization_id
  ```

### Role-Based Access Control
- **Read Operations**: Require any valid organization membership
- **Write Operations**: Require minimum "member" role within the organization
- **Role Hierarchy**: `admin` > `member` > `viewer`

## API Changes

### Required Headers
All inbox endpoints now require:
```
X-Organization-ID: <organization_uuid>
```

### Updated Endpoints

#### GET /api/inbox/interactions
- **Scoping**: Returns only interactions for the specified organization
- **Optional User Filter**: `?user_id=123` filters within the organization
- **RBAC**: Any organization member can read
- **Note**: "Inbox is org-scoped; user filters are optional."

#### PUT /api/inbox/interactions/{id}
- **Scoping**: Can only update interactions within the user's organization
- **RBAC**: Requires "member" role or higher

#### DELETE /api/inbox/interactions/{id}
- **Scoping**: Can only archive interactions within the user's organization  
- **RBAC**: Requires "member" role or higher

#### POST /api/inbox/interactions/respond
- **Scoping**: Can only respond to interactions within the user's organization
- **RBAC**: Requires "member" role or higher

#### POST /api/inbox/interactions/generate-response
- **Scoping**: Organization context required for AI response generation
- **RBAC**: Any organization member can generate responses

### Template and Knowledge Base Endpoints
- All require organization context via `X-Organization-ID` header
- Create operations require "member" role or higher
- **Note**: Full org-scoping requires schema updates (see TODOs below)

## Security Benefits

1. **Tenant Isolation**: Users cannot access interactions from other organizations
2. **Shared Team Workflows**: Team members can collaborate on the same interactions
3. **Role-Based Permissions**: Fine-grained control over who can perform actions
4. **Audit Trail**: Organization context is maintained for all operations

## Implementation Details

### Query Pattern
```python
# Old: User-only filtering (unsafe for multi-tenant)
query = db.query(SocialInteraction).filter(
    SocialInteraction.user_id == current_user.id
)

# New: Org-scoped filtering with optional user filter
query = db.query(SocialInteraction).join(
    SocialPlatformConnection,
    SocialInteraction.connection_id == SocialPlatformConnection.id
).filter(
    SocialPlatformConnection.organization_id == tenant_context.organization_id
)

# Optional user filtering within org
if user_id is not None:
    query = query.filter(SocialInteraction.user_id == user_id)
```

### RBAC Enforcement
```python
# Require specific role for write operations
@router.put("/interactions/{interaction_id}")
async def update_interaction(
    tenant_context: TenantContext = Depends(require_role("member"))
):
    # Only users with "member" role or higher can access
```

## Testing

Comprehensive test coverage includes:
- Unauthorized organization access (403 Forbidden)
- Missing organization context (400 Bad Request)  
- Role-based access control validation
- Pagination with org-scoped filtering
- Cross-organization interaction access prevention

## TODOs for Complete Implementation

### Schema Updates Needed
The following models need `organization_id` fields for complete org-scoping:

1. **ResponseTemplate**: Currently user-scoped, should be org-scoped
   ```sql
   ALTER TABLE response_templates ADD COLUMN organization_id UUID 
   REFERENCES organizations(id) ON DELETE CASCADE;
   ```

2. **CompanyKnowledge**: Currently user-scoped, should be org-scoped  
   ```sql
   ALTER TABLE company_knowledge ADD COLUMN organization_id UUID
   REFERENCES organizations(id) ON DELETE CASCADE;
   ```

3. **InteractionResponse**: Should include organization context
   ```sql
   ALTER TABLE interaction_responses ADD COLUMN organization_id UUID
   REFERENCES organizations(id) ON DELETE CASCADE;
   ```

### Migration Strategy
1. Add `organization_id` columns with nullable constraint
2. Backfill data by joining through user organization relationships
3. Make columns non-nullable after backfill
4. Update application code to use org-scoped queries
5. Add proper indexes for performance

## Backward Compatibility

- API clients must include `X-Organization-ID` header
- Single-tenant deployments can use a default organization
- User-only filtering is preserved as optional `?user_id=` parameter

## Performance Considerations

- Added indexes on organization_id fields for efficient filtering
- Joins through SocialPlatformConnection are optimized with proper indexing
- Query plans remain efficient for org-scoped access patterns

## Migration Commands

```bash
# Generate migration for org-scoped templates and knowledge
alembic revision -m "Add organization_id to templates and knowledge base"

# Run migration
alembic upgrade head
```