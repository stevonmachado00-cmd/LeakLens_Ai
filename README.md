# LeakLens AI - Your AI Financial Copilot

LeakLens AI helps users discover hidden recurring subscriptions, detect silent price increases, calculate a Leak Score, and provide AI-powered recommendations to reduce unnecessary spending.

## Tech Stack

- **Frontend:** Next.js 15, React, TypeScript, Tailwind CSS, shadcn/ui
- **Backend:** FastAPI, Python 3.12, SQLAlchemy, Pydantic
- **Database:** SQLite (canonical path: backend/leaklens.db)

- **AI:** ChromaDB, Sentence Transformers
- **Infrastructure:** Docker, Docker Compose

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.12+ (for local development)
- Node.js 20+ (for local development)

### Running with Docker

```bash
docker-compose up --build
```

The frontend will be available at `http://localhost:3000` and the backend at `http://localhost:8000`.
API documentation can be found at `http://localhost:8000/docs`.

## Statement uploads

The MVP currently accepts UTF-8 CSV files up to 10 MB. Use a header row with
`date`, `merchant`, `description`, `amount`, and `currency`; `category` is optional.
Dates must be ISO-8601 (for example, `2026-07-25`) and currency must be a three-letter code.
PDF statement parsing is not yet available.

### Local Development

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Architecture

- `backend/`: FastAPI application with clean architecture.
- `frontend/`: Next.js application with modern UI components.
- `docs/`: Project documentation.
- `tests/`: Test suites for both frontend and backend.

## Database migrations

Database schema changes are managed with Alembic. Run `alembic upgrade head` from
`backend/` after installing dependencies and whenever the project adds a migration.
The backend does not create tables automatically at application startup.

## License

MIT
