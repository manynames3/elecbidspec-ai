# ADR 0003: Keep Deterministic Proposal Generation as the Baseline

## Status

Accepted

## Context

The product promises bid-readiness output even when AI services are unavailable, disabled, slow, or too expensive for a pilot. Bedrock can improve proposal language, but requiring it for every proposal would weaken the MVP demo path and increase operational risk.

## Decision

Generate a deterministic proposal package by default. Use Bedrock only when explicitly enabled for proposal enhancement. Cache proposal artifacts per opportunity and tenant so DOCX/PDF downloads do not trigger repeated AI calls.

## Consequences

- The proposal workflow works without AWS Bedrock credentials.
- Bedrock failures can fall back to deterministic output instead of breaking the user flow.
- AI-enhanced content can still use opportunity data, extracted specs, fit score, and company profile context.
- The deterministic path must stay useful enough to be a credible baseline.
