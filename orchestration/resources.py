from pathlib import Path

from dagster import ConfigurableResource


class ImageDirResource(ConfigurableResource):
    path: str = str(Path("scraped_images") / "images")

    def __call__(self) -> str:
        return self.path


image_dir_resource = ImageDirResource()


# Database session resource
try:
    from db.database import SessionLocal  # type: ignore
except Exception:  # pragma: no cover - resource import failure will surface in Dagster logs
    SessionLocal = None  # type: ignore


class DbSessionResource(ConfigurableResource):
    def __call__(self):
        if SessionLocal is None:
            raise RuntimeError("SessionLocal is not available; check db.database import")
        return SessionLocal()


db_session_resource = DbSessionResource()


