---
name: user-profile-lookup
description: Look up a mock CRM user profile and reconcile it with interview findings. Use when the user mentions user_id (e.g. U001), a name like 陈思远/林婉清/周启明, 用户画像, CRM, or asks to cross-check profile vs report claims.
license: MIT
metadata:
  version: "1.0"
  domain: interview-analysis
---

# User profile lookup

## When to Use

- User mentions `U001` / `U002` / `U003` or interviewee names
- Asks for 用户画像, profile consistency, or CRM cross-check
- Needs vehicle / city / ads package vs interview claims

## Instructions

1. Extract `user_id` or name from the query or report metadata.
2. Call `get_user_profile`.
3. If found, cross-check vehicle, stage, city, and ads claims against the report.
4. If not found, continue report-only analysis and explicitly state the miss.
5. When also analyzing a document, load `single-report-analysis` (or multi) skill as needed.
