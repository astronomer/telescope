from typing import List

import logging

from lazyimport import lazyimport

from telescope.reports import DAGReport, DeploymentReport

lazyimport(
    globals(),
    """
import numpy as np
import plotly.express as px
from pandas import DataFrame
""",
)

log = logging.getLogger(__name__)


def pretty_pie_chart(fig):
    fig.update_traces(
        textposition="outside",
        texttemplate="%{label} - %{value:s} Deployments <br>(%{percent})",
    )
    fig.update_layout(margin=dict(l=5, r=5, t=50, b=5), showlegend=False)
    return fig


def create_airflow_versions_chart(deployment_report: List[DeploymentReport], output_file: str) -> None:
    # noinspection PyUnresolvedReferences
    airflow_df = DataFrame(deployment_report)
    title = "Airflow Versions"
    if "version" in airflow_df:
        vc = airflow_df["version"].value_counts()
        if len(vc) > 10:
            vc = vc.nlargest(10)
            title += " (Top 10)"
        # noinspection PyUnresolvedReferences
        pretty_pie_chart(
            px.pie(
                vc,
                title=title,
                color_discrete_sequence=px.colors.qualitative.Prism,
                names=vc.index,
                values=vc.values,
            )
        ).write_image(output_file, width=750, height=500)
    else:
        log.warning(f"'version' not found in report - unable to create {title} chart")


def prettify_bar_chart(fig):
    return (
        fig.update_layout(
            xaxis={"categoryorder": "total descending"},
            margin=dict(l=5, r=5, t=50, b=5),
            showlegend=False,
        )
        .update_traces(texttemplate="%{text}", textposition="auto")
        .update_layout(uniformtext_mode="hide")
    )


def create_dags_per_airflow_chart(deployment_report: List[DeploymentReport], output_file: str) -> None:
    # noinspection PyUnresolvedReferences
    airflow_df = DataFrame(deployment_report)
    title = "Active DAGs per Airflow"
    if "name" in airflow_df:
        airflow_df["name"] = airflow_df["name"].str.split("|").str[0]

        if len(airflow_df) > 40:
            airflow_df = airflow_df.nlargest(40, "num_dags_active")
            title += " (Top 40)"
        # noinspection PyUnresolvedReferences
        prettify_bar_chart(
            px.bar(
                airflow_df,
                title=title,
                color_discrete_sequence=px.colors.qualitative.Prism,
                x="name",
                y="num_dags_active",
                text="num_dags_active",
                labels={"num_dags_active": "Active DAGs", "name": "Airflow"},
            )
        ).write_image(output_file, width=1500, height=1000)
    else:
        log.warning(f"'name' not found in report - unable to {title} chart")


def create_tasks_per_airflow_chart(deployment_report: List[DeploymentReport], output_file: str) -> None:
    # noinspection PyUnresolvedReferences
    airflow_df = DataFrame(deployment_report)
    title = "Defined Tasks per Airflow (Log Scale)"
    if "name" in airflow_df:
        airflow_df["name"] = airflow_df["name"].str.split("|").str[0]

        if len(airflow_df) > 40:
            airflow_df = airflow_df.nlargest(40, "num_tasks")
            title += " (Top 40)"
        # noinspection PyUnresolvedReferences
        prettify_bar_chart(
            px.bar(
                airflow_df,
                title=title,
                color_discrete_sequence=px.colors.qualitative.Prism,
                x="name",
                y="num_tasks",
                log_y=True,
                text="num_tasks",
                labels={"num_tasks": "Defined Tasks", "name": "Airflow"},
            )
        ).write_image(output_file, width=1500, height=1000)
    else:
        log.warning(f"'name' not found in report - unable to create {title} chart")


def create_task_runs_per_airflow_chart(deployment_report: List[DeploymentReport], output_file: str) -> None:
    # noinspection PyUnresolvedReferences
    airflow_df = DataFrame(deployment_report)
    title = "Monthly Successful Task Runs per Airflow (Log Scale)"
    if "name" in airflow_df:
        airflow_df["name"] = airflow_df["name"].str.split("|").str[0]

        airflow_df["task_runs_monthly_success"] = airflow_df["task_runs_monthly_success"].clip(lower=0)

        if len(airflow_df) > 40:
            airflow_df = airflow_df.nlargest(40, "task_runs_monthly_success")
            title += " (Top 40)"
        # noinspection PyUnresolvedReferences
        prettify_bar_chart(
            px.bar(
                airflow_df,
                title=title,
                color_discrete_sequence=px.colors.qualitative.Prism,
                x="name",
                y="task_runs_monthly_success",
                labels={"task_runs_monthly_success": "Monthly Successful Task Runs", "name": "Airflow"},
                log_y=True,
                text="task_runs_monthly_success",
            )
        ).write_image(output_file, width=1500, height=1000)
    else:
        log.warning(f"'name' not found in report - unable to create {title} chart")


def create_airflow_operator_set_chart(deployment_report: List[DeploymentReport], output_file: str) -> None:
    # noinspection PyUnresolvedReferences
    airflow_df = DataFrame(deployment_report)
    title = "Unique Operator Set (Operator Counted Once Per Airflow)"
    if "unique_operators" in airflow_df:
        # noinspection PyUnresolvedReferences
        vc = airflow_df["unique_operators"].explode(ignore_index=True).replace("", np.NaN).dropna().value_counts()

        if len(vc) > 40:
            vc = vc.nlargest(40)
            title += " (Top 40)"
        # noinspection PyUnresolvedReferences
        prettify_bar_chart(
            px.bar(
                vc,
                title=title,
                color_discrete_sequence=px.colors.qualitative.Prism,
                x=vc.index,
                y=vc.values,
                labels={"y": "Num Airflow Containing", "index": "Operator"},
                text=vc.values,
            )
        ).write_image(output_file, width=1500, height=1000)
    else:
        log.warning(f"'unique_operators' not found in report - unable to create {title} chart")


def create_dag_operator_set_chart(dag_report: List[DAGReport], output_file: str) -> None:
    # noinspection PyUnresolvedReferences
    dag_df = DataFrame(dag_report)
    title = "Unique Operator Set (Operator Counted Once Per DAG, Log Scale)"
    if "operators" in dag_df:
        # noinspection PyUnresolvedReferences
        vc = dag_df["operators"].str.split(",").explode(ignore_index=True).replace("", np.NaN).dropna().value_counts()

        if len(vc) > 40:
            vc = vc.nlargest(40)
            title += " (Top 40)"
        # noinspection PyUnresolvedReferences
        prettify_bar_chart(
            px.bar(
                vc,
                title=title,
                color_discrete_sequence=px.colors.qualitative.Prism,
                x=vc.index,
                y=vc.values,
                labels={"y": "Num DAGs Containing", "index": "Operator"},
                log_y=True,
                text=vc.values,
            )
        ).write_image(output_file, width=1500, height=1000)
    else:
        log.warning(f"'operators' not found in report - unable to create {title} chart")


AIRFLOW_CHARTS = {
    "Airflow Versions": (create_airflow_versions_chart, "Deployment Report"),
    "DAGs per Airflow": (create_dags_per_airflow_chart, "Deployment Report"),
    "Tasks per Airflow": (create_tasks_per_airflow_chart, "Deployment Report"),
    "Monthly Task Runs per Airflow": (create_task_runs_per_airflow_chart, "Deployment Report"),
    "Operator Set by Airflow": (create_airflow_operator_set_chart, "Deployment Report"),
    "Operator Set by DAG": (create_dag_operator_set_chart, "DAG Report"),
}
