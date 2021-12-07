from typing import Dict, List, Optional, Set, Union

import logging
from collections.abc import MutableMapping
from dataclasses import dataclass
from functools import partial, reduce

import jmespath

log = logging.getLogger(__name__)


@dataclass
class SummaryReport:
    num_airflows: int
    num_dags_active: int
    num_dags_inactive: int
    num_tasks: int
    num_successful_task_runs_monthly: int


@dataclass
class InfrastructureReport:
    type: str  # VM or K8s
    provider: str
    version: str
    num_nodes: int
    allocatable_cpu: float
    capacity_cpu: float
    allocatable_gb: float
    capacity_gb: float

    @staticmethod
    def from_input_report_row(input_row):
        return InfrastructureReport(**input_row)


def parse_non_default_configurations(config_report: dict) -> Union[Dict[str, str], MutableMapping]:
    def flatten_dict(d: MutableMapping, parent_key: str = "", sep: str = ".") -> MutableMapping:
        items = []
        for k, v in d.items():
            new_key = parent_key + sep + k if parent_key else k
            if isinstance(v, MutableMapping):
                items.extend(flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    new = {k: {ik: iv for ik, iv in v.items() if iv[1] != "default"} for k, v in config_report.items()}
    filtered = {k: v for k, v in new.items() if len(v)}
    return flatten_dict(filtered)


def parse_non_default_configurations_as_str(config_report: dict) -> str:
    return ", ".join([f"{k}: {v[0]}" for k, v in parse_non_default_configurations(config_report).items()])


def parse_replicas_from_helm(deployment_name: str, component: str, helm_report: dict) -> int:
    for k in helm_report:
        if (
            k.get("namespace") in deployment_name
            and k.get("name") in deployment_name
            and k.get("name") + k.get("namespace") != "astronomerastronomer"
        ):
            return k.get("values", {}).get(component, {}).get("replicas", 1)
    return -1


# noinspection PyBroadException,TryExceptPass
def sum_usage_stats_report_summary(usage_stats_report: Optional[List[Dict[str, int]]]) -> Dict[str, int]:
    """reduce the usage stats split out by dag, and reduce, and calc % of failures"""
    sum_report = {}

    def accumulate(key, accumulator, next_val):
        return accumulator + next_val.get(key, 0)

    # Take all the keys from the first record -
    # keys = ['1_days_success', '1_days_failed', '7_days_success', '7_days_failed', '30_days_success',
    #           '30_days_failed', '365_days_success', '365_days_failed', 'all_days_success', 'all_days_failed']
    # Reduce them all down to a sum value, then further summarize to successes and percents
    if type(usage_stats_report) == list and len(usage_stats_report):
        reduced = {
            key: reduce(partial(accumulate, key), usage_stats_report, 0)
            for key in usage_stats_report[0].keys()
            if key != "dag_id"
        }
        for key, value in reduced.items():
            if "_failed" in key:
                key_success = key.replace("_failed", "_success")
                key_pct = key.replace("_failed", "_failed_pct")
                try:
                    value_all = reduced.get(key_success, 1) + value
                    if value_all != 0:
                        value_pct = int(value / value_all * 100)  # failed / success
                        sum_report[key_pct] = value_pct
                    else:
                        sum_report[key_pct] = 0
                except Exception:
                    sum_report[key_pct] = -1
            else:
                sum_report[key] = value
    return sum_report


def dag_is_active(dag: dict) -> bool:
    return dag.get("is_active", False) and not dag.get("is_paused", False)


@dataclass
class AirflowReport:
    name: str
    version: str
    executor: str
    num_schedulers: int
    num_webservers: int
    num_workers: int
    providers: Dict[str, str]
    num_providers: int
    packages: Dict[str, str]
    non_default_configurations: Dict[str, str]
    parallelism: int
    pools: Dict[str, Dict[str, int]]
    default_pool_slots: int
    num_pools: int
    env: Dict[str, List[str]]
    connections: List[str]
    num_connections: int
    unique_operators: List[str]
    task_run_info: Dict[str, int]
    task_runs_monthly_success: int
    num_dags: int
    num_tasks: int
    num_dags_active: int
    num_dags_inactive: int

    @staticmethod
    def from_input_report_row(name: str, input_row: dict, verify: dict = None):
        task_run_info = sum_usage_stats_report_summary(input_row.get("usage_stats_report", []))
        connections = input_row.get("env_vars_report", {}).get("connections", []) + input_row.get(
            "connections_report", []
        )
        return AirflowReport(
            name=name,
            version=input_row.get("airflow_version_report"),
            executor=jmespath.search("configuration_report.core.executor | [0]", input_row),
            num_schedulers=parse_replicas_from_helm(deployment_name=name, component="scheduler", helm_report=verify),
            num_webservers=parse_replicas_from_helm(deployment_name=name, component="webserver", helm_report=verify),
            num_workers=parse_replicas_from_helm(deployment_name=name, component="workers", helm_report=verify),
            providers=input_row.get("providers_report", []),
            num_providers=len(input_row.get("providers_report", []) or []),
            packages=input_row.get("installed_packages_report"),
            non_default_configurations=parse_non_default_configurations(
                config_report=input_row.get("configuration_report", {})
            ),
            parallelism=int(
                input_row.get("configuration_report", {}).get("core", {}).get("parallelism", ("-1", "-1"))[0]
            ),
            pools=input_row.get("pools_report"),
            num_pools=len(input_row.get("pools_report")),
            default_pool_slots=input_row.get("pools_report", {}).get("default_pool", {}).get("total", -1),
            env=input_row.get("env_vars_report"),
            connections=connections,
            num_connections=len(connections),
            unique_operators=list(
                {
                    op
                    for dr in (input_row.get("dags_report", []) or [])
                    for op in (dr.get("operators", "") or "").split(",")
                }
            ),
            task_run_info=task_run_info,
            task_runs_monthly_success=task_run_info.get("30_days_success", -1),
            num_tasks=sum(dr.get("num_tasks", 0) for dr in input_row.get("dags_report", [])),
            num_dags=len(input_row.get("dags_report", [])),
            num_dags_active=len([0 for dag in input_row.get("dags_report", []) if dag_is_active(dag)]),
            num_dags_inactive=len([0 for dag in input_row.get("dags_report", []) if not dag_is_active(dag)]),
        )


@dataclass
class DAGReport:
    airflow_name: str
    dag_id: str
    root_dag_id: Optional[str]  # dag_id if it's a subdag
    is_active: bool  # whether the scheduler has recently seen it
    is_paused: bool  # whether the toggle is on/off
    is_subdag: bool
    schedule_interval: Optional[str]
    fileloc: str
    owners: str
    operators: str
    num_tasks: int
