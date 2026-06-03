# ADR 0006: Separate public-source opportunities from tenant-owned uploads

## Status

Accepted

## Context

The MVP needs public bid discovery for all users, but manual RFP/spec uploads can contain customer-specific pursuit context. Treating every opportunity as a global record would make a multi-customer pilot unsafe and would undercut trust in saved searches, workflow notes, proposal artifacts, and attachment extraction.

## Decision

Opportunity records include `tenant_id`. Source-ingested and seed opportunities use the public tenant, while manual uploads use the signed-in user's tenant. Read paths expose public opportunities to everyone and tenant-owned opportunities only to the owning tenant. Tenant-specific fit scores are overlaid at read/search/alert time using the current company profile.

## Consequences

Public source coverage remains shared and efficient. Manual uploads can be used in customer pilots without appearing in public demo search or another tenant's workspace. The tradeoff is that tenant-specific fit scoring is computed dynamically for public opportunities instead of materialized in a dedicated score table; that is acceptable for low-volume pilots but should be revisited for larger customer counts.
