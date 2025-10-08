**blueprint.md**

***

# Car Platform Project Blueprint

## **Project Goal**

To build a scalable, configurable platform for scraping, enriching, deduplicating, and analyzing car ads, supporting specific car queries (e.g., “BMW M5 F90 after 2019”), cross-referencing with official data sources, and serving actionable arbitrage insights for B2C and B2B users.

***

## **Core Architecture Overview**

- **Monorepo:** All code, configs, and assets in one repository.
- **Containerized:** Each service Dockerized, orchestrated locally with Docker Compose.
- **Scripts-first Orchestration:** Site-specific Playwright crawlers run as standalone scripts for reliability under bot detection; later wrapped as Dagster ops/jobs once flows stabilize.
- **Database (Postgres/Supabase):** Ad and image metadata tracked via Supabase (Postgres), including image paths/URIs, source site, crawler status, labels, and model outputs.
- **Object Storage (Local → S3):** Images stored locally for now; migrate to S3 soon (e.g., `s3://bucket/models/<dataset>/...`). Metadata always references canonical storage URIs.
- **Labeling Platform (Label Studio):** Human-in-the-loop annotation, with optional auto-label bootstrapping from ad metadata.
- **Custom Vision Models:** Train our own models (YOLO11m/ViT or similar); prior YOLO baseline deemed insufficiently accurate.
- **API (FastAPI):** Public, partner, and admin endpoints.
- **Operational Dashboards:** Grafana/Prometheus for custom metrics and alerts; Dagster UI once jobs are formalized.
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
├── dagster/              # Defer: wrap stabilized scripts into ops/jobs later
│   ├── jobs.py
│   ├── assets.py
│   ├── resources.py
├── scraper/
│   ├── main.py           # Entry points for scripts-first runners
│   ├── configs/
│   │   ├── bmw_m5_2019plus.json
│   │   └── porsche_cayenne_2020plus.json
│   ├── sites/
│   │   ├── mobile_bg.py
│   │   └── collecting_cars_pw.py  # Example Playwright crawler
│   ├── playwright/
│   │   └── helpers.py    # Anti-bot/hardening utilities (headers, delays, retries)
│   └── download_images.py
├── official_data/
│   ├── fetch_oem_data.py
│   └── features_db.json
├── ml/
│   ├── yolo_runner.py
│   ├── feature_extractor.py
│   └── model_configs/
├── datasets/
│   ├── raw/              # Raw images collected by crawlers (local now → S3 later)
│   ├── label_studio/     # Project exports/imports, tasks, configs
│   └── exports/          # Training-ready datasets (YOLO/COCO/VOC, etc.)
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
│   └── storage_migrate_to_s3.py  # Local→S3 migration utility (planned)
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

1. **Site-Specific Crawlers (Playwright, scripts-first)**
   - Per-site Playwright scripts hardened against bot detection (headers, realistic delays, retries, IP hygiene).
   - Two primary modes per site: Ads ingestion (structured metadata + images) and Training data accumulation (images with inferred labels from ad text/spec).
   - Config-driven scope: make/model/year/region; resilient to layout changes via selectors and validations.
2. **Official Data Sync**
   - Fetches valid trims/options/features/colors from OEM sites/APIs/vehicle DBs.
   - Updates canonical tables used in all enrichment.
3. **Image & Metadata Enrichment**
   - Custom-trained vision models extract car features. Start with YOLO11m/ViT; iterate beyond YOLO baseline due to accuracy constraints.
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
   - Scripts emit metrics/logs; Grafana dashboards for scraping health, ML ops, deduplication rates, system metrics.
   - Dagster UI comes later when scripts are wrapped into jobs.

***

## **End-to-End Data Flow**

```plaintext
[Scraping Trigger] → Scripts-first Crawler (Playwright: Scrape & Ingest)
                    ↓
Supabase (Metadata: image_path, model, status="raw")
                    ↓
Local FS → S3 Bucket soon (Images: e.g., s3://your-bucket/models/bmw_m5_f90/image_001.jpg)
                    ↓
Label Studio (Annotation Toolkit: Auto-label + Manual Review)
                    ↓
Supabase (Updated Metadata: annotations, confidence, status="labeled/cleaned")
                    ↓
Export to Training (e.g., YOLO11m/ViT datasets)
```

Notes:
- Start with local filesystem for images and migrate to S3 shortly; metadata always stores canonical URIs for portability.
- Ad-sourced labels serve as weak supervision to bootstrap Label Studio tasks.
- Crawlers can run in either ingest or dataset-accumulation mode depending on trigger.

***

## **Image Dataset Management**

Storage layout (local now → S3 near-term):

- Local: `datasets/raw/<make>_<model>_<gen>/...` and `datasets/exports/...`
- S3 (planned): `s3://<bucket>/datasets/raw/<make>_<model>_<gen>/...`
- Canonical URIs stored in Supabase, e.g., `image_uri` as `file://...` or `s3://...`

Supabase metadata (proposed fields):

- ads: `id`, `source_site`, `source_url`, `title`, `price`, `currency`, `location`, `spec_json`, `created_at`
- images: `id`, `ad_id`, `image_uri`, `checksum`, `width`, `height`, `status` (raw|labeled|cleaned), `labels_bootstrap` (from ad), `annotations` (Label Studio export ref), `model_predictions`, `created_at`, `updated_at`

Label Studio conventions:

- One project per dataset/model scope (e.g., `bmw_m5_f90_features`)
- Ontology versioned in repo under `datasets/label_studio/<project>/ontology.json`
- Imports reference `image_uri` directly; exports saved under `datasets/exports/<project>/<date>/...`

Data quality and governance:

- Enforce deterministic pathing and file checksums to avoid dupes
- Periodic validation job compares Supabase metadata to storage and Label Studio exports
- Migration utility updates `image_uri` from local to S3 and backfills missing fields

## **Design Principles**

- **Configurable, Granular Scraping:** Only fetches what’s relevant, avoids bans, stays efficient.
- **Reference-Driven Data Quality:** Normalization and deduplication powered by authoritative data.
- **Horizontally Scalable:** Multiple scrapers and ML jobs running in parallel.
- **Agile Deliverables:** Each phase brings visible, testable functionality.
- **Resilient, Monitored, and Secure:** Error handling, monitoring, compliance, and robust access controls throughout.

***

## **Technology Choices**

- Python, Docker, Playwright (Python), Supabase (Postgres), Local FS → S3 (near-term), Label Studio, Custom Vision Models (YOLO11m/ViT), FastAPI, Grafana, Prometheus, Dagster (later), MLflow (optional)

***

# tasks.md

***

# Car Platform Agile Task List

## **Phase 0: Repository & Setup**
- [ ] Create repo, folder structure, and initial config placeholders
- [ ] Write and commit blueprint, tasks, requirements, and design docs

***

## **Phase 1: Site Crawler MVP (Scripts-First)**
- [ ] Implement Playwright crawler per site (e.g., mobile.de, collecting-cars) with anti-bot hardening
- [ ] Support two modes: Ads ingestion and Training data accumulation
- [ ] Persist ad metadata to Supabase (status="raw", image_path URIs)
- [ ] Download images to local filesystem with stable path scheme (future S3)
- [ ] Minimal quality checks (nulls, missing images, broken pages)
- [ ] Provide admin CLI or script triggers to run crawlers per site/model/year

***

## **Phase 2: Labeling Pipeline & Dataset Management**
- [ ] Stand up Label Studio and create projects per dataset/model
- [ ] Import tasks from Supabase metadata with weak labels from ads (when applicable)
- [ ] Define labeling ontology consistent with training targets (bounding boxes/segmentation/classes)
- [ ] Round-trip annotations back to Supabase (annotations, confidence, status)
- [ ] Export labeled datasets in YOLO/COCO/VOC as needed

***

## **Phase 3: Model Training & Evaluation**
- [ ] Create training pipelines for YOLO11m/ViT using exported datasets
- [ ] Implement experiment tracking and evaluation metrics (mAP, recall, precision)
- [ ] Iterate on data quality and labeling to improve accuracy

## **Phase 4: Official Data/Reference Layer**
- [ ] Implement job to fetch valid trims/options/colors from at least one OEM/vehicle data API
- [ ] Structure as canonical options DB/table
- [ ] Add mapping logic to relate scraped metadata to official values

***

## **Phase 5: Metadata Normalization & Enrichment**
- [ ] Parse year, generation, trim, etc., from raw ads and images
- [ ] Apply trained model outputs to enrich ads with high-detail features
- [ ] Map to official terminology using reference data; populate raw → enriched with validation

***

## **Phase 6: Deduplication & Similarity**
- [ ] Write textual and image similarity scoring modules
- [ ] Implement deduplication job linking similar ads
- [ ] Create mapping table for unique/logical vehicles

***

## **Phase 7: Arbitrage & Analytics**
- [ ] Basic price outlier detection for enriched/unique vehicles
- [ ] Simple reporting/export endpoint (CSV, JSON)
- [ ] Notifications or data feed for arbitrage opportunities

***

## **Phase 8: API & Dashboards**
- [ ] Implement FastAPI endpoints for B2C, B2B, and admin
- [ ] Build Grafana dashboards for scraping stats, ML feature extraction, deduplication health
- [ ] Integrate Dagster UI once scripts are wrapped as ops/jobs

***

## **Phase 9: Monitoring, Security, & Resilience**
- [ ] Integrate Prometheus metrics into all services
- [ ] Add error, health, and anomaly alerting
- [ ] Implement retries, DLQ, fallback for all critical jobs
- [ ] Secure API access, secrets, and DB connections

## **Phase 10: Storage Migration to S3**
- [ ] Migrate image storage from local FS to S3; validate URIs in Supabase
- [ ] Backfill existing datasets and update Label Studio import paths
- [ ] Add lifecycle policies and cost controls

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