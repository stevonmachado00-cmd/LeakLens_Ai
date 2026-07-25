# LeakLens AI - Your AI Financial Copilot

LeakLens AI helps users discover hidden recurring subscriptions, detect silent price increases, calculate a Leak Score, and provide AI-powered recommendations to reduce unnecessary spending.

## Tech Stack

- **Frontend:** Next.js 15, React, TypeScript, Tailwind CSS, shadcn/ui
- **Backend:** FastAPI, Python 3.12, SQLAlchemy, Pydantic
- **Database:** SQLite
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

### Local Development

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
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

## License

MIT
