from typing import Dict, List, Optional

import csv
import json
import logging
import os
import textwrap

import humanize
from xlsxwriter import Workbook

from telescope.reporters.charts import AIRFLOW_CHARTS
from telescope.reports import DAGReport, Deployment, DeploymentReport, InfrastructureReport, Report, SummaryReport

log = logging.getLogger(__name__)


def save_xlsx(output_filepath: str, **kwargs) -> None:
    with Workbook(filename=output_filepath) as wb:
        for report_key, report_rows in kwargs.items():
            ws = wb.add_worksheet(name=report_key)
            if len(report_rows):
                col_names = report_rows[0].__dict__.keys()
                for col, col_name in enumerate(col_names):
                    ws.write(0, col, col_name)

                for row, report_row in enumerate(report_rows):
                    for col, col_name in enumerate(col_names):
                        if report_row.__dict__.get(col_name) is not None:
                            sanitized_value = (
                                report_row.__dict__[col_name]
                                if type(report_row.__dict__[col_name]) in [float, int, bool, str]
                                else str(report_row.__dict__[col_name])
                            )
                            ws.write(row + 1, col, sanitized_value)


def save_csv(output_filepath: str, **kwargs) -> None:
    for report_key, report_rows in kwargs.items():
        o = output_filepath.replace(".csv", f"{report_key.replace(' ', '_')}.csv")
        with open(o, "w") as output:
            dw = csv.DictWriter(output, fieldnames=report_rows[0].__dict__.keys())
            dw.writeheader()
            dw.writerows(report_rows)


# TODO - serialize correctly
def save_json(output_filepath: str, **kwargs) -> None:
    with open(output_filepath, "w") as output:
        json.dump(kwargs, output)


REPORT_TYPES = {"json": save_json, "csv": save_csv, "xlsx": save_xlsx}


def should_skip(key, value, astro_seen) -> bool:
    try:
        # cheap dedup of dirty data that has multiple schedulers
        if "astronomer" in key:
            [_, pod] = key.split("|")
            deduped = "-".join(pod.split("-")[:-2])
            if deduped in astro_seen:
                return True
            else:
                # If there was an ApiException or something, skip the dedupe
                if value.get("airflow_report", {}).get("airflow_version_report") != "Unknown":
                    astro_seen.add(deduped)
    except Exception as e:
        log.debug(e)
    return False


def get_product(
    installed_packages_report: dict, configuration_report: dict, helm: Optional[dict], attempt: bool = False
) -> Optional[str]:
    """one of software | core | oss
    astronomer astronomer in verify (won't always have)
    astronomer-certified in airflow_report.installed_packages_report (core/software)
    astronomer in airflow_report.configuration_report (software)
    astronomer_airflow_scripts (? + runtime)
    astro in airflow version - ISN'T ALWAYS TRUE
    """
    if "astronomer-certified" in installed_packages_report:
        if "astronomer" in configuration_report:
            return "software"
        else:
            return "core"
    else:
        return "oss"


def generate_output_reports(
    input_data: dict, filename_organization: str = None, filename_date: str = None
) -> Dict[str, List[Report]]:
    """Aggregates and parses the raw JSON data and assembles various reports on the data"""
    output_reports = {
        "Summary Report": [],
        "Infrastructure Report": [],
        "Deployment Report": [],
        "DAG Report": [],
        "Deployments": [],
    }

    common_fields = {
        "telescope_version": input_data.get("telescope_version"),
        "report_date": input_data.get("report_date", filename_date),
        "organization": input_data.get("organization_name", filename_organization),
    }

    if "cluster_info" in input_data:
        output_reports["Infrastructure Report"] = [InfrastructureReport(**input_data["cluster_info"], **common_fields)]

    maybe_verify: dict = input_data.get("verify", {}).get("helm", {})

    airflows = set()
    deployment_reports = []
    deployments = []
    dag_reports = []
    summary_dags_active = 0
    summary_dags_inactive = 0
    summary_num_tasks = 0
    summary_num_successful_task_runs_monthly = 0

    astro_seen = set()
    for host_type in ["kubernetes", "docker", "ssh", "local"]:
        if host_type in input_data:
            for key, value in input_data[host_type].items():

                # cheap dedup of dirty data that has multiple schedulers, and sanity check for the report we want
                if should_skip(key, value, astro_seen) or not value["airflow_report"]:
                    continue

                airflows.add(key)

                product = get_product(
                    installed_packages_report=value["airflow_report"].get("installed_packages_report"),
                    configuration_report=value["airflow_report"].get("configuration_report"),
                    helm=maybe_verify,
                )
                deployment_report = DeploymentReport.from_input_report_row(
                    name=key, input_row=value["airflow_report"], verify=maybe_verify, product=product, **common_fields
                )

                summary_dags_active += deployment_report.num_dags_active
                summary_dags_inactive += deployment_report.num_dags_inactive
                summary_num_tasks += deployment_report.num_tasks
                summary_num_successful_task_runs_monthly += deployment_report.task_runs_monthly_success
                deployment_reports.append(deployment_report)

                deployments.append(Deployment.from_deployment_report(deployment_report, key, maybe_verify))

                if type(value["airflow_report"]) == dict and "dags_report" in value["airflow_report"]:
                    for dag_report in value["airflow_report"].get("dags_report"):
                        dag_reports.append(
                            DAGReport(
                                workspace_id=deployment_report.workspace_id,
                                deployment_id=deployment_report.deployment_id,
                                airflow_name=key,
                                product=product,
                                **dag_report,
                                **common_fields,
                            )
                        )

            output_reports["Deployments"] = deployments
            output_reports["Deployment Report"] = deployment_reports
            output_reports["DAG Report"] = dag_reports
        else:
            log.debug(f"Skipping host type {host_type}, not found in input report")

    output_reports["Summary Report"] = [
        SummaryReport(
            num_airflows=len(airflows),
            num_dags_active=summary_dags_active,
            num_dags_inactive=summary_dags_inactive,
            num_tasks=summary_num_tasks,
            num_successful_task_runs_monthly=summary_num_successful_task_runs_monthly,
            **common_fields,
        )
    ]
    return output_reports


def generate_report(output_reports, report_type: str, output_filepath: str) -> None:
    REPORT_TYPES.get(report_type, save_xlsx)(output_filepath, **output_reports)


def generate_charts(output_reports) -> None:
    if not os.path.exists("charts"):
        log.info("Creating /charts subdirectory...")
        os.mkdir("charts")
    for chart, (gen_fn, report) in AIRFLOW_CHARTS.items():
        chart_path = "charts/" + chart.replace(" ", "_").lower() + ".png"
        log.info(f"Creating chart: {chart}, path: {chart_path} ...")
        gen_fn(output_reports[report], chart_path)


def generate_report_summary_text(output_reports, output_file: str = "report_summary.txt") -> None:
    summary_reports: List[SummaryReport] = output_reports["Summary Report"]
    airflow_reports: List[DeploymentReport] = output_reports["Deployment Report"]

    def humanize_num(_i: int):
        humanized = humanize.intword(_i, format="%.0f")
        for full, abbr in {" thousand": "K", " million": "M", " billion": "B"}.items():
            humanized = humanized.replace(full, abbr)
        return humanized

    with open(output_file, "w") as outf:
        summary = summary_reports[0]
        outf.write(
            textwrap.dedent(
                f"""
        Summary:
        - Airflows Assessed: {summary.num_airflows}
        - DAGs Active: {summary.num_dags_active}
        - DAGs Inactive: {summary.num_dags_inactive}
        - Tasks Defined: {humanize_num(summary.num_tasks)}
        - Successful Monthly Tasks Runs: {humanize_num(summary.num_successful_task_runs_monthly)}
        """
            )
        )

        for i, row in enumerate(sorted(airflow_reports, key=lambda _row: _row.task_runs_monthly_success, reverse=True)):
            outf.write(
                textwrap.dedent(
                    f"""
            =======
            Airflow #{i + 1} - {row.name}
            - Airflow {row.version}
            - {row.executor}
            - DAGs: {row.num_dags_active} Active, {row.num_dags_inactive} Inactive
            - Tasks: {humanize_num(row.num_tasks)} defined
            - Task Runs: {humanize_num(row.task_runs_monthly_success) if row.task_runs_monthly_success > 0 else "None"} Monthly
            - Parallelism: {row.parallelism}
            - Pools: Default ({row.default_pool_slots} Slots), {row.num_pools - 1} Other Pools
            - Operators: {len(row.unique_operators)} defined
            - Connections: {row.num_connections} defined
            - Providers: {row.num_providers} defined
            """
                )
            )
