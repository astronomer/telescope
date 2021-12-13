import json
import logging
import os
import textwrap
from dataclasses import asdict
from importlib.resources import path

import humanize
import pandas as pd
from jinja2 import Template

from telescope import reporters
from telescope.reporters import AirflowReport, DAGReport, InfrastructureReport, SummaryReport
from telescope.reporters.charts import AIRFLOW_CHARTS

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


def create_report_summary_text(summary_df, airflow_df, output_file: str):
    def humanize_num(_i: int):
        humanized = humanize.intword(_i, format="%.0f")
        for full, abbr in {" thousand": "K", " million": "M", " billion": "B"}.items():
            humanized = humanized.replace(full, abbr)
        return humanized

    with open(output_file, "w") as outf:
        summary = summary_df.loc[0]
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

        for i, row in (
            airflow_df.sort_values(by=["task_runs_monthly_success"], ascending=False).reset_index(drop=True).iterrows()
        ):
            outf.write(
                textwrap.dedent(
                    f"""
            =======
            Airflow #{i + 1} - {row['name']}
            - Airflow {row.version}
            - {row.executor}
            - DAGs: {row.num_dags_active} Active, {row.num_dags_inactive} Inactive
            - Tasks: {humanize_num(row.num_tasks)} defined
            - Task Runs: {humanize_num(row.task_runs_monthly_success) if row.task_runs_monthly_success > 0 else "None"} Monthly
            - Parallelism: {row.parallelism}
            - Pools: Default ({row.default_pool_slots} Slots), {row.num_pools} Other Pools
            - Operators: {len(row.unique_operators)} defined
            - Connections: {row.num_connections} defined
            - Providers: {row.num_providers} defined
            """
                )
            )


def zip_outputs():
    return NotImplementedError


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

    maybe_verify: dict = input_report.get("verify", {}).get("helm", {})

    airflows = set()
    airflow_reports = []
    dag_reports = []
    summary_dags_active = 0
    summary_dags_inactive = 0
    summary_num_tasks = 0
    summary_num_successful_task_runs_monthly = 0

    for host_type in ["kubernetes", "docker", "ssh"]:
        if host_type in input_report:
            for key, value in input_report[host_type].items():
                airflows.add(key)
                airflow_report = AirflowReport.from_input_report_row(
                    name=key, input_row=value["airflow_report"], verify=maybe_verify
                )
                summary_dags_active += airflow_report.num_dags_active
                summary_dags_inactive += airflow_report.num_dags_inactive
                summary_num_tasks += airflow_report.num_tasks
                summary_num_successful_task_runs_monthly += airflow_report.task_runs_monthly_success
                airflow_reports.append(asdict(airflow_report))

                for dag_report in value["airflow_report"].get("dags_report"):
                    dag_reports.append(asdict(DAGReport(airflow_name=key, **dag_report)))

            output_reports["Airflow Report"] = pd.DataFrame(airflow_reports)
            output_reports["DAG Report"] = pd.DataFrame(dag_reports)
        else:
            log.debug(f"Skipping host type {host_type}, not found in input report")

    output_reports["Summary Report"] = pd.DataFrame(
        [
            SummaryReport(
                num_airflows=len(airflows),
                num_dags_active=summary_dags_active,
                num_dags_inactive=summary_dags_inactive,
                num_tasks=summary_num_tasks,
                num_successful_task_runs_monthly=summary_num_successful_task_runs_monthly,
            )
        ]
    )

    log.info(f"Saving {report_type} type report to {output_filepath}")
    REPORT_TYPES.get(report_type, save_xlsx)(output_filepath, **output_reports)

    log.info("Creating charts in charts subdirectory...")
    if not os.path.exists("charts"):
        os.mkdir("charts")
    for chart, (gen_fn, report) in AIRFLOW_CHARTS.items():
        chart_path = "charts/" + chart.replace(" ", "_").lower() + ".png"
        log.info(f"Creating chart: {chart}, path: {chart_path} ...")
        gen_fn(output_reports[report], chart_path)

    create_report_summary_text(output_reports["Summary Report"], output_reports["Airflow Report"], "report_summary.txt")


def assemble_from_file(input_filepath: str, **kwargs):
    with open(input_filepath) as input_file:
        assemble(json.load(input_file), **kwargs)
