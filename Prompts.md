13) PW-FE-REPLACE-003  Analytics UI: replace social vanity cards with business KPIs
TASK: Implement PW-FE-REPLACE-003 (AnalyticsHub ’ business outcomes)

Why:
- Owners need KPIs that show money and bookings, not just likes and reach.

Scope / Done when:
- Replace/augment AnalyticsHub cards to show:
  - Leads, Quotes, Quotes Accepted, Jobs Scheduled, Jobs Completed
  - Revenue, Avg Ticket, Acceptance Rate (%)
  - Time-series chart (group by day/week/month)
- Fetch from /api/analytics/business with filters (date range, group_by, platform?).
- Keep social metrics available but visually secondary.
- Add simple empty-states ("No jobs yet") and loading/error states.
- Tests (frontend):
  - Renders KPIs from mocked API
  - Filter changes refetch and update cards/graph
  - Accessibility: landmarks, labels for KPI cards and chart

Paths to inspect first (read-only):
- frontend/src/components/AnalyticsHub.jsx
- frontend/src/services/api* (HTTP helpers)
- any chart components used today

Branch/PR:
- Branch: feat/pw-fe-analytics-business-kpis
- Title: [PW-FE-REPLACE-003] AnalyticsHub: business outcome KPIs + time series

Depends on:
- PW-ANALYTICS-ADD-001

14) PW-FE-REPLACE-002  Inbox UI: add Leads / Quotes / Jobs tabs
TASK: Implement PW-FE-REPLACE-002 (Inbox tabs ’ Leads/Quotes/Jobs)

Why:
- After DMs become leads/quotes/jobs, users need dedicated views to work the funnel.

Scope / Done when:
- Convert current tabs (inbox/templates) into multi-tab:
  - Inbox | Leads | Quotes | Jobs
- Leads tab:
  - List with status (new/contacted/qualified/closed), platform, created_at
  - Filters: status, platform, date
  - Row actions: view, assign (if RBAC), add note
- Quotes tab:
  - List with status (draft/sent/accepted/declined/expired), total, created_at
  - Filters: status, date
  - Row actions: view, send, mark accepted/declined
- Jobs tab:
  - List with status (scheduled/completed/canceled), scheduled_for, service_type
  - Filters: status, date; action: open in Scheduler (deep-link)
- Implement API calls for each tab (read-only actions here; state changes go to existing endpoints).
- Tests (frontend):
  - Tab switching renders correct lists
  - Filters change queries
  - RBAC: hide/disable assign where role lacks permission
- Accessibility: tabs keyboard-navigable, proper aria-controls/selected

Paths to inspect first (read-only):
- frontend/src/pages/SocialInbox.jsx (or equivalent inbox page/component)
- frontend/src/services/api* (inbox/leads/quotes/jobs endpoints)

Branch/PR:
- Branch: feat/pw-fe-inbox-multitab
- Title: [PW-FE-REPLACE-002] Inbox: add Leads/Quotes/Jobs tabs + filters

Depends on:
- PW-DM-REPLACE-001
- PW-PRICING-ADD-002
- PW-DM-ADD-001

15) PW-FE-ADD-001  Settings UI: add Pricing / Weather / Booking Policies tabs
TASK: Implement PW-FE-ADD-001 (Settings tabs for vertical knobs)

Why:
- Tenants must tune pricing, weather thresholds, and booking behavior without code.

Scope / Done when:
- In Settings page, add three new tabs:
  - Pricing: base_rates (per surface), min_job_total, bundles[], seasonal_modifiers[]
  - Weather: rain probability, wind mph, temp low (F), lookahead_days, auto_reschedule
  - Booking Policies: intent_threshold, require_photos, required_fields[], auto_followup_hours, quiet_hours, business_hours, buffer_minutes
- Bind forms to the new settings endpoints with optimistic UI + server validation error display.
- Show defaults from the settings resolver; indicate plan-gated fields (disabled + tooltip).
- Tests (frontend):
  - Initial load shows resolved defaults
  - Save persists and reflects via re-fetch
  - Validation errors surface inline and prevent save
- Accessibility: labels, descriptions, error text announced; tab panel roles.

Paths to inspect first (read-only):
- frontend/src/pages/Settings.jsx
- frontend/src/services/api* (settings GET/PUT)

Branch/PR:
- Branch: feat/pw-fe-settings-vertical-tabs
- Title: [PW-FE-ADD-001] Settings: Pricing/Weather/Booking tabs (tenant-configurable)

Depends on:
- PW-SETTINGS-REPLACE-001
- PW-SETTINGS-ADD-001

16) PW-SEC-REPLACE-001  Enforce org + RBAC on sensitive endpoints
TASK: Implement PW-SEC-REPLACE-001 (org-scoped + RBAC enforcement across sensitive routes)

Why:
- Multi-tenant safety: DM inbox, leads, quotes, jobs, media must be org-isolated with role checks.

Scope / Done when:
- Audit routes: inbox, leads, quotes, jobs, media, analytics.
- Require org context on each; replace user-only filters with org_id filters and RBAC checks.
- Return 403 for cross-tenant access; add unit/integration tests for allow/deny cases.
- Doc note: "All sensitive resources are org-scoped; user filters optional."

Paths to inspect first (read-only):
- backend/api/* (inbox, leads, quotes, jobs, media, analytics routes)
- backend/auth/* (tenant extraction, permission checker)
- backend/db/query helpers (if any)

Branch/PR:
- Branch: fix/pw-org-rbac-enforcement
- Title: [PW-SEC-REPLACE-001] Enforce org + RBAC on inbox/leads/quotes/jobs/media/analytics

Depends on:
- PW-SETTINGS-REPLACE-001

17) PW-SEC-ADD-002  Credentials encryption + rotation (KMS-backed)
TASK: Implement PW-SEC-ADD-002 (encrypt OAuth tokens at rest + key rotation)

Why:
- Social and field-service tokens are high-value secrets; must be encrypted & rotated.

Scope / Done when:
- Add a crypto/KMS abstraction (e.g., KeyProvider) and encrypt at rest:
  - UserCredentials tokens for social + (future) field-service creds.
- Store: algorithm, key version, last_rotated_at; implement rotate() path.
- Migrations: add columns for metadata.
- Service hooks: encrypt on save, decrypt on use; reject if key unavailable.
- Tests: encrypt/decrypt/rotate happy paths; failures (bad key, wrong version) handled.

Paths to inspect first (read-only):
- backend/db/models/UserCredentials* (or wherever tokens live)
- backend/core/config* (inject KMS provider config)

Branch/PR:
- Branch: feat/pw-sec-credentials-encryption
- Title: [PW-SEC-ADD-002] Encrypt tokens at rest + rotation metadata (KMS-backed)

18) PW-SEC-ADD-003  Per-endpoint rate limiting
TASK: Implement PW-SEC-ADD-003 (throttles on webhook/booking/media endpoints)

Why:
- Prevent abuse and brute force; plan quotas aren't per-endpoint throttles.

Scope / Done when:
- Introduce middleware/util for sliding-window limits (e.g., per-IP and per-user):
  - Webhooks (social DMs)
  - Media upload/download
  - Booking-related endpoints (quotes/jobs)
- Configurable limits via env/plan; return 429 with retry headers.
- Tests: hit limits ’ 429, within limits ’ 200; separate buckets per endpoint.

Paths to inspect first (read-only):
- backend/app or middleware registration points
- backend/api/* (routes to wrap)
- backend/core/config* (expose per-endpoint configs)

Branch/PR:
- Branch: feat/pw-sec-rate-limits
- Title: [PW-SEC-ADD-003] Endpoint rate limits (webhooks, media, booking)

19) PW-INTEG-ADD-001  Housecall Pro client (OAuth, create job, webhooks)
TASK: Implement PW-INTEG-ADD-001 (Housecall Pro integration client)

Why:
- Push accepted quotes into a real field-service system and stay in sync on job status.

Scope / Done when:
- Client module: HousecallProClient with methods:
  - oauth_start(), oauth_callback() (persist encrypted creds per org)
  - create_job({customer, service_type, address, scheduled_for, duration})
  - update_job_status(job_external_id, status, note?)
- API:
  - GET /api/integrations/housecallpro/oauth/start
  - GET /api/integrations/housecallpro/oauth/callback
  - POST /api/integrations/housecallpro/jobs (org-scoped; from accepted Quote/Job)
- Webhooks:
  - POST /api/integrations/housecallpro/webhook ’ verifies signature, upserts external status ’ PATCH internal Job
- Security:
  - Encrypt tokens with the credentials KMS (from PW-SEC-ADD-002)
  - Org/RBAC checks on all routes
- Tests:
  - Unit: client method signatures + request building (mock HTTP)
  - Integration: oauth flow happy path (mock), create job maps fields, webhook updates internal Job

Paths to inspect (read-only):
- backend/integrations/* (pattern)
- backend/db/models/* (Job + UserCredentials)
- backend/api/* (oauth patterns you already use)

Branch/PR:
- Branch: feat/pw-integ-housecallpro
- Title: [PW-INTEG-ADD-001] Housecall Pro client + oauth + job create + webhook

Depends on:
- PW-DM-ADD-001 (Job model exists)
- PW-SEC-ADD-002 (encrypted creds)
- PW-SEC-REPLACE-001 (org/RBAC enforced)

20) PW-INTEG-ADD-002  Jobber client (OAuth, create job, webhooks)
TASK: Implement PW-INTEG-ADD-002 (Jobber integration client)

Why:
- Many exterior-cleaning shops use Jobber; parity with Housecall Pro expands TAM.

Scope / Done when:
- Client: JobberClient with:
  - oauth_start(), oauth_callback()
  - create_job({customer, service_type, address, scheduled_for, duration})
  - update_job_status(job_external_id, status, note?)
- API:
  - GET /api/integrations/jobber/oauth/start
  - GET /api/integrations/jobber/oauth/callback
  - POST /api/integrations/jobber/jobs
- Webhooks:
  - POST /api/integrations/jobber/webhook ’ verify ’ update internal Job
- Security:
  - Encrypt tokens (KMS), org/RBAC checks
- Tests:
  - Unit: client methods (mock HTTP)
  - Integration: oauth happy path, create job field mapping, webhook status update

Paths to inspect (read-only):
- backend/integrations/* (reuse patterns from 19)
- backend/db/models/* (Job + creds)
- backend/api/*

Branch/PR:
- Branch: feat/pw-integ-jobber
- Title: [PW-INTEG-ADD-002] Jobber client + oauth + job create + webhook

Depends on:
- PW-DM-ADD-001
- PW-SEC-ADD-002
- PW-SEC-REPLACE-001

21) PW-SETTINGS-ADD-002  Enforcement points (wire resolver into services)
TASK: Implement PW-SETTINGS-ADD-002 (use the settings resolver across services)

Why:
- Ensure all behavior is SaaS-configurable (no hard-coded rules): pricing, DM booking, weather, scheduling.

Scope / Done when:
- Update the following to read from the central settings resolver:
  - DM pipeline: dm.intent_threshold, require_photos, required_fields, auto_followup_hours, quiet_hours
  - Pricing engine: pricing.base_rates, min_job_total, bundles, seasonal_modifiers
  - Weather/rescheduler: weather.bad_weather_threshold, lookahead_days, auto_reschedule
  - Scheduling: business_hours, buffer_minutes
- Keep changes minimal (read settings where decisions are made). If a large refactor is needed, add TODO with related Action IDs.
- Tests: add unit tests per service to confirm decisions change when settings change (e.g., different thresholds ’ different outcomes).
- Add a tiny "effective settings" cache bust call where settings update endpoints write.

Paths to inspect (read-only):
- backend/services/* (DM, pricing, weather/rescheduler, scheduling)
- backend/api/* (touch points where decisions occur)

Branch/PR:
- Branch: feat/pw-settings-enforcement
- Title: [PW-SETTINGS-ADD-002] Wire resolver into DM/pricing/weather/scheduling enforcement points

Depends on:
- PW-SETTINGS-REPLACE-001
- PW-SETTINGS-ADD-001

22) PW-DM-DELETE-001  Remove premature "Convert to Jobs" marketing claim
TASK: Implement PW-DM-DELETE-001 (delete misleading landing-page claim)

Why:
- Until the DM’Lead’Quote’Job pipeline is fully shipped, the claim is misleading.

Scope / Done when:
- Remove/adjust landing-page copy that states "Convert to Jobs & Captures photos, provides estimates, and books jobs directly."
- Keep benefit-oriented copy but avoid promising unshipped features (or add "coming soon" if marketing requires).
- Run a quick grep to ensure no other pages claim this shipped funnel.

Paths to inspect first (read-only):
- frontend/src/pages/LandingPage.jsx
- frontend/src/components/* (any hero/feature sections)
- public content (if any marketing HTML snippets)

Branch/PR:
- Branch: chore/pw-landing-cleanup-convert-to-jobs
- Title: [PW-DM-DELETE-001] Remove/adjust "Convert to Jobs" marketing claim

Depends on:
- (none)

23) PW-FE-DELETE-001  Remove mock scheduledPosts data from Scheduler
TASK: Implement PW-FE-DELETE-001 (remove mock data from Scheduler)

Why:
- Production UI must reflect real jobs/posts only; mock arrays cause confusion and bugs.

Scope / Done when:
- Delete any hard-coded mock arrays/fixtures (e.g., scheduledPosts) from Scheduler.jsx and related components.
- Ensure the Content mode still fetches via existing API; Service Jobs mode fetches /api/jobs.
- Add a simple empty-state ("No jobs scheduled") instead of mock data.
- Frontend tests updated: rely on mocked API responses rather than in-file fixtures.

Paths to inspect first (read-only):
- frontend/src/pages/Scheduler.jsx
- frontend/src/components/* (calendar, list rendering)
- frontend/src/services/api* (ensure real fetch paths are used)

Branch/PR:
- Branch: chore/pw-fe-scheduler-remove-mocks
- Title: [PW-FE-DELETE-001] Remove mock scheduledPosts; use real API with empty-states

Depends on:
- PW-FE-REPLACE-001 (dual-mode groundwork)

24) PW-ANALYTICS-DELETE-001  Remove synthetic "ROI" metric (backend/UI references)
TASK: Implement PW-ANALYTICS-DELETE-001 (delete synthetic ROI until revenue exists)

Why:
- Current ROI is a fake constant-based formula; it misleads owners. Replace later with revenue-based ROI.

Scope / Done when:
- Remove ROI calculation from backend analytics/dashboard endpoints.
- Remove/rename any ROI UI card that displays this synthetic value (or hide behind a feature flag set to off).
- Ensure no 500s: where ROI field was referenced, either drop the field or return null/omit safely.
- Add a TODO note referencing the future revenue-based ROI (depends on payments/revenue tracking).
- Tests: adjust backend analytics tests to stop expecting ROI; frontend snapshot/tests updated accordingly.

Paths to inspect first (read-only):
- backend/api/* (dashboard/analytics endpoints)
- frontend/src/components/AnalyticsHub.jsx (any ROI card)
- frontend/src/services/api* (ROI field references)

Branch/PR:
- Branch: chore/pw-analytics-remove-synthetic-roi
- Title: [PW-ANALYTICS-DELETE-001] Remove synthetic ROI (backend & UI references)

Depends on:
- (none)  safe to delete now; real ROI comes later with revenue tracking

25) PW-INTEG-DELETE-001  Remove unshipped integration claims (HCP/Jobber/Calendly)
TASK: Implement PW-INTEG-DELETE-001 (delete/flag unshipped integration marketing)

Why:
- Until real connectors ship, claiming "Works with Housecall Pro / Jobber / Calendly" is misleading.

Scope / Done when:
- Remove or "coming soon" any claims of HCP/Jobber/Calendly integrations in landing/marketing UI.
- Grep repo to catch duplicates (hero sections, feature bullets, footers).
- Optional: guard remaining mentions behind a feature flag defaulted OFF.
- Ensure no UI references point to non-existent setup pages.

Paths to inspect first (read-only):
- frontend/src/pages/LandingPage.jsx
- frontend/src/components/* (feature/hero sections)
- any public site content (if applicable)

Branch/PR:
- Branch: chore/pw-landing-remove-integration-claims
- Title: [PW-INTEG-DELETE-001] Remove/flag HCP/Jobber/Calendly claims (unshipped)

26) PW-WEATHER-DELETE-001  Remove weather-aware scheduling claims (until live)
TASK: Implement PW-WEATHER-DELETE-001 (delete/flag weather-reschedule claims)

Why:
- Weather thresholds & auto-rescheduler are being built; claims must not predate delivery.

Scope / Done when:
- Remove "weather-aware scheduling / auto-reschedule" statements from landing/marketing.
- If product wants to tease it, change to "coming soon" and link to a public roadmap URL (if you have one).
- Verify no screenshots or badges imply it's already live.

Paths to inspect first (read-only):
- frontend/src/pages/LandingPage.jsx
- frontend/src/components/* (marketing sections)

Branch/PR:
- Branch: chore/pw-landing-remove-weather-claims
- Title: [PW-WEATHER-DELETE-001] Remove/flag weather-aware scheduling claims

27) PW-ANALYTICS-ADD-002  Seasonal & cohort analyses (backend + optional UI hook)
TASK: Implement PW-ANALYTICS-ADD-002 (seasonality/cohorts)

Why:
- Pressure-washing demand is seasonal; owners need month/quarter trends and service-type cohorts.

Scope / Done when:
- Extend /api/analytics/business to support:
  - group_by: month|quarter (in addition to day|week)
  - breakdowns: service_type (and keep platform breakdown if present)
  - outputs:
    - time_series grouped by month/quarter
    - cohorts: { service_type ’ counts & revenue over period }
- DB: add indexes if needed for created_at/org_id/status; ensure queries are performant.
- Tests:
  - Unit: aggregator for month/quarter rollups and service_type cohorts
  - Integration: endpoint returns expected shapes for seeded data
- Optional UI hook (small):
  - Add a "Seasonality" chart tab in AnalyticsHub to read the new fields (if prior UI work exists); otherwise leave TODO pointing to FE action.

Paths to inspect first (read-only):
- backend/api/* (analytics routes)
- backend/services/* (analytics aggregator/queries)
- frontend/src/components/AnalyticsHub.jsx (only if adding the small chart tab now)

Branch/PR:
- Branch: feat/pw-analytics-seasonality-cohorts
- Title: [PW-ANALYTICS-ADD-002] Seasonality (month/quarter) + service-type cohorts

Depends on:
- PW-ANALYTICS-ADD-001

28) PW-SETTINGS-REPLACE-002  Migrate legacy plan booleans ’ features JSON
TASK: Implement PW-SETTINGS-REPLACE-002 (replace deprecated boolean plan flags)

Why:
- Plan gating should be driven by a single source of truth (features JSON), not scattered booleans.

Scope / Done when:
- Identify boolean plan flags still referenced (e.g., full_ai, enhanced_autopilot, etc.).
- Migrate gating to Plan.features JSON (keys like "dm_booking", "pricing_rules", "weather_scheduler", "integrations.housecallpro", etc.).
- Update helpers (plan_enforcement) to read only from features JSON.
- Add migration script (data/backfill): set features JSON based on current booleans; mark booleans deprecated.
- Remove boolean reads in code paths; leave deprecation comment on model until a later cleanup PR drops columns.
- Tests: unit tests for plan enforcement (has_feature/get_limit) reading JSON only.

Paths to inspect first (read-only):
- backend/db/models/Plan* (booleans + features JSON)
- backend/services/plan_enforcement* (helpers)
- any feature-gated routes/services referencing plan booleans

Branch/PR:
- Branch: refactor/pw-plan-features-json
- Title: [PW-SETTINGS-REPLACE-002] Migrate plan gating to features JSON only

Depends on:
- none (safe refactor; coordinate with teams touching gating)

29) PW-SETTINGS-DELETE-001  Remove unused/research-only settings keys in FE
TASK: Implement PW-SETTINGS-DELETE-001 (prune irrelevant settings UI keys)

Why:
- The pressure-washing vertical needs clear, relevant settings; leftover research keys confuse users.

Scope / Done when:
- In Settings UI, remove or repurpose research-only keys (e.g., company_name, industryContext, legacy research toggles) that do not affect vertical behavior.
- Keep only vertical-relevant tabs/fields: Pricing, Weather, Booking Policies, Social Inbox basics, Integrations.
- Ensure API calls still succeed (no missing fields sent); fetch the new effective settings after save.
- Tests: FE tests updated; saving without the removed keys still passes.

Paths to inspect first (read-only):
- frontend/src/pages/Settings.jsx
- frontend/src/components/* (any settings subcomponents)
- frontend/src/services/api* (payload shapes for settings PUT)

Branch/PR:
- Branch: chore/pw-settings-prune-unused
- Title: [PW-SETTINGS-DELETE-001] Remove unused/research keys from Settings UI

Depends on:
- PW-SETTINGS-REPLACE-001 (resolver exists)
- PW-SETTINGS-ADD-001 (namespaces exist)

30) PW-INTEG-ADD-003  ServiceTitan client (OAuth, create job, webhooks)
TASK: Implement PW-INTEG-ADD-003 (ServiceTitan integration client)

Why:
- Some exterior-cleaning operations are on ServiceTitan; completing the trio increases coverage.

Scope / Done when:
- Client: ServiceTitanClient with:
  - oauth_start(), oauth_callback() ’ persist encrypted creds per org
  - create_job({customer, service_type, address, scheduled_for, duration})
  - update_job_status(external_id, status, note?)
- API:
  - GET /api/integrations/servicetitan/oauth/start
  - GET /api/integrations/servicetitan/oauth/callback
  - POST /api/integrations/servicetitan/jobs
- Webhooks:
  - POST /api/integrations/servicetitan/webhook ’ verify, map payload ’ upsert external status ’ PATCH internal Job
- Security:
  - Encrypt tokens with KMS (from PW-SEC-ADD-002); org/RBAC checks on routes
- Tests:
  - Unit: request-building, signature verification (mock)
  - Integration: oauth happy path; create job maps fields; webhook updates Job

Paths to inspect first (read-only):
- backend/integrations/* (mirror patterns from Housecall Pro/Jobber)
- backend/db/models/* (Job, credentials)
- backend/api/* (oauth/route patterns)

Branch/PR:
- Branch: feat/pw-integ-servicetitan
- Title: [PW-INTEG-ADD-003] ServiceTitan client + oauth + job create + webhook

Depends on:
- PW-DM-ADD-001 (Job model)
- PW-SEC-ADD-002 (encrypted creds)
- PW-SEC-REPLACE-001 (org/RBAC enforced)

31) PW-PRICING-REPLACE-001  Revenue-based ROI (replace synthetic ROI, gated)
TASK: Implement PW-PRICING-REPLACE-001 (revenue-based ROI metric, no more constants)

Why:
- ROI must reflect money, not engagement. Use revenue once available; otherwise return null and hide in UI.

Scope / Done when:
- Backend:
  - Add roi.revenue_based = (total_revenue / marketing_cost) or, if no explicit spend yet, (total_revenue / content_cost_proxy). If neither exists, return null/omit.
  - Expose via /api/analytics/business (add an optional "roi" field).
  - Guard with feature flag: features["analytics.revenue_roi"].
- UI:
  - If roi === null ’ hide ROI card or show "Enable revenue tracking to see ROI".
  - If roi present ’ display % with tooltip explaining formula.
- Tests:
  - Backend unit: roi null when revenue=0, non-null when revenue>0; flag off ’ field omitted.
  - FE: card hidden when null; renders when value present.

Paths to inspect first (read-only):
- backend/api/analytics* or dashboard endpoints (where synthetic ROI was referenced previously)
- frontend/src/components/AnalyticsHub.jsx (card rendering)

Branch/PR:
- Branch: feat/pw-pricing-revenue-roi
- Title: [PW-PRICING-REPLACE-001] Revenue-based ROI (feature-gated; null until revenue exists)