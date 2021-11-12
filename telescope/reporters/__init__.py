from typing import Dict, List, Optional, Union

import logging
from collections.abc import MutableMapping
from dataclasses import dataclass

import jmespath

log = logging.getLogger(__name__)


@dataclass
class SummaryReport:
    num_airflows: int
    num_dags_active: int
    num_dags_inactive: int


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

    # was having issues with - and | in key name
    # return jmespath.search(f'[?name == "{deployment_name}".values.{component}.replicas', helm_report)


@dataclass
class AirflowReport:
    name: str
    version: str
    executor: str
    num_schedulers: int
    scheduler_resources: str
    num_webservers: int
    num_workers: int
    providers: Dict[str, str]
    packages: Dict[str, str]
    non_default_configurations: Dict[str, str]
    pools: Dict[str, Dict[str, int]]
    env: Dict[str, List[str]]
    connections: List[str]
    task_run_info: Dict[str, int]

    @staticmethod
    def from_input_report_row(name: str, input_row: dict, verify: dict = None):
        return AirflowReport(
            name=name,
            version=input_row.get("airflow_version_report"),
            executor=jmespath.search("configuration_report.core.executor | [0]", input_row),
            num_schedulers=parse_replicas_from_helm(deployment_name=name, component="scheduler", helm_report=verify),
            scheduler_resources="",
            num_webservers=parse_replicas_from_helm(deployment_name=name, component="webserver", helm_report=verify),
            num_workers=parse_replicas_from_helm(deployment_name=name, component="workers", helm_report=verify),
            providers=input_row.get("providers_report"),
            # ", ".join([f"{k}:{v}" for k, v in (input_row.get("providers_report") or {}).items()]),
            packages=input_row.get("installed_packages_report"),
            # ", ".join([f"{k}=={v}" for k, v in input_row.get("installed_packages_report").items()]),
            non_default_configurations=parse_non_default_configurations(
                config_report=input_row.get("configuration_report", {})
            ),
            pools=input_row.get("pools_report"),
            # ", ".join([f"{k} - {v['total']}" for k, v in input_row.get("pools_report", {}).items()]),
            env=input_row.get("env_vars_report"),
            # "; ".join([f"{k}: {', '.join(v)}" for k, v in input_row.get('env_vars_report', {}).items() if len(v)]),
            connections=input_row.get("env_vars_report", {}).get("connections", [])
            + input_row.get("connections_report", []),
            # ", ".join(input_row.get('env_vars_report', {}).get('connections', []) + input_row.get('connections_report', [])),
            task_run_info=input_row.get("usage_stats_report")
            # "; ".join([f"{k}: {v}" for k, v in input_row.get('usage_stats_report', {}).items()])
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
    operators: str  # List[str]
    num_tasks: int
    connections: str = ""  # List[str]
    variables: str = ""  # List[str]