# CarBot POC - Current Status

## ✅ Completed

### Infrastructure
- [x] Complete folder structure created
- [x] `pyproject.toml` configured with `uv` for dependency management
- [x] `.env` file template with Supabase configuration
- [x] `.gitignore` for Python/Docker projects
- [x] Docker setup (`Dockerfile` + `docker-compose.yml`)
- [x] Dependencies installed via `uv`
 - [x] Static files mounted for serving downloaded images

### Database Layer
- [x] SQLAlchemy models defined:
  - `CarAdRaw` - Raw scraped data with JSONB
  - `CarAdEnriched` - Normalized/enriched data
  - `OfficialCarData` - Reference data from OEMs
- [x] Database connection configuration
- [x] Alembic migrations setup
- [x] Utility scripts for DB initialization and testing
 - [x] Added `local_image_paths` field and migration

### API Layer
- [x] FastAPI application structure
- [x] Health check endpoints (`/health`, `/health/db`)
- [x] Car ad endpoints:
  - List ads with filtering
  - Get specific ad
  - Get enriched data
  - Statistics summary
- [x] Pydantic schemas for request/response
- [x] CORS middleware configured
 - [x] ML endpoints: image analysis, market analysis, anomaly detection, price model training
 - [x] Web UI shows anomaly badges and supports "show anomalies only" filter

### Scraper Layer
- [x] Basic scraper runner structure
- [x] Configuration-driven architecture
- [x] Example config for BMW M5 2019+
- [x] Database integration for storing scraped data
- [x] Anti-ban features (delays, user agents)
 - [x] Intelligent extractor (multi-language regex + scoring) replacing brittle CSS selectors
 - [x] Stable dedup via `source_site` + consistent `source_id`
 - [x] Image detection (including lazy/relative URLs), download, deduplication, linking to ads

### Documentation
- [x] README.md with project overview
- [x] SETUP.md with detailed setup instructions
- [x] Blueprint and tasks preserved
 - [x] Added ML dashboard page and status endpoints

## 🚧 To Do Next (POC-focused)

### Immediate
1. Train the price prediction model with current dataset (`POST /api/v1/ml/train-price-model`)
2. Improve field extraction quality (engine displacement, dealer name normalization)
3. Add basic caching/batching to anomaly endpoint for performance

### Phase A - Image Recognition (YOLO)
- [ ] Add YOLO runtime (Ultralytics) dependency and simple runner
- [ ] Prepare dataset sampler from `scraped_images/` (resizing, format, metadata)
- [x] Heuristic color inference via OpenCV HSV masks (POC)
- [x] Persist `detected_color` and `detected_color_confidence` to `CarAdEnriched`
- [ ] Run YOLO on first image per ad to extract: body style, color, damage cues, badge/logo detection
- [ ] Store YOLO outputs in `CarAdEnriched` (new columns: `detected_body_style`, `damage_score`, `features_json`)
- [ ] Surface detections in UI (badges + details panel)

### Phase B - Orchestration (Dagster - initial stage)
- [x] Add Dagster minimal repo and UI (`dagster dev`) with `workspace.yaml`
- [x] Create `enrichment_job` (folder scan report) and `enrichment_db_job` (persist colors)
- [ ] Create `scrape_bmw_m5` job: config → scrape → save → images
- [ ] Create `image_inference` job: iterate new ads → run YOLO → persist enriched fields
- [ ] Add schedules/sensors for periodic runs and backfills
- [ ] Expose Dagster UI via docker-compose

### Phase C - Enrichment (tie to YOLO + reference)
- [ ] Map YOLO `detected_color`/`body_style` → normalized values
- [ ] Add heuristic VIN/trim inference from title + detections
- [ ] Persist confidence scores per enrichment field

### Future Phases
- Cross-site scaling (AutoTrader, mobile.de)
- Advanced dedup (image+text similarity)
- Arbitrage analysis and alerts
- Production monitoring (Prometheus/Grafana)

## 📊 Current Statistics

```
Files Created: 60+
Lines of Code: ~2,500
Dependencies: 45+ packages (added numpy, OpenCV, scikit-learn, pandas, Dagster)
Database Models: 3 (+ new columns)
API Endpoints: 12+ (incl. ML)
Docker Services: 2 (api + optional local db); Dagster running via `dagster dev`
```

## 🎯 POC Success Criteria

1. ✅ Infrastructure set up
2. ✅ Scrape and persist listings with images from one site
3. ✅ Serve listings + images via API and web UI
4. ✅ Add ML layer: anomaly detection, market analysis, image condition heuristics
5. ✅ Heuristic color inference integrated and persisted (11 enriched rows)
6. ⏳ Dagster orchestrates scrape → image → inference pipelines
7. ⏳ Official BMW data integration (specs) for 10+ ads

## 🚀 Quick Commands

```bash
# Check environment
uv run python scripts/check_env.py

# Test database
uv run python scripts/test_db_connection.py

# Initialize database
uv run python scripts/init_db.py

# Start API
uv run uvicorn api.main:app --reload

# Run scraper
uv run python scraper/main.py

# Docker
docker-compose up --build
```

## 📝 Notes

- Using **Supabase** (cloud Postgres) instead of local DB for easier setup
- **uv** for fast, modern Python dependency management
- **SQLAlchemy + Alembic** for ORM and migrations
- **FastAPI** for modern, auto-documented API
- **Docker** ready for production deployment
- Configuration-driven scraping for easy extensibility

## 🔗 Important Links

- Local API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Supabase Dashboard: https://supabase.com/dashboard

---

**Next Action:** Update `.env` file with your actual Supabase password and run the database connection test!

