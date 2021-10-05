"""
Airflow system reporting script. Goal was to produce an easily runnable script & transferable output. This script should
be run in a live Airflow environment (i.e. the same settings as your running Airflow). For example, by exec-ing into
your scheduler pod and running `python airflow_debug_report.py`.

The output can be configured via flags/arguments and/or environment variables (flags take precedence over env vars):

airflow_debug_report.py [-o/--output {json,markdown}] [-r/--reporters [{airflow_version,datetime,...}]] [output_dir]
AIRFLOW_REPORT_OUTPUT_FORMAT=markdown AIRFLOW_REPORT_REPORTERS=airflow_version,providers AIRFLOW_REPORT_OUTPUT_DIR=/tmp python airflow_debug_report.py
"""

import argparse
import datetime
import json
import logging
import os
from typing import Any, Dict, List, Callable

import airflow.jobs.base_job
from airflow import DAG
from airflow.models import DagModel, TaskInstance
from airflow.operators.python import PythonOperator
from airflow.utils import timezone
from airflow.utils.log.secrets_masker import should_hide_value_for_key
from airflow.utils.session import provide_session
from sqlalchemy import func


class AirflowReport:
    name = "Airflow Report base class"

    @classmethod
    def get_data(cls) -> Any:
        raise NotImplementedError

    @classmethod
    def report_markdown(cls) -> str:
        """
        Should return a Markdown string formatted as:

        # [REPORT NAME]
        ... data ...
        [finish with newline]

        Default should work unless get_data() returns a collection e.g. list which has to be formatted properly
        """
        return f"# {cls.name}\n{cls.get_data()}\n"

    @classmethod
    def report_json(cls) -> Dict[str, Any]:
        """
        Should return report name + data e.g. {"Airflow Version": "v2.1.3"}
        Default should work unless get_data() returns something not JSON serializable
        """
        return {cls.name: cls.get_data()}


class AirflowVersionReport(AirflowReport):
    name = "AIRFLOW VERSION"

    @classmethod
    def get_data(cls) -> Any:
        return airflow.version.version


class ProvidersReport(AirflowReport):
    name = "PROVIDERS"

    @classmethod
    def get_data(cls) -> Any:
        """Return dict of providers packages {package name: version}"""
        from airflow.providers_manager import ProvidersManager

        providers_manager = ProvidersManager()
        result = {}
        for provider_version, provider_info in providers_manager.providers.values():
            result[provider_info["package-name"]] = provider_version

        return result

    @classmethod
    def report_markdown(cls) -> str:
        result = f"# {cls.name}\n"
        for package_name, package_version in cls.get_data().items():
            result += f"- {package_name}=={package_version}\n"
        return result


class DateTimeReport(AirflowReport):
    name = "DATE & TIME (UTC)"

    @classmethod
    def get_data(cls) -> Any:
        return datetime.datetime.utcnow()

    @classmethod
    def report_json(cls) -> Dict[str, Any]:
        return {cls.name: cls.get_data().isoformat()}


class HostnameReport(AirflowReport):
    name = "HOSTNAME"

    @classmethod
    def get_data(cls) -> Any:
        import socket

        return socket.gethostname()


class InstalledPackagesReport(AirflowReport):
    name = "INSTALLED PACKAGES"

    @classmethod
    def get_data(cls) -> Any:
        import pkg_resources

        sorted_packages = sorted([f"{pkg.key}=={pkg.version}" for pkg in pkg_resources.working_set])
        return sorted_packages

    @classmethod
    def report_markdown(cls) -> str:
        result = f"# {cls.name}\n"
        for pkg in cls.get_data():
            result += f"- {pkg}\n"
        return result


class ConfigurationReport(AirflowReport):
    name = "CONFIGURATION"

    @classmethod
    def get_data(cls) -> Any:
        from airflow.configuration import conf

        running_configuration = []

        # Additional list because these are currently not hidden by the SecretsMasker but might contain passwords
        additional_hide_list = {
            "AIRFLOW__CELERY__BROKER_URL",
            "AIRFLOW__CELERY__FLOWER_BASIC_AUTH",
            "AIRFLOW__CELERY__RESULT_BACKEND",
            "AIRFLOW__CORE__SQL_ALCHEMY_CONN",
        }
        for section, options in conf.as_dict(display_source=True, display_sensitive=True).items():
            for option, (value, config_source) in options.items():
                airflow_env_var_key = f"AIRFLOW__{section.upper()}__{option.upper()}"
                if should_hide_value_for_key(airflow_env_var_key) or airflow_env_var_key in additional_hide_list:
                    running_configuration.append((section, option, "***", config_source))
                else:
                    running_configuration.append((section, option, value, config_source))

        return sorted(running_configuration)

    @classmethod
    def report_markdown(cls) -> str:
        result = f"# {cls.name}\n"
        for config_option in cls.get_data():
            result += f"- {config_option}\n"
        return result


class AirflowEnvVarsReport(AirflowReport):
    name = "ENVIRONMENT VARIABLES"

    @classmethod
    def get_data(cls) -> Any:
        import os

        config_options = 0
        connections = 0
        variables = 0
        for env_var in os.environ.keys():
            if env_var.startswith("AIRFLOW__"):
                config_options += 1
            elif env_var.startswith("AIRFLOW_CONN_"):
                connections += 1
            elif env_var.startswith("AIRFLOW_VAR_"):
                variables += 1

        return {"config_options": config_options, "connections": connections, "variables": variables}

    @classmethod
    def report_markdown(cls) -> str:
        result = f"# {cls.name}\n"
        data = cls.get_data()
        result += f"- {data['config_options']} configuration options set via environment variables\n"
        result += f"- {data['connections']} connections set via environment variables\n"
        result += f"- {data['variables']} variables set via environment variables\n"
        return result


class SchedulerReport(AirflowReport):
    name = "SCHEDULER(S)"

    @classmethod
    @provide_session
    def get_data(cls, session=None) -> Any:
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
        return schedulers_new_to_old

    @classmethod
    def report_markdown(cls) -> str:
        result = f"# {cls.name}\n"
        for scheduler in cls.get_data():
            result += f"- {json.dumps(scheduler)}\n"
        return result


class PoolsReport(AirflowReport):
    name = "POOLS"

    @classmethod
    @provide_session
    def get_data(cls, session=None) -> Any:
        pool_stats = airflow.models.Pool.slots_stats()
        return [*pool_stats.values()]  # Unpacking to avoid non-serializable dict_values type

    @classmethod
    def report_markdown(cls) -> str:
        result = f"# {cls.name}\n"
        for pool_stat in cls.get_data():
            result += f"1. \<pool name obfuscated\>: {pool_stat}\n"
        return result


class UsageStatsReport(AirflowReport):
    name = "USAGE STATISTICS"

    @classmethod
    @provide_session
    def get_data(cls, session=None) -> Any:
        result = {}

        # DAG stats
        paused_dag_count = session.query(func.count()).filter(DagModel.is_paused, DagModel.is_active).scalar()
        unpaused_dag_count = session.query(func.count()).filter(~DagModel.is_paused, DagModel.is_active).scalar()
        dagfile_count = session.query(func.count(func.distinct(DagModel.fileloc))).filter(DagModel.is_active).scalar()
        result["dag_stats"] = {
            "active": paused_dag_count + unpaused_dag_count,
            "unpaused": unpaused_dag_count,
            "paused": paused_dag_count,
            "dag_files": dagfile_count,
        }

        # Task instance stats
        total_task_instances = session.query(TaskInstance).count()
        task_instances_1_day = (
            session.query(TaskInstance)
            .filter(TaskInstance.start_date > timezone.utcnow() - datetime.timedelta(days=1))
            .count()
        )
        task_instances_7_days = (
            session.query(TaskInstance)
            .filter(TaskInstance.start_date > timezone.utcnow() - datetime.timedelta(days=7))
            .count()
        )
        task_instances_30_days = (
            session.query(TaskInstance)
            .filter(TaskInstance.start_date > timezone.utcnow() - datetime.timedelta(days=30))
            .count()
        )
        task_instances_365_days = (
            session.query(TaskInstance)
            .filter(TaskInstance.start_date > timezone.utcnow() - datetime.timedelta(days=365))
            .count()
        )
        result["task_instance_stats"] = {
            "total": total_task_instances,
            "1_day": task_instances_1_day,
            "7_days": task_instances_7_days,
            "30_days": task_instances_30_days,
            "365_days": task_instances_365_days,
        }

        return result

    @classmethod
    def report_markdown(cls) -> str:
        result = f"# {cls.name}\n"
        data = cls.get_data()

        result += "## DAG stats:\n"
        result += f"- {data['dag_stats']['active']} active DAGs, of which:\n"
        result += f"- {data['dag_stats']['unpaused']} unpaused DAGs\n"
        result += f"- {data['dag_stats']['paused']} paused DAGs\n"
        result += (
            f"- {data['dag_stats']['dag_files']} DAG files (more DAGs than DAG files could indicate dynamic DAGs)\n\n"
        )

        result += "## Task instance stats:\n"
        result += f"- {data['task_instance_stats']['total']} total task instances\n"
        result += f"- {data['task_instance_stats']['1_day']} task instances in last 1 day\n"
        result += f"- {data['task_instance_stats']['7_days']} task instances in last 7 days\n"
        result += f"- {data['task_instance_stats']['30_days']} task instances in last 30 days\n"
        result += f"- {data['task_instance_stats']['365_days']} task instances in last 365 days\n"

        return result


def report_json(reporting_classes: List[AirflowReport], output_dir: str = "") -> str:
    result = {}
    for reporter in reporting_classes:
        json_report = reporter.report_json()

        # Try JSON serialization here because serialization errors are hard to trace if only serializing at the end,
        # once the full result has been collected
        try:
            json.dumps(json_report)
        except Exception as e:
            logging.exception("Failed reporting %s (skipped)", reporter.name)
            logging.exception(e)

        result.update(json_report)
        logging.info("Reported %s", reporter.name)

    output_path = os.path.join(output_dir, "airflow_debug_report.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)

    return output_path


def report_markdown(reporting_classes: List[AirflowReport], output_dir: str = "") -> str:
    output_path = os.path.join(output_dir, "airflow_debug_report.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("<!-- This report was automatically generated -->\n")
        for reporter in reporting_classes:
            try:
                f.write(reporter.report_markdown())
                f.write("\n")
                logging.info("Reported %s", reporter.name)
            except Exception as e:
                logging.exception("Failed reporting %s (skipped)", reporter.name)
                logging.exception(e)

    return output_path


def report(reporting_classes: List[AirflowReport], reporting_function: Callable, output_dir: str = ""):
    logging.info("Starting reporting...")
    output_path = reporting_function(reporting_classes=reporting_classes, output_dir=output_dir)
    logging.info("Your Airflow system dump was written to %s", output_path)


# You can run this script as an Airflow DAG...
with DAG(dag_id="airflow_debug_report", start_date=datetime.datetime(2021, 1, 1), schedule_interval=None) as dag:
    PythonOperator(task_id="report", python_callable=report)

# Or by executing "python airflow_debug_report.py"
if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    reporting_formatters = {"json": report_json, "markdown": report_markdown}

    # Mapping of name pass-able via CLI to Python class
    reporting_class_mapping = {
        "airflow_version": AirflowVersionReport,
        "datetime": DateTimeReport,
        "hostname": HostnameReport,
        "providers": ProvidersReport,
        "installed_packages": InstalledPackagesReport,
        "configuration": ConfigurationReport,
        "scheduler": SchedulerReport,
        "pools": PoolsReport,
        "airflow_env_vars": AirflowEnvVarsReport,
        "usage_stats": UsageStatsReport,
    }

    parser.add_argument(
        "-o",
        "--output",
        help="Output format (default JSON)",
        choices=reporting_formatters.keys(),
        default=os.environ.get("AIRFLOW_REPORT_OUTPUT_FORMAT", "json"),
    )

    def get_reporters_default():
        """Function to support handling errors if AIRFLOW_REPORT_REPORTERS is not set correctly"""
        try:
            return os.environ.get("AIRFLOW_REPORT_REPORTERS").split(",")
        except Exception:
            return reporting_class_mapping.keys()

    parser.add_argument(
        "-r",
        "--reporters",
        help="Reporting sections (comma separated)",
        choices=reporting_class_mapping.keys(),
        default=get_reporters_default(),
        nargs="*",
    )
    parser.add_argument(
        "output_dir",
        help="Output directory, defaults to current directory",
        nargs="?",
        default=os.environ.get("AIRFLOW_REPORT_OUTPUT_DIR", ""),
    )
    args = parser.parse_args()

    # Map reporters to Python classes
    reporting_classes = [reporting_class_mapping[key] for key in args.reporters]

    reporting_function = reporting_formatters[args.output]
    report(reporting_classes=reporting_classes, reporting_function=reporting_function, output_dir=args.output_dir)
