# ElecBidSpec AI

ElecBidSpec AI is a full-stack bid intelligence and proposal-prep platform for electrical contractors, GCs, and cable suppliers pursuing public infrastructure work. It ingests fragmented public bid sources and uploaded RFP/spec documents, extracts electrical scope signals, classifies project type, scores each opportunity against a company capability profile, and generates bid-readiness and proposal artifacts.

**Live demo:** https://elecbidspec-ai.pages.dev

**Architecture docs:** [docs/architecture.md](docs/architecture.md)

**Architecture decisions:** [docs/adrs/README.md](docs/adrs/README.md)

![ElecBidSpec AI dashboard preview](frontend/public/assets/elecbidspec-console-preview-dark.svg)

## About

This project was built as an MVP for a realistic B2B workflow: helping electrical infrastructure teams find and qualify high-value public opportunities before the bid window gets crowded. The product problem is fragmented public bid data. Relevant work can be buried in federal postings, state DOT bid-item tables, public utility pages, school authority notices, city/county procurement sites, Bonfire portals, and PDFs with inconsistent titles and value signals.

The app works without live SAM.gov access. Local startup seeds sample electrical/data-center/grid replacement opportunities and a sample company profile, while manual PDF/text upload supports spec extraction and proposal prep from documents found elsewhere.

## Tech Stack

| Area | Technologies |
| --- | --- |
| Frontend | Next.js 15, React 19, TypeScript, static export for Cloudflare Pages |
| Backend | FastAPI, Python, Mangum for AWS Lambda |
| Data | PostgreSQL, SQLAlchemy 2, Alembic migrations, JSON/JSONB for extracted specs and artifacts |
| Ingestion | Adapter registry for SAM.gov, public JSON feeds, public HTML pages, bid-item tables, Bonfire portals, and source-specific public adapters |
| Documents | PDF/text upload, `pypdf` extraction, generated DOCX/PDF proposal outputs |
| AI | Optional Amazon Bedrock proposal enhancement with deterministic fallback |
| Auth | First-party email/password auth, hashed passwords, bearer sessions, admin/user roles, tenant-aware profiles |
| Deployment | Docker Compose locally; Cloudflare Pages frontend; Terraform-managed AWS Lambda Function URL, scheduled Lambda worker, S3 uploads/artifacts, Neon Postgres-compatible database |
| Testing | Pytest coverage for extraction, classification, fit scoring, ingestion adapters, auth, search, alerts, proposals, and source health |

## Engineering Highlights

- Built an extensible ingestion layer where each public source is an adapter, not one hardcoded scraper.
- Normalizes bid records into a common opportunity model with source health, value confidence, project classification, extracted specs, and fit scoring.
- Keeps the MVP useful without third-party keys through seed data, public no-key adapters, and manual RFP/spec upload.
- Separates deterministic proposal generation from optional Bedrock enhancement so demo flows continue when AI services are disabled or unavailable.
- Uses SQLAlchemy/Alembic migrations with tenant-aware records for profiles, workflows, proposal artifacts, alert preferences, and saved searches.
- Implements low-idle deployment with Cloudflare Pages, Lambda Function URL, EventBridge-scheduled worker, S3, and pooled Postgres rather than always-on compute.
- Protects admin ingestion refreshes and mutating job endpoints behind admin auth or a bootstrap token.
- Includes 49 backend tests across core domain logic and ingestion adapter behavior.

## Architecture

The system has three main surfaces:

- A static Next.js frontend hosted on Cloudflare Pages.
- A FastAPI backend that runs locally under Uvicorn or in AWS Lambda through Mangum.
- A scheduled worker that queues and processes ingestion jobs, source refreshes, and alert digests.

See [docs/architecture.md](docs/architecture.md) for a C4-style container diagram, runtime flows, deployment shape, and constraints. See [docs/adrs/README.md](docs/adrs/README.md) for the main architecture decisions.

## Core Features

- Dashboard filters by due date, state, project type, source, value match, and fit score.
- Natural-language search for opportunity discovery.
- Manual PDF/text upload for RFP/spec intake.
- Public source ingestion with health reporting and portal-gated source labels.
- Electrical spec extraction for cable, conduit, trenching, transformer, substation, fiber, data center, emergency repair, and related terms.
- Project classification into data center power, utility replacement, fire damage rebuild, underground installation, overhead/pole installation, substation-related, and general electrical.
- Company fit scoring based on states served, bonding capacity, cable supply, installation capabilities, labor model, and experience.
- Proposal assistant with summary, scope checklist, missing-info checklist, required-documents checklist, risk flags, executive summary, compliance matrix, bid/no-bid memo, partner outreach email, DOCX export, and PDF export.
- Saved searches, watched/saved opportunities, in-app alert digests, and optional SMTP email delivery.

## Public Bid Sources

SAM.gov is optional. The backend treats SAM.gov as one source in a nationwide source registry, not as the whole product.

Default no-key sources include:

- `txdot_bid_items` for Texas DOT official bid item projects with electrical, lighting, conduit, cable, fiber, signal, and related scope
- `pa_emarketplace` for Pennsylvania eMarketplace open solicitations
- `nyc_city_record` for current NYC City Record/Open Data solicitations
- `nyc_school_construction_authority` for NYC School Construction Authority opportunities filtered from the City Record feed
- `sf_open_bids` for San Francisco Open Bid Opportunities
- `la_ramp` through the Los Angeles RAMP Open Bid Opportunities Socrata feed
- `montgomery_md_solicitations` through Montgomery County, MD active solicitations
- `chicago_solicitations` through the public City of Chicago/CTA solicitation table
- `jea_procurement` for JEA public formal/informal solicitation packages grouped by solicitation number
- `bonfire_portal` for Bonfire public portal JSON feeds, including DFW Airport

Keyed sources can also run when the corresponding environment variable is configured:

- `sam_gov` through the SAM.gov Contract Opportunities API using `SAM_GOV_API_KEY` or `SAM_GOV_API_KEY_SECRET_ARN`
- `nypa` through the New York Power Authority public RFQ API using `NYPA_API_SUBSCRIPTION_KEY`

The source catalog also tracks official portals for Caltrans, FDOT, NYSDOT, GDOT, IDOT, Ohio DOT/OhioBuys, NC eVP, VDOT, ADOT, TVA, BPA, LADWP, Austin Energy, CPS Energy, SRP, Port Authority NY/NJ, LA Metro, SEPTA, MTA, University of California, and Houston Public Works. Sources that require a browser session, captcha, supplier portal, or vendor/API access are labeled `portal_gated`; sources routed through another live importer are labeled `covered_by_source`.

The scraper adapter is intentionally conservative: public pages only, HTTP GET requests, configurable selectors, optional detail-page fetches, and no login, captcha bypass, or browser automation.

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

## Local Backend Commands

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic -c alembic.ini upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

Run tests:

```bash
cd backend
pytest
```

## Local Frontend Commands

```bash
cd frontend
npm install
npm run dev
```

Build the static frontend export:

```bash
cd frontend
npm run build
```

## Deployment

### Cloudflare Pages Frontend

The frontend is configured for a static Next.js export so Cloudflare Pages can host it without a Node server.

Recommended Pages settings:

- Root directory: `frontend`
- Build command: `npm run build`
- Build output directory: `out`
- Environment variable: `NEXT_PUBLIC_API_URL=https://your-public-backend.example.com/api`

The deployed frontend cannot call `http://localhost:8000/api`. Deploy the FastAPI backend to a public host first, then set `NEXT_PUBLIC_API_URL` in Cloudflare Pages production and preview environments.

### Low-Idle Production Backend

The MVP uses a low-idle deployment shape:

```text
Cloudflare Pages -> AWS Lambda Function URL -> Neon-compatible pooled Postgres
                                      |
                                      +-> S3 uploads
                                      +-> EventBridge scheduled Lambda worker
                                      +-> Bedrock on demand
```

The FastAPI app runs unchanged on Lambda through Mangum. Terraform manages the AWS resources under `infra/aws-lambda/terraform`:

- Lambda Function URL for the public HTTPS API
- API Lambda for FastAPI
- Scheduled worker Lambda for queued ingestion jobs
- Private S3 bucket for uploaded RFP/spec files
- Private S3 bucket for Lambda deployment artifacts
- IAM role/policies for CloudWatch Logs, S3 uploads, optional Secrets Manager access, and optional Bedrock calls

Use a pooled Postgres connection string for `DATABASE_URL`, especially on Lambda. The app sets `DATABASE_DISABLE_POOL=true` in Lambda so SQLAlchemy does not hold idle local pools across invocations.

Terraform state will contain Lambda environment variables, including `DATABASE_URL` and optional API keys. Keep local `.tfstate` files out of git and use an encrypted remote state backend before sharing this deployment with a team.

Deploy:

```bash
export DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST-pooler.REGION.aws.neon.tech/DB?sslmode=require'
export FRONTEND_ORIGIN='https://elecbidspec-ai.pages.dev'
export AWS_REGION='us-east-1'

./scripts/deploy_lambda_backend.sh
```

The script builds `.build/elecbidspec-ai-backend.zip`, runs `terraform init`, applies the stack, and prints outputs. Set the Cloudflare Pages environment variable to the Terraform output:

```bash
terraform -chdir=infra/aws-lambda/terraform output -raw api_base_url
```

Then set:

```bash
NEXT_PUBLIC_API_URL=<api_base_url>
```

First deploy defaults `BOOTSTRAP_DATABASE_ON_STARTUP=true`, which runs Alembic migrations and seeds the Taihan profile plus sample opportunities on Lambda cold start. After the database is initialized, reduce cold-start work:

```bash
export BOOTSTRAP_DATABASE_ON_STARTUP=false
./scripts/deploy_lambda_backend.sh
```

Required production inputs:

- `DATABASE_URL`, preferably pooled Postgres
- `FRONTEND_ORIGIN=https://elecbidspec-ai.pages.dev`
- `ADMIN_API_TOKEN`, required for manual refresh and custom ingestion job endpoints
- `AUTH_ADMIN_EMAIL` and `AUTH_ADMIN_PASSWORD` if you want a seeded admin login
- `AUTH_USER_EMAIL` and `AUTH_USER_PASSWORD` if you want a seeded standard user login
- `AUTH_REQUIRED=true` when profile/proposal endpoints should require login
- `SAM_GOV_API_KEY` only if live SAM.gov ingestion is enabled locally
- `SAM_GOV_API_KEY_SECRET_ARN` for deployed Lambda when reusing a SAM.gov key stored in AWS Secrets Manager
- `NYPA_API_SUBSCRIPTION_KEY` only if live NYPA utility RFQ ingestion is enabled
- `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `ALERT_EMAIL_FROM` only if daily saved-search emails should send
- `BEDROCK_PROPOSALS_ENABLED=true` only if AI-written proposal drafts should call Bedrock
- `BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6` for Claude Sonnet proposal drafting
- `API_TIMEOUT_SECONDS=120` when deploying Lambda with Sonnet, because proposal generation can take 30-45 seconds

## Auth and Admin Controls

The MVP includes first-party email/password login with hashed passwords, bearer session tokens, `admin` and `user` roles, and tenant-aware company profiles. Seed users are created only from environment variables:

```bash
AUTH_ADMIN_EMAIL=admin@example.com
AUTH_ADMIN_PASSWORD=use-a-generated-password
AUTH_USER_EMAIL=user@example.com
AUTH_USER_PASSWORD=use-a-generated-password
AUTH_SESSION_TTL_HOURS=168
```

Passwords are stored as salted PBKDF2 hashes. Session tokens are stored only as SHA-256 hashes. Set `AUTH_REQUIRED=true` to require login for tenant-specific profile/proposal operations; leave it `false` for public demo mode while still allowing users to sign in.

Manual ingestion refreshes can create outbound requests and mutate production opportunity records, so they are protected. A logged-in user with role `admin` can refresh sources from the dashboard. `ADMIN_API_TOKEN` remains available as a bootstrap or break-glass token.

Protected endpoints accept either:

```bash
Authorization: Bearer $ADMIN_API_TOKEN
```

or:

```bash
X-Admin-Token: $ADMIN_API_TOKEN
```

## Bedrock Proposal Generation

The proposal assistant can use Amazon Bedrock to write company-specific proposal content. When enabled, the backend sends Bedrock the opportunity, extracted specs, fit score, and current company capability profile, then validates the returned JSON against the existing proposal response shape.

```bash
BEDROCK_PROPOSALS_ENABLED=true
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6
BEDROCK_REGION=us-east-1
BEDROCK_MAX_TOKENS=1800
BEDROCK_TEMPERATURE=0.2
```

AWS credentials are not stored in the app. `boto3` uses the normal AWS credential chain, such as environment variables, workload identity, or an instance/container role. If Bedrock is disabled or unavailable, the endpoint falls back to deterministic proposal generation.

## API Surfaces

- `GET /api/opportunities` with filters for due date, state, project type, fit score, estimated value, $5M target match, bid status, source type, and source
- `POST /api/uploads` for manual PDF/text intake
- `POST /api/search` for natural-language opportunity search
- `GET /api/opportunities/{id}/proposal` for proposal-prep output
- `GET /api/opportunities/{id}/proposal.docx` for downloadable DOCX proposal package
- `GET /api/opportunities/{id}/proposal.pdf` for downloadable PDF proposal package
- `GET/PUT /api/company-profile` for fit-scoring capabilities
- `POST /api/auth/login`, `GET /api/auth/me`, and `POST /api/auth/logout` for pilot authentication
- `POST /api/ingestion/jobs` for background ingestion, protected by `ADMIN_API_TOKEN`
- `POST /api/ingestion/refresh-defaults` for protected refresh of all default public sources
- `GET /api/ingestion/summary` for public source coverage and source health counts
- `GET /api/ingestion/adapters` for available ingestion adapters

## Project Structure

```text
backend/
  app/
    api/                FastAPI routes
    services/           extraction, classification, fit scoring, proposals, alerts, ingestion
    services/ingestion/ adapter registry and public source importers
    seed_data/          sample opportunities and company profile
  alembic/              database migrations
  tests/                pytest suite
frontend/
  src/app/              Next.js app routes, dashboard, sales page, Taihan page
  src/components/       dashboard, opportunity, upload, auth, profile components
  public/assets/        dashboard preview asset
infra/aws-lambda/
  terraform/            Lambda, Function URL, EventBridge, S3, IAM resources
scripts/
  deploy_lambda_backend.sh
docs/
  architecture.md
  adrs/
```

## Privacy, Security, and Limitations

- Secrets are loaded from environment variables. No API keys are hardcoded.
- Uploaded files are stored under `UPLOAD_DIR` locally or in the configured private S3 upload bucket in Lambda.
- The public-source ingestion layer avoids login bypasses, captcha bypasses, and browser automation.
- Portal-gated sources are labeled explicitly so source coverage is not overstated.
- SAM.gov and NYPA live ingestion require API keys or subscription keys.
- Bedrock proposal generation is optional and falls back to deterministic generation.
- This is an MVP, not a replacement for legal, compliance, or final estimating review.
