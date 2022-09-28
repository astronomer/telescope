from typing import Sequence

import datetime
import json
import logging
import socket
from contextlib import redirect_stderr, redirect_stdout

from airflow.models import BaseOperator
from astronomer.aeroscope.util import clean_airflow_report_output


class AeroscopeOperator(BaseOperator):
    template_fields: Sequence[str] = ("presigned_url", "organization")

    def __init__(
        self,
        presigned_url,
        organization,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.presigned_url = presigned_url
        self.organization = organization

    def execute(self, context):
        import io
        import runpy
        from urllib.request import urlretrieve

        import requests

        a = "airflow_report.pyz"
        urlretrieve("https://github.com/astronomer/telescope/releases/latest/download/airflow_report.pyz", a)
        s = io.StringIO()
        with redirect_stdout(s), redirect_stderr(s):
            runpy.run_path(a)
        date = datetime.datetime.now(datetime.timezone.utc).isoformat()[:10]
        content = {
            "telescope_version": "aeroscope-latest",
            "report_date": date,
            "organization_name": self.organization,
            "local": {socket.gethostname(): {"airflow_report": clean_airflow_report_output(s.getvalue())}},
        }
        upload = requests.put(self.presigned_url, data=json.dumps(content))
        if not upload.ok:
            logging.error(f"Upload failed with code {upload.status_code}::{upload.json()}")
            upload.raise_for_status()
