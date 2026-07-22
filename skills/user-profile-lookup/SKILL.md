---
name: user-profile-lookup
description: Load mock user CRM profile and reconcile with interview findings.
---

# User profile lookup

1. Extract user_id or name from query/report.
2. Call `get_user_profile`.
3. If found, cross-check vehicle/stage/ads claims vs report.
4. If not found, continue with report-only and state the miss.
