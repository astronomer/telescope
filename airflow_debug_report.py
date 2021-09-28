"""
Airflow system reporting script. Goal was to produce an easily runnable script & transferable output.

This script should be run in a live Airflow environment (i.e. the same settings as your running Airflow). For example,
by exec-ing into your scheduler pod and running `python airflow_debug_report.py`.
"""

import datetime
import json
import logging
import socket
import sys

import airflow.jobs.base_job
from airflow import DAG
from airflow.models import DagModel
from airflow.operators.python import PythonOperator
from airflow.utils.session import provide_session
from sqlalchemy import func


class AirflowReport:
    name = "Airflow Report base class"

    @classmethod
    def report_markdown(cls) -> str:
        raise NotImplementedError


class AirflowVersionReport(AirflowReport):
    name = "AIRFLOW VERSION"

    @classmethod
    def report_markdown(cls) -> str:
        return f"# {cls.name}\n{airflow.version.version}\n\n"


class ProvidersReport(AirflowReport):
    name = "PROVIDERS"

    @classmethod
    def report_markdown(cls) -> str:
        from airflow.providers_manager import ProvidersManager

        providers_manager = ProvidersManager()
        result = f"# {cls.name}\n"
        for provider_version, provider_info in providers_manager.providers.values():
            result += f"- {provider_info['package-name']}=={provider_version}\n"

        result += "\n"
        return result


class DateTimeReport(AirflowReport):
    name = "DATE & TIME (UTC)"

    @classmethod
    def report_markdown(cls) -> str:
        return f"# {cls.name}\n{datetime.datetime.utcnow()}\n\n"


class HostnameReport(AirflowReport):
    name = "HOSTNAME"

    @classmethod
    def report_markdown(cls) -> str:
        return f"# {cls.name}\n{socket.gethostname()}\n\n"


class InstalledPackagesReport(AirflowReport):
    name = "INSTALLED PACKAGES"

    @classmethod
    def report_markdown(cls) -> str:
        import pkg_resources

        result = f"# {cls.name}\n"
        sorted_packages = sorted([f"{pkg.key}=={pkg.version}" for pkg in pkg_resources.working_set])
        for pkg in sorted_packages:
            result += f"- {pkg}\n"

        result += "\n"
        return result


class ConfigurationReport(AirflowReport):
    name = "CONFIGURATION"

    @classmethod
    def report_markdown(cls) -> str:
        from airflow.configuration import conf

        running_configuration = []
        for section, options in conf.as_dict(display_source=True, display_sensitive=True).items():
            for option, (value, config_source) in options.items():
                running_configuration.append((section, option, value, config_source))

        result = f"# {cls.name}\n"
        for config_option in sorted(running_configuration):
            result += f"- {config_option}\n"

        result += "\n"
        return result


class SchedulerReport(AirflowReport):
    name = "SCHEDULER(S)"

    @classmethod
    @provide_session
    def report_markdown(cls, session=None) -> str:
        scheduler_jobs = session.query(airflow.jobs.scheduler_job.SchedulerJob).all()
        schedulers = []
        for scheduler_job in scheduler_jobs:
            schedulers.append(
                {
                    "state": scheduler_job.state,
                    "start_date": scheduler_job.start_date.isoformat(),
                    "end_date": scheduler_job.end_date.isoformat() if scheduler_job.end_date else None,
                    "duration": str(scheduler_job.end_date - scheduler_job.start_date)
                    if scheduler_job.end_date
                    else None,
                }
            )
        schedulers_new_to_old = sorted(schedulers, key=lambda k: k["start_date"], reverse=True)

        result = f"# {cls.name}\n"
        for scheduler in schedulers_new_to_old:
            result += f"- {json.dumps(scheduler)}\n"
        result += "\n"
        return result


class PoolsReport(AirflowReport):
    name = "POOLS"

    @classmethod
    def report_markdown(cls, session=None) -> str:
        pool_stats = airflow.models.Pool.slots_stats()
        result = f"# {cls.name}\n"
        for pool_stat in pool_stats.values():
            result += f"1. \<pool name obfuscated\>: {pool_stat}\n"
        result += "\n"
        return result


class UsageStatsReport(AirflowReport):
    name = "USAGE STATISTICS"

    @classmethod
    @provide_session
    def report_markdown(cls, session=None) -> str:
        result = f"# {cls.name}\n"

        paused_dag_count = session.query(func.count()).filter(DagModel.is_paused, DagModel.is_active).all()[0][0]
        unpaused_dag_count = session.query(func.count()).filter(~DagModel.is_paused, DagModel.is_active).all()[0][0]
        total_dag_count = paused_dag_count + unpaused_dag_count
        result += f"- DAG stats: {total_dag_count} DAGs of which {unpaused_dag_count} unpaused and {paused_dag_count} paused\n"

        result += "\n"
        return result


def report(filename: str = "airflow_debug_report.md"):
    reporters = [
        AirflowVersionReport,
        DateTimeReport,
        HostnameReport,
        ProvidersReport,
        InstalledPackagesReport,
        ConfigurationReport,
        SchedulerReport,
        PoolsReport,
        UsageStatsReport,
    ]
    with open(filename, "w", encoding="utf-8") as f:
        f.write("<!-- This report was automatically generated -->\n")
        for reporter in reporters:
            try:
                f.write(reporter.report_markdown())
                logging.info("Reported %s", reporter.name)
            except Exception as e:
                logging.exception("Failed reporting %s", reporter.name)
                logging.exception(e)

    logging.info("Your Airflow system dump was written to %s", filename)


# You can run this script as an Airflow DAG...
with DAG(dag_id="airflow_debug_report", start_date=datetime.datetime(2021, 1, 1), schedule_interval=None) as dag:
    PythonOperator(task_id="report", python_callable=report)

# Or by executing "python airflow_debug_report.py [filename]"
if __name__ == "__main__":
    try:
        output_filename = sys.argv[1]
        report(filename=output_filename)
    except:
        report()
