import json
from dataclasses import asdict

import pandas as pd
from loguru import logger

from telescope.reporters import InfrastructureReport, AirflowReport


def save_xlsx(output_filepath: str, **kwargs) -> None:
    with pd.ExcelWriter('output.xlsx') as writer:
        for k, v in kwargs.items():
            v.to_excel(writer, sheet_name=k)


def assemble(input_report: dict, output_filepath: str, report_type: str):
    output_reports = {
        "Summary Report": None,
        "Infrastructure Report": None,
        "Airflow Report": None,
        "DAG Report": None
    }
    if 'cluster_info' in input_report:
        output_reports["Infrastructure Report"] = pd.DataFrame([asdict(x) for x in [
            InfrastructureReport.from_input_report_row(infra_type="k8s", input_row=input_report['cluster_info'])
        ]])

    for host_type in ['kubernetes', 'docker', 'ssh']:
        if host_type in input_report:
            output_reports['Airflow Report'] = pd.DataFrame([
                asdict(AirflowReport.from_input_report_row(name=key, input_row=airflow_dict['airflow_report']))
                for key, airflow_dict in input_report[host_type].items()
            ])
        else:
            logger.debug(f"Skipping host type {host_type}, not found in input report")


def assemble_from_file(input_filepath: str, output_filepath: str, report_type: str):
    with open(input_filepath, 'r') as input_file:
        assemble(json.load(input_file), output_filepath, report_type)
