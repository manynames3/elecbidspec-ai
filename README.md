# ElecBidSpec AI

AI-assisted bid intelligence and proposal-prep MVP for electrical cable suppliers and installation contractors.

The app works without live SAM.gov access: Docker startup runs migrations, loads 10 seed opportunities, and creates a sample company capability profile. Users can also upload RFP/spec PDFs or text files for extraction, classification, fit scoring, and proposal draft generation.

## Stack

- Next.js + TypeScript frontend
- FastAPI Python backend
- PostgreSQL
- SQLAlchemy + Alembic migrations
- Docker Compose for local development
- Background worker for queued ingestion jobs

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

## Key API Surfaces

- `GET /api/opportunities` with filters for due date, state, project type, fit score, value, and source
- `POST /api/uploads` for manual PDF/text intake
- `POST /api/search` for natural-language opportunity search
- `GET /api/opportunities/{id}/proposal` for proposal-prep output
- `GET/PUT /api/company-profile` for fit-scoring capabilities
- `POST /api/ingestion/jobs` for background ingestion

## Notes

- Secrets are loaded from environment variables. No API keys are hardcoded.
- Uploaded files are stored under `UPLOAD_DIR`.
- The proposal assistant is deterministic in this MVP. It is structured so an LLM provider can be added later behind the proposal service without changing the API shape.
