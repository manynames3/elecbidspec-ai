# ADR 0001: Use a Low-Idle Serverless Deployment Model

## Status

Accepted

## Context

The MVP is intended for a low-traffic pilot where always-on infrastructure would be wasteful. The app still needs a public API, scheduled ingestion, file storage, database persistence, and optional Bedrock calls.

## Decision

Host the frontend as a static Next.js export on Cloudflare Pages. Run the FastAPI backend on AWS Lambda through Mangum, expose it through a Lambda Function URL, and run a separate scheduled Lambda worker through EventBridge. Store uploaded files and Lambda deployment artifacts in private S3 buckets. Use a pooled Postgres connection string for persistence.

## Consequences

- Idle cost stays low compared with ECS, EC2, RDS, or Lightsail-style always-on services.
- The FastAPI app can run locally under Uvicorn and in Lambda with the same route code.
- Lambda cold starts and API timeouts must be considered, especially for proposal generation.
- SQLAlchemy pooling is disabled in Lambda to avoid holding idle database connections.
- Terraform state must be protected because it can contain environment variables.
