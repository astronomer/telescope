from typing import Dict, List, Optional

import logging
from dataclasses import dataclass

import jmespath

from telescope.reports_util import (
    dag_is_active,
    parse_chart_version_from_helm,
    parse_deployment_id_from_helm,
    parse_non_default_configurations,
    parse_replicas_from_helm,
    parse_updated_at_from_helm,
    parse_workspace_id_from_helm,
    sum_usage_stats_report_summary,
)

log = logging.getLogger(__name__)


class Report:
    pass


@dataclass
class SummaryReport(Report):
    num_airflows: int
    num_dags_active: int
    num_dags_inactive: int
    num_tasks: int
    num_successful_task_runs_monthly: int

    # 1.3.0 additions
    telescope_version: str
    report_date: str
    organization: str


@dataclass
class InfrastructureReport(Report):
    type: str  # VM or K8s
    provider: str
    version: str
    num_nodes: int
    allocatable_cpu: float
    capacity_cpu: float
    allocatable_gb: float
    capacity_gb: float

    # 1.3.0 additions
    telescope_version: str
    report_date: str
    organization: str


@dataclass
class DeploymentReport(Report):
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
    num_users: int
    users: Dict[str, int]
    num_dags: int
    num_tasks: int
    num_dags_active: int
    num_dags_inactive: int

    # 1.3.0 additions
    workspace_id: Optional[str] = None
    deployment_id: Optional[str] = None
    chart_version: Optional[str] = None

    telescope_version: Optional[str] = None
    report_date: Optional[str] = None
    organization: Optional[str] = None
    product: Optional[str] = None

    @staticmethod
    def error_airflow_report(name: str, error_message: str):
        return DeploymentReport(
            name=name,
            version="Unknown",
            executor=error_message,
            num_schedulers=-1,
            num_webservers=-1,
            num_workers=-1,
            providers={},
            num_providers=-1,
            packages={},
            non_default_configurations={},
            parallelism=-1,
            default_pool_slots=-1,
            num_pools=-1,
            env={},
            connections=[],
            num_connections=-1,
            unique_operators=[],
            task_run_info={},
            task_runs_monthly_success=-1,
            num_users=-1,
            users={},
            num_dags=-1,
            num_tasks=-1,
            num_dags_active=-1,
            num_dags_inactive=-1,
            pools={},
        )

    @staticmethod
    def from_input_report_row(
        name: str,
        input_row: dict,
        product: str,
        verify: dict = None,
        organization: str = None,
        report_date: str = None,
        telescope_version: str = None,
    ) -> "DeploymentReport":
        if type(input_row) != dict:
            # noinspection PyTypeChecker
            return DeploymentReport.error_airflow_report(name, error_message=input_row)
        task_run_info = sum_usage_stats_report_summary(input_row.get("usage_stats_report", []))
        connections = input_row.get("env_vars_report", {}).get("connections", []) + input_row.get(
            "connections_report", []
        )
        try:
            return DeploymentReport(
                name=name,
                version=input_row.get("airflow_version_report"),
                executor=jmespath.search("configuration_report.core.executor | [0]", input_row),
                num_schedulers=parse_replicas_from_helm(
                    deployment_name=name, component="scheduler", helm_report=verify
                ),
                num_webservers=parse_replicas_from_helm(
                    deployment_name=name, component="webserver", helm_report=verify
                ),
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
                num_pools=len(input_row.get("pools_report", {})),
                default_pool_slots=input_row.get("pools_report", {}).get("default_pool", {}).get("total", -1),
                env=input_row.get("env_vars_report"),
                connections=connections,
                num_connections=len(connections),
                unique_operators=list(
                    sorted(
                        {
                            op
                            for dr in (input_row.get("dags_report", []) or [])
                            for op in (dr.get("operators", "") or "").split(",")
                        }
                    )
                ),
                task_run_info=task_run_info,
                task_runs_monthly_success=task_run_info.get("30_days_success", -1),
                num_users=input_row.get("user_report", {}).get("total_users", -1),
                users=input_row.get("user_report", {}),
                num_tasks=sum(dr.get("num_tasks", 0) for dr in input_row.get("dags_report", [])),
                num_dags=len(input_row.get("dags_report", [])),
                num_dags_active=len([0 for dag in input_row.get("dags_report", []) if dag_is_active(dag)]),
                num_dags_inactive=len([0 for dag in input_row.get("dags_report", []) if not dag_is_active(dag)]),
                report_date=report_date,
                telescope_version=telescope_version,
                organization=organization,
                workspace_id=parse_workspace_id_from_helm(deployment_name=name, helm_report=verify, default=name),
                deployment_id=parse_deployment_id_from_helm(deployment_name=name, helm_report=verify, default=name),
                chart_version=parse_chart_version_from_helm(deployment_name=name, helm_report=verify),
                product=product,
            )
        except Exception as e:
            log.error(input_row)
            log.exception(e)


@dataclass
class Deployment(Report):
    # 1.3.0 addition
    telescope_version: str
    report_date: str
    organization: str

    workspace_id: str
    deployment_id: str

    workspace_created_at: Optional[str] = None
    workspace_updated_at: Optional[str] = None

    deployment_created_at: Optional[str] = None
    deployment_updated_at: Optional[str] = None

    product: Optional[str] = None

    @staticmethod
    def from_deployment_report(deployment_report: DeploymentReport, name, verify) -> "Deployment":
        return Deployment(
            telescope_version=deployment_report.telescope_version,
            report_date=deployment_report.report_date,
            organization=deployment_report.organization,
            deployment_id=deployment_report.deployment_id,
            workspace_id=deployment_report.workspace_id,
            deployment_updated_at=parse_updated_at_from_helm(deployment_name=name, helm_report=verify),
            product=deployment_report.product,
        )


@dataclass
class DAGReport(Report):
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
    variables: Optional[str] = None
    connections: Optional[str] = None
    cc_rank: Optional[str] = None
    mi_rank: Optional[str] = None
    analysis: Optional[Dict[str, int]] = None

    # 1.3.0 additions
    telescope_version: Optional[str] = None
    report_date: Optional[str] = None
    organization: Optional[str] = None
    workspace_id: Optional[str] = None
    deployment_id: Optional[str] = None

    product: Optional[str] = None
