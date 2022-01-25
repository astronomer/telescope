import json
import tarfile
from importlib.resources import path
from io import BytesIO
from time import sleep, time

import pytest
from docker.models.containers import Container

import airflow_report
import docker
from telescope.util import clean_airflow_report_output


@pytest.fixture
def docker_client():
    return docker.from_env()


@pytest.fixture(params=["2.2.1", "2.1.3", "1.10.15", "1.10.10"])
def docker_scheduler(docker_client, request):
    scheduler = docker_client.containers.run(
        f"apache/airflow:{request.param}",
        entrypoint="sh",
        command='-c "(airflow db upgrade || airflow upgradedb) && airflow scheduler"',
        detach=True,
        remove=True,
    )
    timeout, elapsed_time = 120, 0
    sleep_time = 3
    status = docker_client.containers.get(scheduler.id)
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


@pytest.mark.slow_integration_test
def test_airflow_report(docker_scheduler):
    with path(airflow_report, "__main__.py") as p:
        airflow_report_path = str(p.resolve())

    copy_to_container(docker_scheduler, "/opt/airflow/", local_path=airflow_report_path, name="__main__.py")

    exit_code, output = docker_scheduler.exec_run("python __main__.py")
    print(output.decode("utf-8"))
    report = json.loads(clean_airflow_report_output(output.decode("utf-8")))
    assert "airflow_version_report" in report  # '2.2.1'
    assert type(report["airflow_version_report"]) == str
    assert "." in report["airflow_version_report"]

    assert "hostname_report" in report  # '0ad460b0b358'
    assert type(report["hostname_report"]) == str

    assert "providers_report" in report
    assert type(report["providers_report"]) in [
        type(None),
        dict,
    ], "providers_report is either a dict of providers or None if it's 1.x (not supported)"

    assert "installed_packages_report" in report
    assert type(report["installed_packages_report"]) == dict

    assert "configuration_report" in report
    assert type(report["configuration_report"]) == dict

    assert "pools_report" in report
    assert type(report["pools_report"]) == dict

    assert "dags_report" in report
    assert type(report["dags_report"]) == list

    assert "env_vars_report" in report
    assert type(report["env_vars_report"]) == dict

    assert "usage_stats_report" in report
    assert type(report["usage_stats_report"]) == list

    assert "connections_report" in report
    assert type(report["connections_report"]) == list

    assert "variables_report" in report
    assert type(report["variables_report"]) == list
