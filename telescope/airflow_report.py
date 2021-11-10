from typing import Any

import base64
import datetime
import json
import logging
import sys
from functools import reduce

logging.getLogger("airflow.settings").setLevel(logging.ERROR)
logging.getLogger("google.cloud.bigquery.opentelemetry_tracing").setLevel(logging.ERROR)

import airflow.jobs.base_job
from airflow.models import TaskInstance
from airflow.utils import timezone

try:
    from airflow.utils.session import provide_session
except:
    from typing import Callable, Iterator, TypeVar

    import contextlib
    from functools import wraps
    from inspect import signature

    from airflow import DAG, settings

    RT = TypeVar("RT")

    def find_session_idx(func: Callable[..., RT]) -> int:
        """Find session index in function call parameter."""
        func_params = signature(func).parameters
        try:
            # func_params is an ordered dict -- this is the "recommended" way of getting the position
            session_args_idx = tuple(func_params).index("session")
        except ValueError:
            raise ValueError(f"Function {func.__qualname__} has no `session` argument") from None

        return session_args_idx

    @contextlib.contextmanager
    def create_session():
        """Contextmanager that will create and teardown a session."""
        session = settings.Session
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def provide_session(func: Callable[..., RT]) -> Callable[..., RT]:
        """
        Function decorator that provides a session if it isn't provided.
        If you want to reuse a session or run the function as part of a
        database transaction, you pass it to the function, if not this wrapper
        will create one and close it for you.
        """
        session_args_idx = find_session_idx(func)

        @wraps(func)
        def wrapper(*args, **kwargs) -> RT:
            if "session" in kwargs or session_args_idx < len(args):
                return func(*args, **kwargs)
            else:
                with create_session() as session:
                    return func(*args, session=session, **kwargs)

        return wrapper


try:
    from airflow.utils.log.secrets_masker import should_hide_value_for_key
except ModuleNotFoundError:
    should_hide_value_for_key = lambda x: False  # too old version


def airflow_version_report() -> Any:
    return airflow.version.version


def providers_report() -> Any:
    """Return dict of providers packages {package name: version}"""
    try:
        from airflow.providers_manager import ProvidersManager

        providers_manager = ProvidersManager()
        result = {}
        for provider_version, provider_info in providers_manager.providers.values():
            result[provider_info["package-name"]] = provider_version

        return result
    except ModuleNotFoundError:
        # Older version of airflow
        return None


def hostname_report() -> Any:
    import socket

    return socket.gethostname()


def installed_packages_report() -> Any:
    import pkg_resources

    return {pkg.key: pkg.version for pkg in pkg_resources.working_set}


def configuration_report() -> Any:
    from airflow.configuration import conf

    running_configuration = {}

    # Additional list because these are currently not hidden by the SecretsMasker but might contain passwords
    additional_hide_list = {
        "AIRFLOW__CELERY__BROKER_URL",
        "AIRFLOW__CELERY__FLOWER_BASIC_AUTH",
        "AIRFLOW__CELERY__RESULT_BACKEND",
        "AIRFLOW__CORE__SQL_ALCHEMY_CONN",
    }

    for section, options in conf.as_dict(display_source=True, display_sensitive=True).items():
        if section not in running_configuration:
            running_configuration[section] = {}

        for option, (value, config_source) in options.items():
            airflow_env_var_key = f"AIRFLOW__{section.upper()}__{option.upper()}"
            if should_hide_value_for_key(airflow_env_var_key) or airflow_env_var_key in additional_hide_list:
                running_configuration[section][option] = ("***", config_source)
            else:
                running_configuration[section][option] = (value, config_source)

    return running_configuration


def airflow_env_vars_report() -> Any:
    import os

    config_options = []
    connections = []
    variables = []
    for env_var in os.environ.keys():
        if env_var.startswith("AIRFLOW__"):
            config_options.append(env_var)
        elif env_var.startswith("AIRFLOW_CONN_"):
            connections.append(env_var)
        elif env_var.startswith("AIRFLOW_VAR_"):
            variables.append(env_var)

    return {"config_options": config_options, "connections": connections, "variables": variables}


def pools_report() -> Any:
    try:
        return airflow.models.Pool.slots_stats()
    except AttributeError:
        from typing import Dict, Iterable, Optional, Tuple

        from airflow.exceptions import AirflowException
        from airflow.models import Pool
        from airflow.utils.state import State
        from sqlalchemy.orm.session import Session

        EXECUTION_STATES = {
            State.RUNNING,
            State.QUEUED,
        }

        @provide_session
        def slots_stats(
            *,
            lock_rows: bool = False,
            session: Session = None,
        ) -> Dict[str, dict]:
            """
            Get Pool stats (Number of Running, Queued, Open & Total tasks)
            If ``lock_rows`` is True, and the database engine in use supports the ``NOWAIT`` syntax, then a
            non-blocking lock will be attempted -- if the lock is not available then SQLAlchemy will throw an
            OperationalError.
            :param lock_rows: Should we attempt to obtain a row-level lock on all the Pool rows returns
            :param session: SQLAlchemy ORM Session
            """
            from airflow.models.taskinstance import TaskInstance  # Avoid circular import

            pools: Dict[str, dict] = {}

            query = session.query(Pool.pool, Pool.slots)

            pool_rows: Iterable[Tuple[str, int]] = query.all()
            for (pool_name, total_slots) in pool_rows:
                if total_slots == -1:
                    total_slots = float("inf")  # type: ignore
                pools[pool_name] = dict(total=total_slots, running=0, queued=0, open=0)

            state_count_by_pool = (
                session.query(TaskInstance.pool, TaskInstance.state).filter(
                    TaskInstance.state.in_(list(EXECUTION_STATES))
                )
            ).all()

            # calculate queued and running metrics
            for (pool_name, state) in state_count_by_pool:
                # Some databases return decimal.Decimal here.
                count = 1

                stats_dict = pools.get(pool_name)
                if not stats_dict:
                    continue
                # TypedDict key must be a string literal, so we use if-statements to set value
                if state == "running":
                    stats_dict["running"] = count
                elif state == "queued":
                    stats_dict["queued"] = count
                else:
                    raise AirflowException(f"Unexpected state. Expected values: {EXECUTION_STATES}.")

            # calculate open metric
            for pool_name, stats_dict in pools.items():
                if stats_dict["total"] == -1:
                    # -1 means infinite
                    stats_dict["open"] = -1
                else:
                    stats_dict["open"] = stats_dict["total"] - stats_dict["running"] - stats_dict["queued"]

            return pools

        return slots_stats()


# noinspection SqlNoDataSourceInspection
@provide_session
def dags_report(session) -> Any:
    from airflow.models import DagModel, TaskInstance
    from sqlalchemy import distinct, func, literal_column

    # Use string_agg if it's postgresql, use group_concat otherwise (sqlite, mysql, ?mssql?)
    agg_fn = {"postgresql": func.string_agg}.get(session.bind.dialect.name, func.group_concat)
    agg_fn_input = (
        [distinct(TaskInstance.operator)] + [] if session.bind.dialect.name != "postgresql" else [literal_column("','")]
    )

    dag_model_fields = [
        DagModel.dag_id,
        DagModel.root_dag_id,
        DagModel.is_paused,
        DagModel.is_active,
        DagModel.is_subdag,
        DagModel.fileloc,
        DagModel.owners,
    ]
    q = (
        session.query(
            *dag_model_fields,
            agg_fn(*agg_fn_input).label("operators"),
            func.count(distinct(TaskInstance.task_id)).label("num_tasks"),
        )
        .join(TaskInstance, TaskInstance.dag_id == DagModel.dag_id)
        .group_by(*dag_model_fields)
        # .filter(DagModel.is_active == True)
    )
    return [dict(zip([desc["name"] for desc in q.column_descriptions], res)) for res in q.all()]


@provide_session
def usage_stats_report(session) -> Any:
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

    return {
        "total": total_task_instances,
        "1_day": task_instances_1_day,
        "7_days": task_instances_7_days,
        "30_days": task_instances_30_days,
        "365_days": task_instances_365_days,
    }


reports = [
    airflow_version_report,
    providers_report,
    hostname_report,
    installed_packages_report,
    configuration_report,
    airflow_env_vars_report,
    pools_report,
    dags_report,
    usage_stats_report,
]

if __name__ == "__main__":

    def try_reporter(r):
        try:
            return {r.__name__: r()}
        except Exception as e:
            logging.exception(f"Failed reporting {r.__name__}")
            return {r.__name__: str(e)}

    collected_reports = [try_reporter(report) for report in reports]

    sys.stdout.write("%%%%%%%\n")
    sys.stdout.write(
        base64.encodebytes(
            json.dumps(reduce(lambda x, y: {**x, **y}, collected_reports), default=str).encode("utf-8")
        ).decode("utf-8")
    )
