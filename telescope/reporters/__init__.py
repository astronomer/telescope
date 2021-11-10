from dataclasses import dataclass
from typing import List, Dict, Any, Optional


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
    def from_input_report_row(infra_type, input_row):
        return InfrastructureReport(type=infra_type, **input_row)


def parse_airflow_report_pools(d: dict) -> str:
    return ", ".join([f"{k} - {v['total']}" for k, v in d.items()])


def parse_airflow_executor(airflow_cfg: List[List[str]]) -> str:
    for [section, name, value, set_by] in airflow_cfg:
        if section == "core" and name == "executor":
            return value
    return ""


@dataclass
class AirflowReport:
    name: str
    version: str
    executor: str
    num_schedulers: int
    num_webservers: int
    num_workers: int
    providers: str  # List[str]
    packages: str  # Dict[str, str]
    airflow_configurations: str  # Dict[str, str]
    non_default_configurations: str  # Dict[str, str]
    pools: str
    env: str  # Dict[str, str]
    connections: str  # List[str]
    task_run_info: str  # Dict[str, int]

    @staticmethod
    def from_input_report_row(name, input_row):
        return AirflowReport(
            name=name,
            version=input_row['AIRFLOW VERSION'],
            executor=parse_airflow_executor(input_row['CONFIGURATION']),
            num_schedulers=-1,
            num_webservers=-1,
            num_workers=0,
            providers="",
            packages="",
            airflow_configurations="",
            non_default_configurations="",
            pools=parse_airflow_report_pools(input_row['POOLS']),
            env="",
            connections="",
            task_run_info=""
        )


@dataclass
class DAGReport:
    airflow_name: str
    dag_id: str
    root_dag_id: str  # dag_id if it's a subdag
    is_active: str  # whether the scheduler has recently seen it
    is_paused: str  # whether the toggle is on/off
    is_subdag: str
    schedule: str
    fileloc: str
    owners: str
    operators: str  # List[str]
    num_tasks: int
    connections: str = ""  # List[str]
    variables: str = ""  # List[str]
