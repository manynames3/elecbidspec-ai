# ElecBidSpec AI

AI-assisted bid intelligence and proposal-prep MVP for electrical cable suppliers and installation contractors.

The app works without live SAM.gov access: Docker startup runs migrations, loads 10 seed opportunities, and creates a sample company capability profile. Users can also upload RFP/spec PDFs or text files for extraction, classification, fit scoring, and proposal draft generation.

The default dashboard view is tuned for open public electrical opportunities that are confirmed or likely to meet a $5M+ target. Records carry source type, bid status, value confidence, and a short value explanation so SAM.gov can be one source instead of the whole strategy.

The core product problem is fragmented public bid data. Electrical, data-center power, utility replacement, DOT, school, airport, transit, and municipal infrastructure opportunities are spread across dozens of official portals, many with inconsistent titles, tables, PDFs, source links, and value signals. ElecBidSpec AI turns that scattered public layer into a source-aware pursuit workspace.

The nationwide source monitor distinguishes healthy feeds, no-record feeds, missing API keys, and browser-gated portals. Browser-gated means the public portal is reachable for humans but blocks server-side monitoring with a browser challenge, captcha, supplier-system front door, or similar session requirement.

## Stack

- Next.js + TypeScript frontend
- FastAPI Python backend
- PostgreSQL
- SQLAlchemy + Alembic migrations
- Docker Compose for local development
- Background worker for queued ingestion jobs
- Optional saved-search email digests through SMTP
- Terraform-managed AWS Lambda backend for low-idle pilot deployment

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

## Cloudflare Pages Frontend

The frontend is configured for a static Next.js export so Cloudflare Pages can host it without a Node server.

Recommended Pages settings:

- Root directory: `frontend`
- Build command: `npm run build`
- Build output directory: `out`
- Environment variable: `NEXT_PUBLIC_API_URL=https://your-public-backend.example.com/api`

The frontend cannot call `http://localhost:8000/api` after deployment. Deploy the FastAPI backend to a public host first, then set `NEXT_PUBLIC_API_URL` in Cloudflare Pages production and preview environments.

## Low-Idle Production Backend

For the MVP pilot, avoid ECS Fargate, RDS, EC2, and Lightsail unless traffic justifies always-on services. The low-idle path is:

```text
Cloudflare Pages -> AWS Lambda Function URL -> Neon pooled Postgres
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
- IAM role/policies for CloudWatch Logs, S3 uploads, and optional Bedrock calls

Use a Neon pooled connection string for `DATABASE_URL`, especially on Lambda. Neon pooler hostnames usually include `-pooler`; the app also sets `DATABASE_DISABLE_POOL=true` in Lambda so SQLAlchemy does not hold idle local pools across invocations.

Terraform state will contain Lambda environment variables, including `DATABASE_URL` and any optional API keys. Keep local `.tfstate` files out of git and use an encrypted remote state backend before sharing this deployment with a team.

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

First deploy defaults `BOOTSTRAP_DATABASE_ON_STARTUP=true`, which runs Alembic migrations and seeds the Taihan profile plus sample opportunities on Lambda cold start. After the database is initialized, you can reduce cold-start work:

```bash
export BOOTSTRAP_DATABASE_ON_STARTUP=false
./scripts/deploy_lambda_backend.sh
```

Required production inputs:

- `DATABASE_URL`, preferably Neon pooled Postgres
- `FRONTEND_ORIGIN=https://elecbidspec-ai.pages.dev`
- `ADMIN_API_TOKEN`, required for manual refresh and custom ingestion job endpoints
- `AUTH_ADMIN_EMAIL` and `AUTH_ADMIN_PASSWORD` if you want a seeded admin login
- `AUTH_USER_EMAIL` and `AUTH_USER_PASSWORD` if you want a seeded standard user login
- `AUTH_REQUIRED=true` when profile/proposal endpoints should require login
- `SAM_GOV_API_KEY` only if live SAM.gov ingestion is enabled locally
- `SAM_GOV_API_KEY_SECRET_ARN` for deployed Lambda when reusing a SAM.gov key stored in AWS Secrets Manager
- `NYPA_API_SUBSCRIPTION_KEY` only if live NYPA utility RFQ ingestion is enabled
- `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `ALERT_EMAIL_FROM` only if daily saved-search emails should actually send. Without SMTP, digests are still generated in-app and marked `email_unconfigured` when email delivery is requested.
- `BEDROCK_PROPOSALS_ENABLED=true` only if AI-written proposal drafts should call Bedrock
- `BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6` for Claude Sonnet proposal drafting
- `API_TIMEOUT_SECONDS=120` when deploying Lambda with Sonnet, because proposal generation can take 30-45 seconds

## Admin Refresh Controls

Manual ingestion refreshes can create outbound requests and mutate production opportunity records, so they are protected. A logged-in user with role `admin` can refresh sources from the dashboard. `ADMIN_API_TOKEN` remains available as a bootstrap or break-glass token.

Protected endpoints accept either:

```bash
Authorization: Bearer $ADMIN_API_TOKEN
```

or:

```bash
X-Admin-Token: $ADMIN_API_TOKEN
```

The dashboard prompts for this token before running an admin refresh and stores it only in the browser's local storage for that workstation. Public read-only endpoints such as dashboard data, opportunity search, and source health summaries do not require the token.

## Auth

The MVP includes first-party email/password login with hashed passwords, bearer session tokens, `admin` and `user` roles, and tenant-aware company profiles. Seed users are created only from environment variables:

```bash
AUTH_ADMIN_EMAIL=admin@example.com
AUTH_ADMIN_PASSWORD=use-a-generated-password
AUTH_USER_EMAIL=user@example.com
AUTH_USER_PASSWORD=use-a-generated-password
AUTH_SESSION_TTL_HOURS=168
```

Passwords are stored as salted PBKDF2 hashes. Session tokens are stored only as SHA-256 hashes. Set `AUTH_REQUIRED=true` to require login for tenant-specific profile/proposal operations; leave it `false` for public demo mode while still allowing users to sign in.

## Pilot Workflow, Proposals, Alerts, and Documents

The bid detail page supports tenant-aware workflow state: save, watch, hide, pursuit status, owner, priority, and reviewer notes. The dashboard can filter to saved or watched opportunities.

Proposal generation is split into two paths:

- `GET /api/opportunities/{id}/proposal` returns a fast deterministic draft and caches it per tenant.
- `POST /api/opportunities/{id}/proposal/enhance` requires login and calls Bedrock only on demand, then caches the enhanced proposal.

DOCX and PDF downloads use the cached proposal package when available, so downloads do not trigger slow AI calls.

The dashboard includes an alert digest panel backed by:

- `GET/PUT /api/alerts/preferences`
- `POST /api/alerts/run`
- `GET /api/alerts/latest`
- `GET/POST/PUT/DELETE /api/saved-searches`

The alert implementation generates an in-app digest with high-fit opportunities, due-soon opportunities, saved/watched opportunities, saved-search matches, and recent source refresh issues. Scheduled Lambda workers generate at most one alert run per tenant per cooldown window (`ALERT_SEND_COOLDOWN_HOURS`, default 20). Email delivery is optional and uses SMTP environment variables; leaving them blank keeps alerts in-app only.

For attachment intelligence, `POST /api/opportunities/{id}/attachments/ingest` fetches public linked PDFs/text documents from an opportunity source page, stores the files, extracts electrical scope keywords/materials/deadlines/bonding/submission terms, and reclassifies/rescores the opportunity.

## Public Bid Sources

SAM.gov is optional. The backend now treats SAM.gov as one source in a nationwide source registry, not as the whole product. Default no-key sources include:

This registry is designed around fragmented public data sources rather than a single bid board. Each adapter normalizes a different official source shape, such as open-data APIs, public JSON feeds, bid-item tables, agency procurement pages, Bonfire portals, and source-specific public bid pages. That lets the product surface electrical opportunities that employees could technically find by hand, but are unlikely to monitor consistently across many agencies and formats.

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

The source catalog also tracks identified official portals for Caltrans, FDOT, NYSDOT, GDOT, IDOT, Ohio DOT/OhioBuys, NC eVP, VDOT, ADOT, TVA, BPA, LADWP, Austin Energy, CPS Energy, SRP, Port Authority NY/NJ, LA Metro, SEPTA, MTA, University of California, and Houston Public Works. Source-specific public importers are configured for NYSDOT, VDOT, ADOT, SEPTA, Port Authority NY/NJ construction solicitations, and Austin Energy RFPs. Sources that require a browser session, captcha, supplier portal, or vendor/API access are labeled `portal_gated`; sources routed through another live importer, such as BPA through SAM.gov or LADWP through LA RAMP, are labeled `covered_by_source`.

`GET /api/ingestion/summary` reports source health for every configured source. Statuses include `healthy`, `stale`, `failed`, `portal_gated`, `no_current_matches`, `no_records`, `missing_config`, `needs_adapter`, `covered_by_source`, and `directory_only`, so the dashboard can distinguish live importing sources from known coverage targets.

Check SAM.gov status:

```bash
curl http://localhost:8000/api/ingestion/sam-gov/status
```

Verify live SAM.gov ingestion after setting `SAM_GOV_API_KEY` or `SAM_GOV_API_KEY_SECRET_ARN`:

```bash
curl -X POST http://localhost:8000/api/ingestion/sam-gov/verify \
  -H "Authorization: Bearer $ADMIN_API_TOKEN"
```

The app also keeps generic `public_json_feed` and `public_html_scrape` adapters for state, local, utility, school, authority, or other public bid portals. New official feeds can be added by registering another default job in `backend/app/services/ingestion/defaults.py`; most Socrata-style portals only need a URL, field mapping, source label, keyword fields, and status filter.

The Lambda worker refreshes default public sources on a schedule, and the dashboard exposes a manual refresh for the same source set. Established API/table sources process immediately during manual refresh. Generic portal-link monitors are queued for the background worker by default to avoid long admin requests; call `POST /api/ingestion/refresh-defaults?process_portals_inline=true` when you explicitly want to process portal monitors synchronously. Existing source URLs are updated in place so stale records can be reclassified and rescored without duplicating cards.

The scraper adapter is intentionally conservative: public pages only, HTTP GET requests, configurable selectors, optional detail-page fetches, and no login, captcha bypass, or browser automation.

```bash
curl -X POST http://localhost:8000/api/ingestion/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_API_TOKEN" \
  -d '{
    "adapter": "public_json_feed",
    "params": {
      "url": "https://example.gov/bids.json",
      "records_path": "items",
      "source_type": "state_local",
      "mapping": {
        "title": "title",
        "agency": "agency.name",
        "due_date": "closeDate",
        "estimated_value": "budget",
        "source_url": "links.detail"
      }
    }
  }'
```

The MVP value filter uses posted or extracted values when available. If no value is posted, it marks high-scope projects as `likely` when indicators such as data center, hyperscale, AI infrastructure, GPU/HPC compute, critical power, UPS, substation, transmission, high voltage, transformers, switchgear, duct bank, and bonding language suggest the bid may meet the $5M+ threshold.

Available adapters:

- `bonfire_portal` for public Bonfire open-opportunity JSON feeds
- `public_bid_page` for source-configured public bid tables, lists, and JSON pages with embedded HTML tables
- `public_json_feed` for configurable public JSON bid feeds
- `public_html_scrape` for configurable public HTML bid listings
- `public_portal_links` for conservative public portal link monitoring
- `chicago_solicitations` for City of Chicago/CTA public solicitations
- `jea_procurement` for JEA formal/informal solicitation document packages
- `la_ramp` for Los Angeles RAMP public bid opportunities
- `montgomery_md_solicitations` for Montgomery County, MD active solicitations
- `nypa` for New York Power Authority public RFQs
- `nyc_city_record` for NYC City Record solicitations
- `pa_emarketplace` for Pennsylvania eMarketplace open solicitations
- `sf_open_bids` for San Francisco Open Bid Opportunities
- `txdot_bid_items` for Texas DOT official bid item projects
- `sam_gov` for federal Contract Opportunities

Example HTML scrape job:

```bash
curl -X POST http://localhost:8000/api/ingestion/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_API_TOKEN" \
  -d '{
    "adapter": "public_html_scrape",
    "params": {
      "url": "https://example.gov/procurement",
      "record_selector": "article.bid-card",
      "source_type": "state_local",
      "field_selectors": {
        "title": "a.notice-link",
        "source_url": "a.notice-link@href",
        "agency": ".agency",
        "due_date": ".due"
      },
      "detail_field_selectors": {
        "description": ".scope",
        "estimated_value": ".value",
        "state": ".state"
      }
    }
  }'
```

## SAM.gov Ingestion

Add a SAM.gov API key to `.env`:

```bash
SAM_GOV_API_KEY=your_key_here
```

Then create an ingestion job from the API docs or with curl:

```bash
curl -X POST http://localhost:8000/api/ingestion/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_API_TOKEN" \
  -d '{"adapter":"sam_gov","params":{"limit":10,"keyword":"medium voltage cable"}}'
```

The worker service polls queued jobs and imports normalized opportunities. Additional state or local bid portals can be added as new classes implementing `IngestionAdapter` under `backend/app/services/ingestion`.

## Bedrock Proposal Generation

The proposal assistant can use Amazon Bedrock to write company-specific proposal content. When enabled, the backend sends Bedrock the opportunity, extracted specs, fit score, and the current company capability profile, then validates the returned JSON against the existing proposal response shape.

```bash
BEDROCK_PROPOSALS_ENABLED=true
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6
BEDROCK_REGION=us-east-1
BEDROCK_MAX_TOKENS=1800
BEDROCK_TEMPERATURE=0.2
```

Claude Sonnet 4.6 uses a Bedrock inference profile ID here because direct on-demand invocation is not supported for this model in the current AWS account. AWS credentials are not stored in the app. `boto3` uses the normal AWS credential chain, such as environment variables, workload identity, or an instance/container role. If Bedrock is disabled or unavailable, the endpoint falls back to deterministic proposal generation.

The seed profile is configured for Taihan Cable & Solution so proposal drafts are grounded in its cable and power infrastructure capability profile instead of a generic contractor profile. The seeded bonding capacity is user-configured profile context, not a public-source claim, and is currently set to `$600,000,000`.

Proposal output includes:

- Bid summary
- Scope checklist
- Missing information checklist
- Required documents checklist
- Risk flags
- Draft executive summary
- Compliance matrix
- Bid/no-bid memo
- Partner outreach email
- Downloadable DOCX package from `GET /api/opportunities/{id}/proposal.docx`
- Downloadable PDF package from `GET /api/opportunities/{id}/proposal.pdf`

## Key API Surfaces

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

## Notes

- Secrets are loaded from environment variables. No API keys are hardcoded.
- Uploaded files are stored under `UPLOAD_DIR`.
- The proposal assistant uses Bedrock when enabled and falls back to deterministic proposal generation when Bedrock is disabled or unavailable.
