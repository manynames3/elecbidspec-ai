# ElecBidSpec AI

AI-assisted bid intelligence and proposal-prep MVP for electrical cable suppliers and installation contractors.

The app works without live SAM.gov access: Docker startup runs migrations, loads 10 seed opportunities, and creates a sample company capability profile. Users can also upload RFP/spec PDFs or text files for extraction, classification, fit scoring, and proposal draft generation.

The default dashboard view is tuned for open public electrical opportunities that are confirmed or likely to meet a $5M+ target. Records carry source type, bid status, value confidence, and a short value explanation so SAM.gov can be one source instead of the whole strategy.

## Stack

- Next.js + TypeScript frontend
- FastAPI Python backend
- PostgreSQL
- SQLAlchemy + Alembic migrations
- Docker Compose for local development
- Background worker for queued ingestion jobs
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
- `SAM_GOV_API_KEY` only if live SAM.gov ingestion is enabled
- `BEDROCK_PROPOSALS_ENABLED=true` only if AI-written proposal drafts should call Bedrock

## Public Bid Sources

SAM.gov is optional. For state, local, utility, school, authority, or other public bid portals, use `public_json_feed` when a portal exposes JSON and `public_html_scrape` when a portal only exposes public HTML listing/detail pages.

The scraper adapter is intentionally conservative: public pages only, HTTP GET requests, configurable selectors, optional detail-page fetches, and no login, captcha bypass, or browser automation.

```bash
curl -X POST http://localhost:8000/api/ingestion/jobs \
  -H "Content-Type: application/json" \
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

The MVP value filter uses posted or extracted values when available. If no value is posted, it marks high-scope projects as `likely` when indicators such as data center, substation, transmission, high voltage, transformers, switchgear, duct bank, and bonding language suggest the bid may meet the $5M+ threshold.

Available adapters:

- `public_json_feed` for configurable public JSON bid feeds
- `public_html_scrape` for configurable public HTML bid listings
- `sam_gov` for federal Contract Opportunities

Example HTML scrape job:

```bash
curl -X POST http://localhost:8000/api/ingestion/jobs \
  -H "Content-Type: application/json" \
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
  -d '{"adapter":"sam_gov","params":{"limit":10,"keyword":"medium voltage cable"}}'
```

The worker service polls queued jobs and imports normalized opportunities. Additional state or local bid portals can be added as new classes implementing `IngestionAdapter` under `backend/app/services/ingestion`.

## Bedrock Proposal Generation

The proposal assistant can use Amazon Bedrock to write company-specific proposal content. When enabled, the backend sends Bedrock the opportunity, extracted specs, fit score, and the current company capability profile, then validates the returned JSON against the existing proposal response shape.

```bash
BEDROCK_PROPOSALS_ENABLED=true
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
BEDROCK_REGION=us-east-1
```

AWS credentials are not stored in the app. `boto3` uses the normal AWS credential chain, such as environment variables, workload identity, or an instance/container role. If Bedrock is disabled or unavailable, the endpoint falls back to deterministic proposal generation.

The seed profile is configured for Taihan Cable & Solution so proposal drafts are grounded in its cable and power infrastructure capability profile instead of a generic contractor profile.

## Key API Surfaces

- `GET /api/opportunities` with filters for due date, state, project type, fit score, estimated value, $5M target match, bid status, source type, and source
- `POST /api/uploads` for manual PDF/text intake
- `POST /api/search` for natural-language opportunity search
- `GET /api/opportunities/{id}/proposal` for proposal-prep output
- `GET/PUT /api/company-profile` for fit-scoring capabilities
- `POST /api/ingestion/jobs` for background ingestion
- `GET /api/ingestion/adapters` for available ingestion adapters

## Notes

- Secrets are loaded from environment variables. No API keys are hardcoded.
- Uploaded files are stored under `UPLOAD_DIR`.
- The proposal assistant is deterministic in this MVP. It is structured so an LLM provider can be added later behind the proposal service without changing the API shape.
