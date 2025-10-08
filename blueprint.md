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
- **Database (Postgres/Supabase):** A normalized relational schema with canonical tables (`Manufacturer`, `Model`, `Variant`), a master record for each physical vehicle (`UniqueCar`), and tables for transactional data (`Ad`, `Image`).
- **Object Storage (Checksum-based, Local → S3):** Images are stored using a content-addressable path derived from their checksum for automatic deduplication. Stored locally for now, with a clear path to S3 migration.
- **Labeling Platform (Label Studio):** Human-in-the-loop annotation, with optional auto-label bootstrapping from ad metadata.
- **Custom Vision Models:** Train our own models (YOLO11m/ViT or similar); prior YOLO baseline deemed insufficiently accurate.
- **API (FastAPI):** Public, partner, and admin endpoints.
- **Operational Dashboards:** Grafana/Prometheus for custom metrics and alerts; Dagster UI once jobs are formalized.
- **Comprehensive Scrape Configurations & Official Data:** Supports highly-selective scraping for specific makes/models/years. Official data is used to populate the canonical database tables.

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
│   ├── schema.sql      # Illustrative, not authoritative. Migrations are the source of truth.
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

1.  **Site-Specific Crawlers (Ingestion)**
    - Per-site Playwright scripts ingest raw ad data into the `ads` table. At this stage, the `unique_car_id` is `NULL`.
    - Images are downloaded, checksummed, and saved to content-addressable storage. An `images` record is created linking the image to the ad.
2.  **Canonical Data Sync (Reference Layer)**
    - Jobs to fetch valid manufacturers, models, and variants from official sources (OEM sites, data APIs) to populate our canonical tables.
3.  **Metadata Enrichment**
    - A dedicated process parses raw text from `ads` (e.g., "F/S 2022 M5 Comp") and maps it to the canonical `variant_id` from our reference tables.
4.  **Deduplication & Clustering**
    - A similarity engine analyzes ads using VIN, image checksums, and other metadata to identify multiple listings for the same physical car.
    - When a cluster of ads is identified, a master `unique_cars` record is created, and all associated `ads` are updated with the `unique_car_id`.
5.  **Custom Vision Model Enrichment**
    - Custom-trained vision models extract high-quality features (e.g., validated color, detected damage) from images.
6.  **Arbitrage & Analytics**
    - With a clean, deduplicated dataset of unique cars, we can accurately track price history, time on market, and identify investment opportunities.
7.  **API & Dashboard**
   - FastAPI for user and partner programmatic access.
   - Internal admin endpoints for job/data management.
8. **Monitoring**
   - Scripts emit metrics/logs; Grafana dashboards for scraping health, ML ops, deduplication rates, system metrics.
   - Dagster UI comes later when scripts are wrapped into jobs.

***

## **End-to-End Data Flow**

The data lifecycle is a multi-step process from raw ingestion to actionable insight.

```plaintext
[Scraping] → Ad Ingestion (raw text, unique_car_id=NULL)
     ↓
[Enrichment] → Map raw text to Canonical Variant ID
     ↓
[Deduplication] → Cluster Ads, Create UniqueCar, Link Ads
     ↓
[Labeling] → Label Studio (Annotate Images)
     ↓
[Training] → Train Custom Models (e.g., Color, Damage)
     ↓
[Analysis] → Query UniqueCar data for Arbitrage
```

Notes:
- Start with local filesystem for images and migrate to S3 shortly; metadata always stores canonical URIs for portability.
- Ad-sourced labels serve as weak supervision to bootstrap Label Studio tasks.
- Crawlers can run in either ingest or dataset-accumulation mode depending on trigger.

***

## **Image Dataset Management**

Storage layout (local now → S3 near-term):

- **Primary Storage:** Images are stored in a content-addressable (checksum-based) path. e.g., `datasets/storage/ab/cd/abcdef123...jpg`. This path is immutable and guarantees deduplication.
- **Working Directories:** For ML training or analysis, scripts will create temporary directories of symlinks to provide a clean, human-readable dataset for a specific task. e.g., `datasets/exports/bmw-m5-cs-color-v1/`.
- **Canonical URIs:** The `images.image_uri` column in the database stores the canonical path (`file://...` or `s3://...`) to the file in primary storage.

Label Studio conventions:

- One project per dataset/model scope (e.g., `bmw_m5_f90_features`)
- Ontology versioned in repo under `datasets/label_studio/<project>/ontology.json`
- Imports reference `image_uri` directly; exports saved under `datasets/exports/<project>/<date>/...`

Data quality and governance:

- Enforce deterministic pathing and file checksums to avoid dupes.
- Periodic validation jobs to ensure consistency between the database and file storage.
- A dedicated migration utility will handle the future local-to-S3 storage migration.

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

## **Phase 1: Scraper & Ingestion MVP**
- [ ] Implement a Playwright crawler for a single site (e.g., `collecting-cars`).
- [ ] The crawler should ingest raw ad data into the `ads` table.
- [ ] Download images, calculate their checksums, and store them in the checksum-based directory structure.
- [ ] Create `images` records with the correct checksum, URI, and a foreign key to the `ads` table.

***

## **Phase 2: Canonical Data Layer**
- [ ] Build scripts to populate the `manufacturers`, `models`, and `variants` tables from an official data source (e.g., a car data API or a curated file).
- [ ] Seed the database with an initial set of canonical data (e.g., for BMW).

***

## **Phase 3: Enrichment Pipeline**
- [ ] Create a script that reads unprocessed `ads`.
- [ ] Implement logic to parse the raw text fields (`raw_title`, `raw_model`, etc.).
- [ ] Match the parsed text to the canonical data and update the `ads` record with the correct `variant_id`.

***

## **Phase 4: Deduplication Pipeline**
- [ ] Design a similarity scoring module based on image checksums and other metadata (VIN, mileage, location).
- [ ] Implement a job that clusters similar `ads`.
- [ ] For each new cluster, create a `unique_cars` record.
- [ ] Update all `ads` in the cluster with the corresponding `unique_car_id`.

***

## **Phase 5: Labeling & Training Pipeline**
- [ ] Stand up Label Studio and create a project for exterior color identification.
- [ ] Write a script to query the database for all images of a specific variant (full coverage) and import them into Label Studio.
- [ ] Create a training pipeline for a color detection model using exported datasets.
- [ ] Round-trip annotations and model predictions back to the `images` table.

***

## **Phase 6: API & Analytics**
- [ ] Implement initial FastAPI endpoints to query `unique_cars` and their associated `ads` and `images`.
- [ ] Develop basic price outlier detection on the clean, deduplicated `unique_cars` data.

***

## **Phase 7: Dashboards, Monitoring & Scaling**
- [ ] Build Grafana dashboards for scraping stats, enrichment/deduplication rates, and data quality.
- [ ] Begin wrapping the core scripts (ingestion, enrichment, deduplication) into Dagster jobs for orchestration and monitoring.
- [ ] Implement retries and error handling for all critical jobs.

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