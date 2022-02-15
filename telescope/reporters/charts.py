from typing import List

import logging

from lazyimport import lazyimport

from telescope.reports import AirflowReport, DAGReport

lazyimport(
    globals(),
    """
import numpy as np
import plotly.express as px
from pandas import DataFrame
import pandas as pd
""",
)

log = logging.getLogger(__name__)


# noinspection PyUnresolvedReferences
def pretty_pie_chart(fig):
    fig.update_traces(
        textposition="outside",
        texttemplate="%{label} - %{value:s} Deployments <br>(%{percent})",
    )
    fig.update_layout(margin=dict(l=5, r=5, t=50, b=5), showlegend=False)
    return fig


# noinspection PyUnresolvedReferences
def create_airflow_versions_chart(airflow_reports: List[AirflowReport], output_file: str) -> None:
    airflow_df = pd.DataFrame(airflow_reports)
    title = "Airflow Version"
    if "version" in airflow_df:
        vc = airflow_df["version"].value_counts()
        pretty_pie_chart(
            px.pie(
                vc,
                title=title,
                color_discrete_sequence=px.colors.qualitative.Prism,
                names=vc.index,
                values=vc.values,
            )
        ).write_image(output_file)
    else:
        log.warning(f"'version' not found in report - unable to create {title} chart")


# noinspection PyUnresolvedReferences
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


# noinspection PyUnresolvedReferences
def create_dags_per_airflow_chart(airflow_reports: List[AirflowReport], output_file: str) -> None:
    airflow_df = pd.DataFrame(airflow_reports)
    title = "Active DAGs per Airflow"
    if "name" in airflow_df:
        airflow_df["name"] = airflow_df["name"].str.split("|").str[0]
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
        ).write_image(output_file)
    else:
        log.warning(f"'name' not found in report - unable to {title} chart")


# noinspection PyUnresolvedReferences
def create_tasks_per_airflow_chart(airflow_reports: List[AirflowReport], output_file: str) -> None:
    airflow_df = pd.DataFrame(airflow_reports)
    title = "Tasks per Airflow (Log Scale)"
    if "name" in airflow_df:
        airflow_df["name"] = airflow_df["name"].str.split("|").str[0]
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
        ).write_image(output_file)
    else:
        log.warning(f"'name' not found in report - unable to create {title} chart")


# noinspection PyUnresolvedReferences
def create_task_runs_per_airflow_chart(airflow_reports: List[AirflowReport], output_file: str) -> None:
    airflow_df = pd.DataFrame(airflow_reports)
    title = "Monthly Successful Task Runs per Airflow (Log Scale)"
    if "name" in airflow_df:
        airflow_df["name"] = airflow_df["name"].str.split("|").str[0]
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
        ).write_image(output_file)
    else:
        log.warning(f"'name' not found in report - unable to create {title} chart")


# noinspection PyUnresolvedReferences
def create_airflow_operator_set_chart(airflow_reports: List[AirflowReport], output_file: str) -> None:
    airflow_df = pd.DataFrame(airflow_reports)
    title = "Unique Operator Set (Operator Counted Once Per Airflow)"
    if "unique_operators" in airflow_df:
        vc = airflow_df["unique_operators"].explode(ignore_index=True).replace("", np.NaN).dropna().value_counts()
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
        ).write_image(output_file)
    else:
        log.warning(f"'unique_operators' not found in report - unable to create {title} chart")


# noinspection PyUnresolvedReferences
def create_dag_operator_set_chart(dag_report: List[DAGReport], output_file: str) -> None:
    dag_df = pd.DataFrame(dag_report)
    title = "Unique Operator Set (Operator Counted Once Per DAG, Log Scale)"
    if "operators" in dag_df:
        vc = dag_df["operators"].str.split(",").explode(ignore_index=True).replace("", np.NaN).dropna().value_counts()
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
        ).write_image(output_file)
    else:
        log.warning(f"'operators' not found in report - unable to create {title} chart")


AIRFLOW_CHARTS = {
    "Airflow Versions": (create_airflow_versions_chart, "Airflow Report"),
    "DAGs per Airflow": (create_dags_per_airflow_chart, "Airflow Report"),
    "Tasks per Airflow": (create_tasks_per_airflow_chart, "Airflow Report"),
    "Monthly Task Runs per Airflow": (create_task_runs_per_airflow_chart, "Airflow Report"),
    "Operator Set by Airflow": (create_airflow_operator_set_chart, "Airflow Report"),
    "Operator Set by DAG": (create_dag_operator_set_chart, "DAG Report"),
}
