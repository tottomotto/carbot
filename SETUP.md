# CarBot Setup Guide

## 🚀 Quick Start

### 1. Update Environment Variables

**IMPORTANT:** You need to update the `.env` file with your actual Supabase password!

Open `.env` and replace `[YOUR-PASSWORD]` with your real password:

```bash
# Before:
DATABASE_PASSWORD=[YOUR-PASSWORD]
DATABASE_URL=postgresql://postgres.ynmmafwpbfzfnojzbrul:[YOUR-PASSWORD]@aws-1-eu-central-1.pooler.supabase.com:6543/postgres

# After (example):
DATABASE_PASSWORD=your_actual_password_here
DATABASE_URL=postgresql://postgres.ynmmafwpbfzfnojzbrul:your_actual_password_here@aws-1-eu-central-1.pooler.supabase.com:6543/postgres
```

### 2. Install Dependencies

```bash
uv sync
```

### 3. Test Database Connection

```bash
uv run python scripts/test_db_connection.py
```

If this succeeds, you're ready to go!

### 4. Create Database Tables

Generate and run the initial migration:

```bash
# Generate migration
uv run alembic revision --autogenerate -m "Initial schema with car_ads tables"

# Apply migration to database
uv run alembic upgrade head
```

Or use the simpler script (creates tables directly):

```bash
uv run python scripts/init_db.py
```

### 5. Start the API Server

```bash
uv run uvicorn api.main:app --reload
```

The API will be available at: http://localhost:8000

- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **DB Health:** http://localhost:8000/health/db

### 6. (Optional) Run with Docker

```bash
# Build and start
docker-compose up --build

# Or run in background
docker-compose up -d
```

## 📁 Project Structure

```
carbot/
├── api/                    # FastAPI application
│   ├── main.py            # API entry point
│   ├── routes/            # API endpoints
│   └── schemas.py         # Pydantic models
├── db/                    # Database layer
│   ├── models.py          # SQLAlchemy models
│   ├── database.py        # DB connection
│   └── migrations/        # Alembic migrations
├── scraper/               # Web scraping
│   ├── main.py           # Scraper runner
│   └── configs/          # Scrape configurations
├── config/                # App configuration
│   └── settings.py       # Settings management
├── scripts/              # Utility scripts
│   ├── check_env.py      # Check environment
│   ├── test_db_connection.py  # Test DB
│   └── init_db.py        # Initialize database
└── tests/                # Test suite
```

## 🗄️ Database Models

### CarAdRaw
Raw scraped car ads with JSONB storage for flexibility.

### CarAdEnriched
Normalized and validated car data with official specifications.

### OfficialCarData
Reference data from OEM sources for validation and enrichment.

## 🔌 API Endpoints

### Health Checks
- `GET /health` - Basic health check
- `GET /health/db` - Database connection check

### Car Ads
- `GET /api/v1/cars/` - List car ads (with filters)
- `GET /api/v1/cars/{id}` - Get specific ad
- `GET /api/v1/cars/{id}/enriched` - Get enriched data
- `GET /api/v1/cars/stats/summary` - Get statistics

## 🕷️ Running the Scraper

```bash
uv run python scraper/main.py
```

Note: The scraper is currently a skeleton. You'll need to implement site-specific scrapers.

## 🧪 Development

### Run Tests
```bash
uv run pytest
```

### Code Formatting
```bash
uv run black .
uv run ruff check .
```

### Type Checking
```bash
uv run mypy .
```

## 📝 Next Steps

1. **Update `.env` with your actual password** ✅
2. **Test database connection**
3. **Run migrations**
4. **Start the API**
5. **Implement your first scraper** (see `scraper/configs/bmw_m5_2019plus.json`)

## 🐛 Troubleshooting

### Database Connection Issues
- Verify your Supabase password is correct in `.env`
- Check that your IP is allowed in Supabase settings
- Ensure you're using the correct pooler URL

### uv Issues
- Make sure uv is installed: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Try removing `.venv` and running `uv sync` again

### Port Already in Use
If port 8000 is taken:
```bash
uv run uvicorn api.main:app --port 8001 --reload
```

## 📚 Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Supabase Documentation](https://supabase.com/docs)
- [uv Documentation](https://github.com/astral-sh/uv)

