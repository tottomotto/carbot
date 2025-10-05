from dagster import Definitions

from orchestration.jobs import enrichment_job, enrichment_db_job
from orchestration.resources import image_dir_resource, db_session_resource


defs = Definitions(
    jobs=[enrichment_job, enrichment_db_job],
    resources={
        "image_dir": image_dir_resource,
        "db_session": db_session_resource,
    },
)


