**blueprint.md**

***

# Car Platform Project Blueprint

## **Project Goal**

To build a scalable, configurable platform for scraping, enriching, deduplicating, and analyzing car ads, supporting specific car queries (e.g., “BMW M5 F90 after 2019”), cross-referencing with official data sources, and serving actionable arbitrage insights for B2C and B2B users.

***

## **Core Architecture Overview**

- **Monorepo:** All code, configs, and assets in one repository.
- **Containerized:** Each service Dockerized, orchestrated locally with Docker Compose.
- **Dagster:** Modern orchestrator for pipelines—targeted crawling, enrichment, deduplication, analytics, monitoring.
- **Postgres Database:** Raw (jsonb), enriched (structured), dedup map tables.
- **ML YOLO:** Image feature extraction to identify car features and enhance deduplication.
- **API (FastAPI):** Public, partner, and admin endpoints.
- **Operational Dashboards:** Dagster UI for pipelines; Grafana/Prometheus for custom metrics and alerts.
- **Comprehensive Scrape Configurations & Official Data:** Supports highly-selective scraping for only specific makes/models/years. Official data gathered and used for cross-referencing.

***

## **Folder Structure**

```plaintext
car-platform-monorepo/
├── blueprint.md
├── tasks.md
├── requirements.md
├── design.md
├── docker-compose.yml
├── dagster/
│   ├── jobs.py
│   ├── assets.py
│   ├── resources.py
├── scraper/
│   ├── main.py
│   ├── configs/
│   │   ├── bmw_m5_2019plus.json
│   │   └── porsche_cayenne_2020plus.json
│   ├── sites/
│   └── download_images.py
├── official_data/
│   ├── fetch_oem_data.py
│   └── features_db.json
├── ml/
│   ├── yolo_runner.py
│   ├── feature_extractor.py
│   └── model_configs/
├── deduplication/
│   └── scorer.py
├── api/
│   ├── main.py
│   ├── routes/
│   └── schemas.py
├── db/
│   ├── migrations/
│   ├── schema.sql
│   └── seed_data.sql
├── monitoring/
│   ├── grafana/
│   ├── prometheus.yml
├── scripts/
│   ├── backup_db.sh
│   ├── health_check.py
├── config/
│   ├── development.yaml
│   ├── production.yaml
│   └── feature_flags.yaml
├── tests/
│   ├── test_*.py
├── docs/
│   ├── API.md
│   ├── DEPLOYMENT.md
│   └── CONTRIBUTING.md
└── .github/workflows/
```

***

## **Component & Flow Highlights**

1. **Targeted Scraping**
   - Reads search configs (by site, car model/year, etc.) for granular queries.
   - Scraper knows how to only fetch relevant models/years per site.
   - Each scrape job is configuration-driven and easily extensible.
2. **Official Data Sync**
   - Fetches valid trims/options/features/colors from OEM sites/APIs/vehicle DBs.
   - Updates canonical tables used in all enrichment.
3. **Image & Metadata Enrichment**
   - ML (YOLO) extracts car features from images.
   - Raw JSON merged with normalized, validated information.
   - Enriched with official options/terminology.
4. **Deduplication**
   - Uses image and metadata similarity for high-accuracy duplicate detection.
   - Maps logical cars (even if listed in multiple places).
5. **Arbitrage & Analytics**
   - Identifies outliers and opportunities based on enriched, deduped data.
   - Simple views/exports for further analysis or automated action.
6. **API & Dashboard**
   - FastAPI for user and partner programmatic access.
   - Internal admin endpoints for job/data management.
7. **Monitoring**
   - Dagster UI for job status/logs.
   - Grafana dashboards for scraping health, ML ops, deduplication rates, system metrics.

***

## **Design Principles**

- **Configurable, Granular Scraping:** Only fetches what’s relevant, avoids bans, stays efficient.
- **Reference-Driven Data Quality:** Normalization and deduplication powered by authoritative data.
- **Horizontally Scalable:** Multiple scrapers and ML jobs running in parallel.
- **Agile Deliverables:** Each phase brings visible, testable functionality.
- **Resilient, Monitored, and Secure:** Error handling, monitoring, compliance, and robust access controls throughout.

***

## **Technology Choices**

- Python, Docker, Dagster, YOLO, Postgres, FastAPI, Grafana, Prometheus, MLflow (optional)

***

# tasks.md

***

# Car Platform Agile Task List

## **Phase 0: Repository & Setup**
- [ ] Create repo, folder structure, and initial config placeholders
- [ ] Write and commit blueprint, tasks, requirements, and design docs

***

## **Phase 1: Targeted Scraper MVP**
- [ ] Implement scraper runner that loads job configs (per make/model/year)
- [ ] Implement one job config (e.g., BMW M5 F90 2019+ for one site)
- [ ] Parse paginated results using targeted search params
- [ ] Store raw results to `car_ads_raw` table (jsonb)
- [ ] Save images and reference locations in raw table
- [ ] Minimal quality checks (nulls, missing images)
- [ ] Provide initial admin CLI to launch targeted scrapes

***

## **Phase 2: Official Data/Reference Layer**
- [ ] Implement job to fetch valid trims/options/colors from at least one OEM/vehicle data API
- [ ] Structure as canonical options DB/table
- [ ] Add mapping logic to relate scraped metadata to official values

***

## **Phase 3: ML Feature Extraction**
- [ ] Add YOLO runner for image processing and feature extraction
- [ ] Log per-image confidence and failed/excluded cases
- [ ] Store extracted features as structured fields in `car_ads_enriched`
- [ ] Test with actual images and verify feature mapping

***

## **Phase 4: Metadata Normalization**
- [ ] Write parser to extract year, generation, trim, etc., from raw ads
- [ ] Map to official terminology using reference data from Phase 2
- [ ] Populate/convert raw -> enriched records, with data validation

***

## **Phase 5: Deduplication & Similarity**
- [ ] Write textual and image similarity scoring modules
- [ ] Implement deduplication job linking similar ads
- [ ] Create mapping table for unique/logical vehicles

***

## **Phase 6: Arbitrage & Analytics**
- [ ] Basic price outlier detection for enriched/unique vehicles
- [ ] Simple reporting/export endpoint (CSV, JSON)
- [ ] Notifications or data feed for arbitrage opportunities

***

## **Phase 7: API & Dashboards**
- [ ] Implement FastAPI endpoints for B2C, B2B, and admin
- [ ] Build Grafana dashboards for scraping stats, ML feature extraction, deduplication health
- [ ] Integrate Dagster UI into development setup

***

## **Phase 8: Monitoring, Security, & Resilience**
- [ ] Integrate Prometheus metrics into all services
- [ ] Add error, health, and anomaly alerting
- [ ] Implement retries, DLQ, fallback for all critical jobs
- [ ] Secure API access, secrets, and DB connections

***

## **Continuous Delivery (Sprint Cycle)**
- [ ] Add further job configs (different models, years, sites)
- [ ] Improve ML models and reference data mapping
- [ ] Enhance feature extraction and analytics sophistication
- [ ] Add unit, integration, and E2E tests
- [ ] Expand documentation

***

**How to use:**  
Incrementally build and test each phase, ensuring each delivers visible and actionable progress (e.g., running a real targeted scrape or enrichment job after Phase 1). Only proceed once outcomes are validated. Adjust planned tasks based on system feedback, blockers, or changing priorities.

***

If you need a sample targeted scrape config, job logic, or reference data-fetcher, let me know the priority!