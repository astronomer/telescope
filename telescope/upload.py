from typing import Dict, List, Optional, Union

import datetime
import logging
import textwrap

from google.cloud import storage
from google.cloud.storage import Blob
from lazyimport import lazyimport

from telescope.reports import Report

lazyimport(
    globals(),
    """
from pandas import DataFrame
import pandas as pd
""",
)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

PROJECT = "astronomer-cloud"
BUCKET = "astronomer-telescope"

REPORT_STUBS = {
    "raw": "gs://{BUCKET}/raw/{org_with_env}/{date}/data.json",
    "Deployments": "gs://{BUCKET}/reports/deployments/{org_with_env}/{date}/data.parquet",
    "Summary Report": "gs://{BUCKET}/reports/summary_report/{org_with_env}/{date}/data.parquet",
    "Infrastructure Report": "gs://{BUCKET}/reports/infrastructure_report/{org_with_env}/{date}/data.parquet",
    "Deployment Report": "gs://{BUCKET}/reports/deployment_report/{org_with_env}/{date}/data.parquet",
    "DAG Report": "gs://{BUCKET}/reports/dag_report/{org_with_env}/{date}/data.parquet",
}


def get_gcs_report_path(report_type: str, organization_name: str, date: str, env: Optional[str] = None):
    if report_type in REPORT_STUBS:
        inputs = {
            "BUCKET": BUCKET,
            "org_with_env": f"{organization_name}__{env}" if env else organization_name,
            "date": date,
        }
        # noinspection StrFormat
        return REPORT_STUBS[report_type].format(**inputs)
    else:
        raise RuntimeError(f"Report Type {report_type} not found in {REPORT_STUBS.keys()}")


def upload_to_gcs(output_reports: Dict[str, Union[dict, List[Report]]], organization_name: str,
                  raw_filepath: str, date: str) -> None:
    log.debug(
        textwrap.dedent(
            """
    Note: Logging into GCP using YOUR credentials - you will need to have already run the following:
    gcloud auth login
    gcloud auth application-default login

    See more here:
    https://cloud.google.com/sdk/docs/install-sdk
    https://cloud.google.com/docs/authentication/best-practices-applications
    """
        )
    )

    # Upload raw file
    client = storage.Client()
    raw_gcs_filepath = get_gcs_report_path("raw", organization_name, date, env=None)
    blob = Blob.from_string(uri=raw_gcs_filepath, client=client)
    blob.upload_from_filename(filename=raw_filepath)

    # Upload reports
    for report_type, df in output_reports.items():
        gcs_path = get_gcs_report_path(report_type, organization_name, date, env=None)
        log.info(f"Saving report type: {report_type} to path: {gcs_path}")

        if not gcs_path:
            continue
        # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_parquet.html
        # noinspection PyUnresolvedReferences
        df = DataFrame(output_reports[report_type])
        for col in df.columns:
            # cast any "object" types to strings - dict, list
            if df[col].dtypes in ("O",):
                df[col] = df[col].astype("string")
        df.to_parquet(gcs_path, compression="snappy")
