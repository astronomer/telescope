import tarfile

try:
    from importlib.resources import path
except ModuleNotFoundError:
    from importlib_resources import path

from io import BytesIO
from time import sleep, time

import docker
import pytest
from docker.models.containers import Container

import airflow_report
from airflow_report.__main__ import dag_varconn_usage
from astronomer_telescope.util import clean_airflow_report_output
from tests import resources
from tests.conftest import manual_tests


@pytest.fixture
def docker_client():
    return docker.from_env()


@pytest.fixture()
def example_dag_path():
    with path(resources, "example-dag.py") as p:
        return str(p.resolve())


@pytest.fixture(
    params=[
        "apache/airflow:2.3.4",
        "apache/airflow:2.2.4",
        "apache/airflow:2.1.3",
        "apache/airflow:2.0.0",
        "apache/airflow:1.10.15",
        "apache/airflow:1.10.10",
        "bitnami/airflow:1.10.2",
    ]
)
def docker_scheduler(docker_client, request):
    scheduler = docker_client.containers.run(
        request.param,
        entrypoint="sh",
        command='-c "(airflow db upgrade || airflow upgradedb) && airflow scheduler"',
        detach=True,
        remove=True,
    )
    timeout, elapsed_time = 120, 0
    sleep_time = 3
    status = docker_client.containers.get(scheduler.id).status
    while status != "running" and elapsed_time < timeout:
        print("Not running, sleeping...")
        sleep(sleep_time)
        elapsed_time += sleep_time
        status = docker_client.containers.get(scheduler.id)
    print("Scheduler started, waiting for db migrations and initialization...")
    for line in scheduler.logs(stream=True):
        if b"Starting the scheduler" in line:
            print("Scheduler started! Handing off container")
            break
    yield scheduler
    scheduler.stop()
    # scheduler.remove()


def copy_to_container(container: Container, container_path: str, local_path: str, name: str):
    def create_archive():
        pw_tarstream = BytesIO()
        pw_tar = tarfile.TarFile(fileobj=pw_tarstream, mode="w")
        file_data = open(local_path, "rb").read()
        tarinfo = tarfile.TarInfo(name=name)
        tarinfo.size = len(file_data)
        tarinfo.mtime = time()
        pw_tar.addfile(tarinfo, BytesIO(file_data))
        pw_tar.close()
        pw_tarstream.seek(0)
        return pw_tarstream

    with create_archive() as archive:
        container.put_archive(path=container_path, data=archive)


@manual_tests
def test_airflow_report(docker_scheduler: Container):
    with path(airflow_report, "__main__.py") as p:
        airflow_report_path = str(p.resolve())

    if "bitnami" in str(docker_scheduler.image):
        fpath = "/opt/bitnami/airflow/"
        run = "bash -c 'cd /opt/bitnami/airflow/ && source venv/bin/activate && python __main__.py'"
    else:
        fpath = "/opt/airflow/"
        run = "python __main__.py"

    copy_to_container(docker_scheduler, fpath, local_path=airflow_report_path, name="__main__.py")
    exit_code, output = docker_scheduler.exec_run(run)
    print(output.decode("utf-8"))
    report = clean_airflow_report_output(output.decode("utf-8"))

    print(report)

    assert "airflow_version_report" in report  # '2.2.1'
    assert (
        type(report["airflow_version_report"]) == str
    ), f'airflow_version_report: {report["airflow_version_report"]} - {type(report["airflow_version_report"])} != str'
    assert "." in report["airflow_version_report"]

    assert "hostname_report" in report  # '0ad460b0b358'
    assert (
        type(report["hostname_report"]) == str
    ), f'hostname_report: {report["hostname_report"]} - {type(report["hostname_report"])} != str'

    assert "providers_report" in report
    assert type(report["providers_report"]) in [
        type(None),
        dict,
    ], "providers_report is either a dict of providers or None if it's 1.x (not supported)"

    assert "installed_packages_report" in report
    assert (
        type(report["installed_packages_report"]) == dict
    ), f'installed_packages_report: {report["installed_packages_report"]} - {type(report["installed_packages_report"])} != dict'

    assert "configuration_report" in report
    assert (
        type(report["configuration_report"]) == dict
    ), f'configuration_report: {report["configuration_report"]} - {type(report["configuration_report"])} != dict'

    assert "pools_report" in report
    assert type(report["pools_report"]) in [
        list,
        dict,
    ], f'pools_report: {report["pools_report"]} - {type(report["pools_report"])} not in [list, dict]'

    assert "dags_report" in report
    assert (
        type(report["dags_report"]) == list
    ), f'dags_report: {report["dags_report"]} - {type(report["dags_report"])} != list'

    assert "env_vars_report" in report
    assert (
        type(report["env_vars_report"]) == dict
    ), f'env_vars_report: {report["env_vars_report"]} - {type(report["env_vars_report"])} != dict'

    assert "usage_stats_report" in report
    assert (
        type(report["usage_stats_report"]) == list
    ), f'usage_stats_report: {report["usage_stats_report"]} - {type(report["usage_stats_report"])} != list'

    assert "connections_report" in report
    assert (
        type(report["connections_report"]) == list
    ), f'connections_report: {report["connections_report"]} - {type(report["connections_report"])} != list'

    assert "variables_report" in report
    assert (
        type(report["variables_report"]) == list
    ), f'variables_report: {report["variables_report"]} - {type(report["variables_report"])} != list'

    assert "user_report" in report
    if type(report["user_report"]) == dict:
        assert list(report["user_report"].keys()) in [
            [
                "1_days_active_users",
                "7_days_active_users",
                "30_days_active_users",
                "365_days_active_users",
                "total_users",
            ],
            ["total_users"],
        ], f'user_report: {report["user_report"]} - {type(report["user_report"])} != dict or keys are different'


def test_dag_varconn_usage(example_dag_path: str):
    actual = dag_varconn_usage(example_dag_path)
    expected_conns = {"easy_-conn", "harder_-conn", "macro_-conn"}
    expected_vars = {"easy_-var", "value_macro-var", "json_macro-var"}
    expected = (expected_vars, expected_conns)
    assert actual[0] == expected[0]
    assert actual[1] == expected[1]
