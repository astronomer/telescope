import json
import logging
from dataclasses import asdict
from importlib.resources import path

import pandas as pd
from jinja2 import Template

from telescope import reporters
from telescope.reporters import AirflowReport, DAGReport, InfrastructureReport, SummaryReport

log = logging.getLogger(__name__)


def save_xlsx(output_filepath: str, **kwargs) -> None:
    with pd.ExcelWriter(output_filepath) as writer:
        for k, v in kwargs.items():
            v.to_excel(writer, sheet_name=k)


def save_html(output_filepath: str, **kwargs) -> None:
    with path(reporters, "report.html.jinja2") as tmpl, open(str(tmpl.resolve())) as template, open(
        output_filepath, "w"
    ) as output:
        template_to_render = Template(template.read(), autoescape=True)
        rendered_template = template_to_render.render(dataframes=kwargs)
        output.write(rendered_template)


def save_csv(output_filepath: str, **kwargs) -> None:
    for k, v in kwargs.items():
        o = output_filepath.replace(".csv", f"{k.replace(' ', '_')}.csv")
        with open(o, "w") as output:
            v.to_csv(output, index=False)


def save_json(output_filepath: str, **kwargs) -> None:
    with open(output_filepath, "w") as output:
        json.dump({k: v.to_dict("records") for k, v in kwargs.items()}, output)


REPORT_TYPES = {"html": save_html, "json": save_json, "csv": save_csv, "xlsx": save_xlsx}


def assemble(input_report: dict, output_filepath: str, report_type: str):
    output_reports = {
        "Summary Report": pd.DataFrame(),
        "Infrastructure Report": pd.DataFrame(),
        "Airflow Report": pd.DataFrame(),
        "DAG Report": pd.DataFrame(),
    }
    if "cluster_info" in input_report:
        output_reports["Infrastructure Report"] = pd.DataFrame(
            [asdict(x) for x in [InfrastructureReport.from_input_report_row(input_row=input_report["cluster_info"])]]
        )

    maybe_verify = input_report.get("verify", {}).get("helm")

    airflows = set()
    dags_active = set()
    dags_inactive = set()
    airflow_reports = []
    dag_reports = []

    for host_type in ["kubernetes", "docker", "ssh"]:
        if host_type in input_report:
            for key, value in input_report[host_type].items():
                airflows += key
                airflow_reports.append(
                    asdict(
                        AirflowReport.from_input_report_row(
                            name=key, input_row=value["airflow_report"], verify=maybe_verify
                        )
                    )
                )

                for dag_report in value["airflow_report"].get("dags_report"):
                    if dag_report["is_active"] and not dag_report["is_paused"]:
                        dags_active += dag_report["dag_id"]
                    else:
                        dags_inactive += dag_report["dag_id"]
                    dag_reports.append(asdict(DAGReport(airflow_name=key, **dag_report)))

            output_reports["Airflow Report"] = pd.DataFrame(airflow_reports)
            output_reports["DAG Report"] = pd.DataFrame(dag_reports)
        else:
            log.debug(f"Skipping host type {host_type}, not found in input report")

    output_reports["Summary Report"] = pd.DataFrame(
        [
            SummaryReport(
                num_airflows=len(airflows), num_dags_active=len(dags_active), num_dags_inactive=len(dags_inactive)
            )
        ]
    )

    log.info(f"Saving {report_type} type report to {output_filepath}")
    REPORT_TYPES.get(report_type, save_xlsx)(output_filepath, **output_reports)


def assemble_from_file(input_filepath: str, output_filepath: str, report_type: str):
    with open(input_filepath) as input_file:
        assemble(json.load(input_file), output_filepath, report_type)
