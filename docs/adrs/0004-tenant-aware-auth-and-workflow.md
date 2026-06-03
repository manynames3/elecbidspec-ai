# ADR 0004: Add First-Party Tenant-Aware Auth and Workflow State

## Status

Accepted

## Context

The app began as an MVP demo but includes company-specific profiles, proposal artifacts, saved searches, watched opportunities, notes, and admin refresh controls. A paying pilot needs basic user boundaries without introducing a heavy external identity provider too early.

## Decision

Implement first-party email/password auth with salted PBKDF2 password hashes, hashed bearer session tokens, `admin` and `user` roles, and tenant-aware records for profiles, workflows, saved searches, alerts, and proposal artifacts. Keep `ADMIN_API_TOKEN` as a bootstrap and break-glass path for protected admin ingestion endpoints.

## Consequences

- The MVP supports private pilot usage and role-protected refresh controls.
- Tenant-aware records prepare the data model for future multi-tenant separation.
- Auth remains simple enough for local development and seeded demo users.
- Production deployments still need operational hardening such as password reset, audit logging, and stronger tenant isolation before broad customer rollout.
