# ADR 0005: Label Portal-Gated Sources Instead of Bypassing Access Controls

## Status

Accepted

## Context

Some official procurement portals are public to human users but block server-side monitoring with browser challenges, captchas, supplier-system front doors, or vendor-login requirements. The product still needs to track these sources honestly because coverage trust matters to buyers.

## Decision

Represent portal-gated sources in the source catalog and source health response with explicit `portal_gated` status and access notes. Do not bypass login, captcha, browser challenge, or supplier portal controls. Use official APIs, approved vendor access, or legally allowed browser/session workflows only when available.

## Consequences

- The dashboard can show coverage targets without pretending every source is live-importing.
- The ingestion system stays aligned with public-source and access-control constraints.
- Some high-value sources require future partner access or source-specific agreements.
- Source health becomes a product trust signal, not just an engineering metric.
