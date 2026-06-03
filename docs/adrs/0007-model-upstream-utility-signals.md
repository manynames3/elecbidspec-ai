# ADR 0007: Model upstream utility signals separately from active bids

## Status

Accepted

## Context

Many high-value grid and data-center power opportunities do not start as open public bids. Investor-owned utility work often moves through regulatory filings, RTO/ISO planning, capital plans, large-load interconnection requests, zoning records, supplier prequalification, and gated procurement portals before a formal RFP is visible to suppliers. Treating every record as an active bid would mislead users and weaken trust.

## Decision

Opportunity records include separate fields for `project_stage`, `signal_type`, `owner_type`, and optional `forecast_rfp_date`.

Supported stages are:

- `early_signal`
- `pre_rfp`
- `active_bid`
- `awarded`

The backend infers stage, owner type, and signal type during seed loading, manual upload enrichment, API creation, and ingestion-worker processing. The frontend exposes stage and owner filters, shows stage/owner context on bid cards, and explains pursuit timing on detail pages.

## Consequences

The product can represent pre-RFP utility intelligence without claiming that gated IOU procurement is directly accessible. It also gives business-development users a clearer next action: monitor, prequalify, contact partners, prepare a bid, or pass. The tradeoff is that source adapters need to be disciplined about labeling early signals accurately and avoiding unsupported forecast-RFP claims.
