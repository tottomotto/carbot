# Database Schema

This document outlines the database schema for the car platform, managed via SQLAlchemy and Alembic migrations. The schema is designed around a normalized model that separates canonical data (manufacturers, models) from transactional data (ads) and observational data (unique cars, images).

## Schema Diagram (Conceptual)

```
+----------------+      +-----------+      +-----------+      +-------------+
| Manufacturer |----<|   Model   |----<|  Variant  |----<|  UniqueCar  |
+----------------+      +-----------+      +-----------+      +-------------+
                                                                    ^
                                                                    |
                                                              +-----+-----+
                                                              |    Ad     |
                                                              +-----+-----+
                                                                    ^
                                                                    |
                                                              +-----+-----+
                                                              |   Image   |
                                                              +-----------+
```

## Data Flow Logic

1.  **Ingestion**: Scrapers collect ad data, creating records in the `ads` table. The `unique_car_id` is initially `NULL`. Raw text like make, model, year is stored.
2.  **Enrichment (Future Step)**: A process parses the raw text from ads, matches it against the canonical `manufacturers`, `models`, and `variants` tables, and populates the appropriate foreign keys.
3.  **Deduplication (Future Step)**: A process analyzes ads based on VIN, image checksums, and other metadata to identify ads that represent the same physical car. When a cluster is found, a `unique_cars` record is created, and all relevant `ads` are updated with the corresponding `unique_car_id`.

## Tables

### `manufacturers`
Canonical list of car manufacturers.

| Column | Type | Description |
|---|---|---|
| `id` | `Integer` | PK |
| `name` | `String(100)` | Unique name (e.g., "BMW"). |

### `models`
Canonical list of car models, linked to a manufacturer.

| Column | Type | Description |
|---|---|---|
| `id` | `Integer` | PK |
| `manufacturer_id` | `Integer` | FK to `manufacturers.id`. |
| `name` | `String(100)` | Model name (e.g., "M5"). Unique per manufacturer. |

### `variants`
Specific versions of a model.

| Column | Type | Description |
|---|---|---|
| `id` | `Integer` | PK |
| `model_id` | `Integer` | FK to `models.id`. |
| `name` | `String(100)` | Variant name (e.g., "Competition"). Unique per model. |
| `start_year` | `Integer` | Start production year. |
| `end_year` | `Integer` | End production year. |

### `unique_cars`
Master record for a single, physical car.

| Column | Type | Description |
|---|---|---|
| `id` | `Integer` | PK |
| `variant_id` | `Integer` | FK to `variants.id`. The car's canonical identity. |
| `vin` | `String(17)` | Vehicle Identification Number. The ultimate unique identifier. |
| `first_seen_at` | `DateTime` | Timestamp of the first time an ad for this car was seen. |
| `last_seen_at` | `DateTime` | Timestamp of the last time an ad for this car was seen. |
| `status` | `String(50)` | Current status (e.g., "For Sale", "Sold"). |

### `ads`
A single advertisement on a source website.

| Column | Type | Description |
|---|---|---|
| `id` | `Integer` | PK |
| `unique_car_id` | `Integer` | FK to `unique_cars.id`. Populated by the deduplication process. |
| `source_site` | `String(100)` | Website the ad was scraped from. |
| `source_id` | `String(255)` | The ad's ID on the source website. |
| `source_url` | `Text` | Full URL of the ad. |
| `raw_...` | `String`, `Float`... | Raw, unparsed fields from the scraper (e.g., `raw_title`, `raw_price`). |
| `raw_data` | `JSON` | The complete raw JSON payload from the scraper. |
| `created_at` | `DateTime` | When the ad was first ingested. |
| `last_scraped_at`| `DateTime` | When the ad was last checked. |
| `is_active` | `Boolean` | If the ad is still active on the source site. |

### `images`
Universal repository for all images from all sources.

| Column | Type | Description |
|---|---|---|
| `id` | `Integer` | PK |
| `ad_id` | `Integer` | FK to `ads.id`. For images from an ad. |
| `variant_id` | `Integer` | FK to `variants.id`. For generic images of a variant. |
| `unique_car_id` | `Integer` | FK to `unique_cars.id`. For non-ad images of a specific known car. |
| `image_uri` | `String(1024)`| Checksum-based URI (`file://` or `s3://`). |
| `checksum` | `String(64)` | SHA256 of the image file. Used for deduplication. |
| `status` | `String(50)` | Image status in the ML pipeline (e.g., "raw", "labeled"). |
| `annotations` | `JSON` | Annotation data from Label Studio. |
| `created_at` | `DateTime` | When the image was ingested. |

**Constraint:** Exactly ONE of `ad_id`, `variant_id`, or `unique_car_id` must be non-NULL for each image.
