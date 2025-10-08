from dagster import Definitions

from orchestration.jobs import enrichment_job, enrichment_db_job, targeted_scrape_job, build_training_dataset_job, collect_and_build_dataset_job, collect_images_job, collect_auto_data_images_job, crawl_site_images_job
from orchestration.resources import image_dir_resource, db_session_resource, dataset_dir_resource


defs = Definitions(
    jobs=[
        enrichment_job,
        enrichment_db_job,
        targeted_scrape_job,
        build_training_dataset_job,
        collect_and_build_dataset_job,
        collect_images_job,
        collect_auto_data_images_job,
        crawl_site_images_job,
    ],
    resources={
        "image_dir": image_dir_resource,
        "db_session": db_session_resource,
        "dataset_dir": dataset_dir_resource,
    })