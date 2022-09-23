"""
Google Cloud Composer - https://cloud.google.com/composer/docs/concepts/plugins
AWS Managed Apache Airflow - https://docs.aws.amazon.com/mwaa/latest/userguide/configuring-dag-import-plugins.html
"""
from typing import Any, Dict, List, Sequence, Union

import base64
import datetime
import json
import logging
import socket
from contextlib import redirect_stderr, redirect_stdout
from json import JSONDecodeError
from airflow.models.baseoperator import BaseOperator
from airflow.plugins_manager import AirflowPlugin
from flask import Blueprint, Response, jsonify
from flask_appbuilder import BaseView as AppBuilderBaseView
from flask_appbuilder import expose

bp = Blueprint(
    "aeroscope",
    __name__,
    template_folder="templates",  # registers airflow/plugins/templates as a Jinja template folder
    static_folder="static",
    static_url_path="/static/aeroscope",
)


def clean_airflow_report_output(log_string: str) -> Union[dict, str]:
    r"""Look for the magic string from the Airflow report and then decode the base64 and convert to json
    Or return output as a list, trimmed and split on newlines
    >>> clean_airflow_report_output('INFO 123 - xyz - abc\n\n\nERROR - 1234\n%%%%%%%\naGVsbG8gd29ybGQ=')
    'hello world'
    >>> clean_airflow_report_output('INFO 123 - xyz - abc\n\n\nERROR - 1234\n%%%%%%%\neyJvdXRwdXQiOiAiaGVsbG8gd29ybGQifQ==')
    {'output': 'hello world'}
    """
    log_lines = log_string.split("\n")
    enumerated_log_lines = list(enumerate(log_lines))
    found_i = -1
    for i, line in enumerated_log_lines:
        if "%%%%%%%" in line:
            found_i = i + 1
            break
    if found_i != -1:
        output = base64.decodebytes("\n".join(log_lines[found_i:]).encode("utf-8")).decode("utf-8")
        try:
            return json.loads(output)
        except JSONDecodeError:
            return get_json_or_clean_str(output)
    else:
        return get_json_or_clean_str(log_string)


def get_json_or_clean_str(o: str) -> Union[List[Any], Dict[Any, Any], Any]:
    """Either load JSON (if we can) or strip and split the string, while logging the error"""
    try:
        return json.loads(o)
    except (JSONDecodeError, TypeError) as e:
        log.debug(e)
        log.debug(o)
        return o.strip()


log = logging.getLogger(__name__)


# Creating a flask appbuilder BaseView
class Aeroscope(AppBuilderBaseView):
    default_view = "aeroscope"

    @expose("/")
    def aeroscope(self):
        import io
        import runpy
        from urllib.request import urlretrieve

        a = "airflow_report.pyz"
        urlretrieve("https://github.com/astronomer/telescope/releases/latest/download/airflow_report.pyz", a)
        s = io.StringIO()
        with redirect_stdout(s), redirect_stderr(s):
            runpy.run_path(a)
        date = datetime.datetime.now(datetime.timezone.utc).isoformat()[:10]
        content = {
            "telescope_version": "aeroscope",
            "report_date": date,
            "organization_name": "aeroscope",
            "local": {socket.gethostname(): {"airflow_report": clean_airflow_report_output(s.getvalue())}},
        }
        filename = f"{date}.aeroscope.data.json"
        return Response(
            json.dumps(content),
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment;filename={filename}"},
        )


v_appbuilder_view = Aeroscope()


# Defining the plugin class
class AirflowTestPlugin(AirflowPlugin):
    name = "aeroscope"
    hooks = []
    macros = []
    flask_blueprints = [bp]
    appbuilder_views = [
        {
            "name": "Download Results",
            "category": "Aeroscope",
            "view": v_appbuilder_view,
        },
    ]
    appbuilder_menu_items = []
    global_operator_extra_links = []
    operator_extra_links = []


class AeroscopeOperator(BaseOperator):
    template_fields: Sequence[str] = (
        "presigned_url",
        "email",
    )

    def __init__(
        self,
        *,
        presigned_url,
        email,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.presigned_url = presigned_url
        self.email = email

    def execute(self, context: "Context"):
        from urllib.request import urlretrieve

        import requests
        import io
        import runpy

        a = "airflow_report.pyz"
        urlretrieve("https://github.com/astronomer/telescope/releases/latest/download/airflow_report.pyz", a)
        s = io.StringIO()
        with redirect_stdout(s), redirect_stderr(s):
            runpy.run_path(a)
        date = datetime.datetime.now(datetime.timezone.utc).isoformat()[:10]
        content = {
            "telescope_version": "aeroscope",
            "report_date": date,
            "organization_name": "aeroscope",
            "local": {socket.gethostname(): {"airflow_report": clean_airflow_report_output(s.getvalue())}},
            "user_email": self.email,
        }
        s3 = requests.put(self.presigned_url, data=json.dumps(content))
        if s3.ok:
            return "success"
        else:
            raise ValueError(f"upload failed  with code {s3.status_code}::{s3.json()}")
        # return json.dumps(content)
