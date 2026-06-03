# ADR 0002: Model Ingestion as Source Adapters

## Status

Accepted

## Context

Electrical bid opportunities are spread across many official sources with different shapes: APIs, Socrata feeds, HTML tables, bid-item data, Bonfire JSON, public bid pages, and source-specific formats. A single hardcoded importer would not scale as new agencies are added.

## Decision

Use an ingestion adapter registry. Each adapter implements a common interface and returns normalized opportunity records. Default source jobs and source health metadata live in a source catalog. Generic adapters handle public JSON, public HTML, public bid pages, portal-link monitoring, and Bonfire feeds, while source-specific adapters handle sources such as SAM.gov, TxDOT, NYC City Record, JEA, NYPA, and PA eMarketplace.

## Consequences

- New sources can be added without rewriting core opportunity, scoring, or proposal logic.
- Tests can target adapter behavior independently.
- Source health can distinguish live importing sources, missing config, no records, portal-gated sources, and failed jobs.
- Each source still needs careful mapping and validation because public procurement data is inconsistent.
