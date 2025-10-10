# AutoEvolution Scraper

A modular, production-ready web scraper for extracting comprehensive car specifications from [autoevolution.com](https://www.autoevolution.com).

## Features

✅ **Smart Cookie Management** - Automatically loads cookies from `cookies.json`, skips consent wait on subsequent runs  
✅ **Fast Execution** - No waiting for consent banner when cookies exist (~3s time savings per page)  
✅ **Comprehensive Spec Extraction** - Captures 80+ spec fields across multiple categories  
✅ **Infotainment Features** - Detects Apple CarPlay, Android Auto, and other connectivity features  
✅ **Gallery Images** - Extracts and stores car images with captions  
✅ **Robust Error Handling** - Graceful fallbacks and detailed logging  
✅ **Modular Architecture** - Clean separation of concerns across multiple modules  

## Architecture

### Module Structure

```
scripts/autoevolution/
├── __init__.py           # Package initialization
├── main.py               # Entry point and orchestration
├── config.py             # Configuration and logging setup
├── database.py           # Database helper functions (get_or_create)
├── scraper.py            # Core Playwright scraping logic
├── spec_extractor.py     # Comprehensive spec extraction with units
├── unit_parser.py        # Unit-aware parsing (HP/kW/BHP, Nm/lb-ft, etc.)
├── parsers.py            # Legacy parser (kept for reference)
├── cookies.json          # Persistent browser session (gitignored)
└── README.md             # This file
```

### Data Flow

```
1. main.py
   ↓
2. scraper.py (handle_cookie_consent, fetch_generation_details)
   ↓
3. spec_extractor.py (extract_all_specs with value+unit)
   ↓
4. unit_parser.py (parse_specs_with_units - extract all unit variations)
   ↓
5. database.py (get_or_create, upsert to DB with unit-specific columns)
```

## Usage

### Basic Usage

```bash
# Scrape a specific generation URL
uv run python -m scripts.autoevolution.main \
  --generation_url "https://www.autoevolution.com/cars/bmw-ms-cs-2021.html"

# Scrape by brand and model
uv run python -m scripts.autoevolution.main \
  --brand bmw \
  --model m5
```

### Command-Line Arguments

- `--generation_url`: Full URL to a specific generation page (e.g., BMW M5 CS F90)
- `--brand`: Brand slug (e.g., `bmw`, `mercedes-benz`)
- `--model`: Model slug (e.g., `m5`, `c-class`)

## What Gets Scraped

### 1. Infotainment Features
- Apple CarPlay
- Android Auto
- Bluetooth connectivity
- Other connectivity features

### 2. Technical Specifications (with Multiple Units)

**Engine:**
- Cylinders (e.g., V8, I6)
- Displacement (cc and liters)
- **Power in multiple units**: HP, kW, BHP
- **Torque in multiple units**: Nm, lb-ft
- RPM ranges for power and torque
- Fuel type, **fuel capacity** (liters and gallons)

**Performance:**
- **Top speed** (km/h and mph)
- **Acceleration** (0-100 km/h and 0-60 mph)
- Transmission type
- Drive type (AWD, RWD, FWD)

**Dimensions (metric and imperial):**
- **Length** (mm and inches)
- **Width** (mm and inches)
- **Height** (mm and inches)
- **Wheelbase** (mm and inches)
- **Ground clearance** (mm and inches)
- Turning circle

**Weight (metric and imperial):**
- **Unladen weight** (kg and lbs)
- **Gross weight** (kg and lbs)

**Brakes & Tires:**
- Front/rear brake types
- Front/rear tire sizes

**Fuel Economy (multiple formats):**
- **City, highway, combined** (L/100km and mpg)
- CO2 emissions (g/km)

**Aerodynamics:**
- Drag coefficient (Cd)

### 3. Gallery Images
- Up to 10 high-quality images per version
- Image URLs and captions stored in database

### 4. Extra Data (JSONB)
- Unmapped specs for future expansion
- Highlight features
- Category-specific data

## Database Schema

Data is stored in a normalized schema:

```
brands
  └── models
        └── generations
              └── versions
                    ├── specs (1:1)
                    └── images (1:N)
```

### Key Tables

- **brands**: Car manufacturers (BMW, Mercedes, etc.)
- **models**: Car models (M5, C-Class, etc.)
- **generations**: Model generations (F90, W206, etc.)
- **versions**: Engine/trim variants (M5 CS 4.4L V8, etc.)
- **specs**: Technical specifications (stored with JSONB `extra` field)
- **images**: Gallery images linked to versions

## Cookie Management

The scraper uses Playwright's `storage_state` feature to persist cookies for efficient operation:

1. **First Run**: 
   - No `cookies.json` found
   - Waits for cookie consent banner
   - Accepts consent and saves cookies to file
   
2. **Subsequent Runs**: 
   - Detects existing `cookies.json`
   - Loads cookies automatically
   - **Skips the 1-second consent wait** for faster scraping
   - Only does a quick check (no waiting) in case banner appears unexpectedly
   
3. **Automatic Saving**: 
   - Cookies are saved after each successful scrape
   - Session state persists across runs

### Cookie File Location
```
scripts/autoevolution/cookies.json
```

This file is automatically gitignored to prevent committing session data.

### Performance Impact
- **First run**: ~3 seconds (1s wait + 2s for consent handling)
- **Subsequent runs**: ~0s (instant, no waiting)

## Spec Extraction Details

### How It Works

The `spec_extractor.py` module uses a multi-strategy approach:

1. **Infotainment Icons**: Searches for images and elements with connectivity keywords
2. **Spec Tables**: Finds all `<table>` elements with technical data
3. **Category Detection**: Attempts to identify spec categories (engine, performance, etc.)
4. **Highlight Features**: Extracts bullet points and feature lists
5. **Gallery Images**: Collects car images from common gallery containers

### Spec Mapping

The `parsers.py` module maps raw scraped data to database columns:

```python
# Example mappings
"power" → horsepower (int)
"torque" → torque (int) + torque_rpm_min/max
"top_speed" → top_speed (int)
"acceleration_0-62_mph_0-100_kph" → acceleration_0_100 (float)
"fuel_capacity" → fuel_capacity (float)
```

Unmapped specs are stored in the `extra` JSONB column for future use.

## Error Handling

The scraper includes robust error handling:

- **Cookie Consent**: Multiple selectors, graceful fallback
- **Element Selection**: Tries alternative selectors if primary fails
- **Data Parsing**: Continues on individual row failures
- **Database**: Uses `get_or_create` to prevent duplicates
- **Logging**: Detailed INFO and DEBUG level logging

## Logging

Logging is configured in `config.py`:

```python
# Default: INFO level
# Change to DEBUG for detailed output
logging.basicConfig(level=logging.INFO)
```

### Log Output Example

```
2025-10-10 16:47:00 - INFO - Loading saved cookies from cookies.json
2025-10-10 16:47:01 - INFO - Processing single generation URL: ...
2025-10-10 16:47:02 - INFO - Created Generation: F90
2025-10-10 16:47:03 - INFO - Extracting comprehensive specs from page...
2025-10-10 16:47:04 - INFO - Stored 21 spec fields for BMW M5 CS
2025-10-10 16:47:05 - INFO - Stored 10 images for BMW M5 CS
```

## Development

### Adding New Spec Fields

1. Add mapping to `parsers.py` `key_map` dict
2. Add column to `db/models.py` `Spec` model
3. Create and apply Alembic migration
4. Run scraper to test

### Debugging

Enable DEBUG logging in `config.py`:

```python
logging.basicConfig(level=logging.DEBUG)
```

This will show:
- Raw spec keys found on page
- Category detection results
- Element selection details
- Data transformation steps

## Performance

- **Average scrape time**: 5-10 seconds per generation page
- **Cookie persistence**: Saves ~3 seconds per page after first run (no consent wait)
- **Smart consent handling**: Instant check when cookies loaded, only waits on first run
- **Database**: Uses connection pooling for efficiency
- **Memory**: Minimal footprint, processes one version at a time

## Future Enhancements

- [ ] Scrape multiple generations in parallel
- [ ] Add support for other car websites
- [ ] Implement incremental updates (only scrape new/changed data)
- [ ] Add data validation and quality checks
- [ ] Export scraped data to JSON/CSV
- [ ] Add progress tracking for large scraping jobs

## Troubleshooting

### Cookie consent not working
- Check if selectors have changed on the website
- Update selectors in `scraper.py` `handle_cookie_consent()`

### No specs found
- Enable DEBUG logging to see what elements are being found
- Check if page structure has changed
- Update selectors in `spec_extractor.py`

### Database errors
- Ensure migrations are up to date: `uv run alembic upgrade head`
- Check database connection in `config/settings.py`

## License

Part of the Carbot project.

