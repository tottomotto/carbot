# CarBot - Car Platform POC

A scalable platform for scraping, enriching, deduplicating, and analyzing car ads.

## Overview

This POC demonstrates the core functionality:
- Targeted car ad scraping (starting with BMW M5 2019+)
- Official data enrichment
- Database storage with Supabase
- FastAPI endpoints for data access

## Tech Stack

- **Python 3.11+** with `uv` for dependency management
- **FastAPI** for API endpoints
- **SQLAlchemy** + **Alembic** for database ORM and migrations
- **Supabase (Postgres)** for database
- **BeautifulSoup4** for web scraping
- **Docker** for containerization
- **Dagster** for orchestration (jobs, UI)

## Setup

### Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) installed
- Supabase account with database credentials

### Installation

1. Clone the repository:
```bash
git clone <your-repo>
cd carbot
```

2. Install dependencies with uv:
```bash
uv sync
```

3. Copy `.env.example` to `.env` and add your credentials:
```bash
cp .env.example .env
# Edit .env with your actual Supabase credentials
```

4. Run database migrations:
```bash
uv run alembic upgrade head
```

5. Start the API server:
```bash
uv run uvicorn api.main:app --reload
```

## Project Structure

```
carbot/
├── api/              # FastAPI application
├── scraper/          # Web scraping modules
├── db/               # Database models and migrations
├── config/           # Configuration files
├── tests/            # Test suite
├── orchestration/    # Dagster jobs and resources
└── docs/             # Documentation
```

## Development

Run tests:
```bash
uv run pytest
```

Format code:
## Orchestration (Dagster)

Run the Dagster UI and launch jobs:
```bash
dagster dev
# In the UI, run `enrichment_job` (folder scan) or `enrichment_db_job` (persist colors)
# New: run `Create deduplicated YOLO dataset and Label Studio import` to build a training set
```

```bash
uv run black .
uv run ruff check .
```

## License

MIT

