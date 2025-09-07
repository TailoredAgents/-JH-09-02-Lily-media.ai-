# OpenAPI Schema Validation Report
Generated: 2025-09-07T14:25:36.967962+00:00
Schema Hash: dd01268b7d73f703

## ✅ Schema Validation: PASSED

### ⚠️ Warnings

- Missing request body documentation for POST /api/auth/refresh
- Missing description for parameter in POST /api/auth/refresh
- Missing request body documentation for POST /api/auth/logout
- Missing description for parameter in POST /api/auth/logout
- Missing request body documentation for POST /api/2fa/verify
- Missing description for parameter in POST /api/2fa/verify
- Missing description for parameter in OPTIONS /{full_path}
- Used but undefined tags: two-factor-authentication, integrations, authentication

### 📋 Missing Documentation
These endpoints exist in the code but are not documented:

- /openapi.json

### 👻 Orphaned Documentation
These endpoints are documented but don't exist in the code:

- /api/integrations/instagram/post
- /{full_path}
- /api/integrations/metrics/collection
- /api/integrations/tiktok/video
- /api/integrations/facebook/post
- /api/quota/status

### 📝 Recommendations

- Add documentation for missing endpoints
- Remove or update orphaned documentation
- Address documentation warnings for better API usability