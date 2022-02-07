from typing import Any, List

import base64
import json
import logging
import re
import sys
from functools import reduce

from sqlalchemy import text

logging.getLogger("airflow.settings").setLevel(logging.ERROR)
logging.getLogger("google.cloud.bigquery.opentelemetry_tracing").setLevel(logging.ERROR)

import airflow.jobs.base_job

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


def env_vars_report() -> Any:
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
    agg_fn_input = [distinct(TaskInstance.operator)] + (
        [] if session.bind.dialect.name != "postgresql" else [literal_column("','")]
    )

    dag_model_fields = [
        DagModel.dag_id,
        DagModel.schedule_interval,
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
    dags = [dict(zip([desc["name"] for desc in q.column_descriptions], res)) for res in q.all()]
    for dag in dags:
        if dag["fileloc"]:
            try:
                dag["variables"], dag["connections"] = dag_varconn_usage(dag["fileloc"])
            except:
                dag["variables"] = None
                dag["connections"] = None
            try:
                for dag_complexity_metric_name, dag_complexity_metric_value in dag_complexity_report(
                    dag["fileloc"]
                ).items():
                    dag[dag_complexity_metric_name] = dag_complexity_metric_value
            except:
                dag["cc_rank"] = None
                dag["mi_rank"] = None
                dag["analysis"] = None
    return dags


var_patterns = [
    re.compile(r"{{[\s]*var.value.([a-zA-Z-_]+)[\s]*}}"),  # "{{ var.value.<> }}"
    re.compile(r"{{[\s]*var.json.([a-zA-Z-_]+)[\s]*}}"),  # "{{ var.json.<> }}"
    re.compile(r"""Variable.get[(]["']([a-zA-Z-_]+)["'][)]"""),  # "Variable.get(<>)"
]

conn_patterns = [
    re.compile(r"""(?=[\w]*[_])conn_id=["']([a-zA-Z-_]+)["']"""),  # "conn_id=<>"
    re.compile(r"[{]{2}[\s]*conn[.]([a-zA-Z-_]+)[.]?"),  # "{{ conn.<> }}"
]


def dag_varconn_usage(dag_path: str):
    var_results = set()
    conn_results = set()
    with open(dag_path) as f:
        dag_contents = f.read()
        for (results, patterns) in [(conn_results, conn_patterns), (var_results, var_patterns)]:
            for pattern in patterns:
                search_results = pattern.findall(dag_contents)
                if search_results:
                    for result in search_results:
                        results.add(result)
    return (var_results or None), (conn_results or None)


def dag_complexity_report(dag_path: str):
    from radon.complexity import average_complexity, cc_rank, cc_visit
    from radon.metrics import mi_rank, mi_visit
    from radon.raw import analyze

    with open(dag_path) as f:
        dag_contents = f.read()
        return {
            "cc_rank": cc_rank(average_complexity(cc_visit(dag_contents))),
            "mi_rank": mi_rank(mi_visit(dag_contents, False)),
            "analysis": analyze(dag_contents)._asdict(),
        }


@provide_session
def connections_report(session) -> List[str]:
    from airflow.models.connection import Connection

    return [conn_id for (conn_id,) in session.query(Connection.conn_id)]


@provide_session
def variables_report(session) -> List[str]:
    from airflow.models.variable import Variable

    return [key for (key,) in session.query(Variable.key)]


def days_ago(dialect: str, days: int) -> str:
    if dialect == "sqlite":
        return f"DATE('now', '-{days} days')"
    elif dialect == "mysql":
        return f"DATE_SUB(NOW(), INTERVAL {days} day)"
    else:
        # postgresql
        return f"now() - interval '{days} days'"


# noinspection SqlResolve
@provide_session
def usage_stats_report(session) -> Any:
    dialect = session.bind.dialect.name
    sql = text(
        f"""
        SELECT
            dag_id,
            (select count(1) from task_instance where state = 'success' AND start_date > {days_ago(dialect, 1)} and dag_id = dag_id) as "1_days_success",
            (select count(1) from task_instance where state = 'failed' AND start_date > {days_ago(dialect, 1)} and dag_id = dag_id) as "1_days_failed",
            (select count(1) from task_instance where state = 'success' AND start_date > {days_ago(dialect, 7)} and dag_id = dag_id) as "7_days_success",
            (select count(1) from task_instance where state = 'failed' AND start_date > {days_ago(dialect, 7)} and dag_id = dag_id) as "7_days_failed",
            (select count(1) from task_instance where state = 'success' AND start_date > {days_ago(dialect, 30)} and dag_id = dag_id) as "30_days_success",
            (select count(1) from task_instance where state = 'failed' AND start_date > {days_ago(dialect, 30)} and dag_id = dag_id) as "30_days_failed",
            (select count(1) from task_instance where state = 'success' AND start_date > {days_ago(dialect, 365)} and dag_id = dag_id) as "365_days_success",
            (select count(1) from task_instance where state = 'failed' AND start_date > {days_ago(dialect, 365)} and dag_id = dag_id) as "365_days_failed",
            (select count(1) from task_instance where state = 'success' and dag_id = dag_id) as "all_days_success",
            (select count(1) from task_instance where state = 'failed' and dag_id = dag_id) as "all_days_failed"
        FROM task_instance
        GROUP BY 1;
    """
    )
    return [dict(r) for r in session.execute(sql)]


# noinspection SqlResolve
@provide_session
def user_report(session) -> Any:
    dialect = session.bind.dialect.name
    sql = text(
        f"""
        SELECT
            (SELECT COUNT(id) FROM ab_user WHERE last_login > {days_ago(dialect, 1)}) AS 1_days_active_users,
            (SELECT COUNT(id) FROM ab_user WHERE last_login > {days_ago(dialect, 7)}) AS 7_days_active_users,
            (SELECT COUNT(id) FROM ab_user WHERE last_login > {days_ago(dialect, 30)}) AS 30_days_active_users,
            (SELECT COUNT(id) FROM ab_user WHERE last_login > {days_ago(dialect, 365)}) AS 365_days_active_users,
            (SELECT COUNT(id) FROM ab_user) AS total_users;
        """
    )
    return [dict(r) for r in session.execute(sql)]


reports = [
    airflow_version_report,
    providers_report,
    hostname_report,
    installed_packages_report,
    configuration_report,
    env_vars_report,
    pools_report,
    dags_report,
    usage_stats_report,
    connections_report,
    variables_report,
    user_report,
]


def main():
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


if __name__ == "__main__":
    main()
