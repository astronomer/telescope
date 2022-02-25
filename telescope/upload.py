from typing import Dict, List, Optional, Union

import datetime
import logging
import textwrap

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

PROJECT = "astronomer-cloud"
BUCKET = "astronomer-telescope"

REPORT_STUBS = {
    "raw": "gcs://{BUCKET}/{customer}/raw/{org_with_env}/{date}/data.json",
    "Astronomer Report": "gcs://{BUCKET}/{customer}/astronomer_report/{org_with_env}/{date}/data.parquet",
    "Summary Report": "gcs://{BUCKET}/{customer}/summary_report/{org_with_env}/{date}/data.parquet",
    "Infrastructure Report": "gcs://{BUCKET}/{customer}/infrastructure_report/{org_with_env}/{date}/data.parquet",
    "Deployment Report": "gcs://{BUCKET}/{customer}/deployment_report/{org_with_env}/{date}/data.parquet",
    "DAGs Report": "gcs://{BUCKET}/{customer}/dag_report/{org_with_env}/{date}/data.parquet",
}


def get_gcs_report_path(
    report_type: str, organization_name: str, is_customer: Optional[bool] = True, env: Optional[str] = None
):
    if report_type in REPORT_STUBS:
        inputs = {
            "BUCKET": BUCKET,
            "customer": "customer" if is_customer else "noncustomer",
            "org_with_env": f"{organization_name}__{env}" if env else organization_name,
            "date": datetime.datetime.utcnow().isoformat()[:10],
        }
        # noinspection StrFormat
        return REPORT_STUBS[report_type].format(**inputs)
    else:
        raise RuntimeError(f"Report Type {report_type} not found in {REPORT_STUBS.keys()}")


def upload_to_gcs(
    output_reports: Dict[str, Union[dict, List[Report]]],
    organization_name: str,
    is_customer: bool = True,
    env: Optional[str] = None,
) -> None:
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

    for report_type, df in output_reports.items():
        gcs_path = get_gcs_report_path(report_type, organization_name, is_customer, env)
        log.debug(f"Saving report type: {report_type} to path: {gcs_path}")

        if not gcs_path:
            continue

        if report_type == "raw":
            # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_json.html
            # noinspection PyUnresolvedReferences
            df = DataFrame(output_reports[report_type])
            df.to_json(gcs_path, default_handler=str)
        else:
            # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_parquet.html
            # noinspection PyUnresolvedReferences
            df = DataFrame(output_reports[report_type])
            for col in df.columns:
                # cast any "object" types to strings - dict, list
                if df[col].dtypes in ("O",):
                    df[col] = df[col].astype(
                        "string",
                    )
            df.to_parquet(gcs_path, compression="snappy")
