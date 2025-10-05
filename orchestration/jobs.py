from pathlib import Path

from dagster import OpExecutionContext, Out, job, op

from ml.infer_color import scan_directory, print_report
from ml.infer_color import infer_dominant_color

try:
    from db.models import CarAdRaw, CarAdEnriched  # type: ignore
except Exception:  # pragma: no cover
    CarAdRaw = None  # type: ignore
    CarAdEnriched = None  # type: ignore


@op(
    required_resource_keys={"image_dir"},
    out={
        "report": Out(str, description="Human-readable report of dominant colors"),
    },
    description="Scan a directory of images and compute dominant colors",
)
def infer_colors_op(context: OpExecutionContext) -> str:
    # Image directory provided via resource
    images_root = context.resources.image_dir()
    root = Path(images_root)
    if not root.exists() or not root.is_dir():
        return f"Directory not found: {root}"

    results = scan_directory(root)

    # Build a string report reusing the same formatting as the CLI
    lines = []
    updated = 0
    for filename, color, conf in results:
        color_display = color or "unknown"
        lines.append(f"{filename}: {color_display} ({conf:.3f})")
        if color:
            updated += 1
    lines.append(f"Total images: {len(results)}, Classified: {updated}")
    return "\n".join(lines)


@job(description="Enrichment job: infer dominant colors for scraped images")
def enrichment_job():
    infer_colors_op()


@op(required_resource_keys={"db_session"}, description="Persist detected colors into CarAdEnriched")
def persist_detected_colors_op(context: OpExecutionContext) -> str:
    if CarAdRaw is None or CarAdEnriched is None:
        return "DB models not available"

    # Open session from resource
    db = context.resources.db_session()
    updated = 0
    scanned = 0
    try:
        ads = (
            db.query(CarAdRaw)
            .filter(CarAdRaw.is_active == True)
            .order_by(CarAdRaw.scraped_at.desc())
            .limit(200)
            .all()
        )
        context.log.info(f"Fetched {len(ads)} ads for enrichment")
        for ad in ads:
            scanned += 1
            paths = ad.local_image_paths or []
            if not paths:
                continue
            first = paths[0]
            color, conf = infer_dominant_color(first)
            if not color:
                continue
            enriched = ad.enriched
            if enriched is None:
                enriched = CarAdEnriched(raw_ad_id=ad.id)
                db.add(enriched)
            enriched.detected_color = color
            enriched.detected_color_confidence = conf
            context.log.info(f"ad_id={ad.id} color={color} conf={conf}")
            updated += 1
        db.commit()
        return f"Scanned: {scanned}, Updated: {updated}"
    except Exception as e:  # pragma: no cover - surfaced in Dagster logs
        db.rollback()
        return f"Error: {e}"
    finally:
        db.close()


@job(description="Persist detected colors into DB from existing raw ads")
def enrichment_db_job():
    persist_detected_colors_op()



