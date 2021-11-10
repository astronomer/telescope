import json
import os
import tarfile
from io import BytesIO
from time import sleep, time

import docker
import pytest
from docker.models.containers import Container

from telescope.util import remove_initial_log_lines


@pytest.fixture
def docker_client():
    return docker.from_env()


@pytest.fixture(params=[
    '2.2.1',
    '2.1.3',
    '1.10.15',
    '1.10.10'
])
def docker_scheduler(docker_client, request):
    scheduler = docker_client.containers.run(f"apache/airflow:{request.param}", entrypoint='sh', command='-c "airflow db upgrade && airflow scheduler"', detach=True, remove=True)
    timeout, elapsed_time = 120, 0
    sleep_time = 3
    status = docker_client.containers.get(scheduler.id)
    while status != 'running' and elapsed_time < timeout:
        print("Not running, sleeping...")
        sleep(sleep_time)
        elapsed_time += sleep_time
        status = docker_client.containers.get(scheduler.id)
    print("Scheduler started, waiting for db migrations and initialization...")
    for line in scheduler.logs(stream=True):
        if b'Starting the scheduler' in line:
            print("Scheduler started! Handing off container")
            break
    yield scheduler
    scheduler.stop()
    # scheduler.remove()


def copy_to_container(container: Container, container_path: str, local_path: str, name: str):
    def create_archive():
        pw_tarstream = BytesIO()
        pw_tar = tarfile.TarFile(fileobj=pw_tarstream, mode='w')
        file_data = open(local_path, 'rb').read()
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
    copy_to_container(docker_scheduler, '/opt/airflow/', local_path='../../telescope/airflow_report.py', name='airflow_report.py')

    # docker exec -e AIRFLOW_REPORT_OUTPUT=- -it 0ad460b0b358 python airflow_report.py
    exit_code, output = docker_scheduler.exec_run("python airflow_report.py", environment={"AIRFLOW_REPORT_OUTPUT": "-"})
    report = json.loads(remove_initial_log_lines(output.decode('utf-8')))
    assert "AIRFLOW VERSION" in report  # '2.2.1'
    assert type(report['AIRFLOW VERSION']) == str

    assert "DATE & TIME (UTC)" in report  # '2021-11-05T21:04:48.456324'
    assert type(report['DATE & TIME (UTC)']) == str

    assert 'HOSTNAME' in report  # '0ad460b0b358'
    assert type(report['HOSTNAME']) == str

    assert 'PROVIDERS' in report
    assert type(report['PROVIDERS']) in [str, dict], "PROVIDERS is either a dict of providers or a string if it's 1.x saying they aren't supported"

    assert 'INSTALLED PACKAGES' in report
    assert type(report['INSTALLED PACKAGES']) == dict

    assert 'CONFIGURATION' in report
    assert type(report['CONFIGURATION']) == list

    assert 'SCHEDULER(S)' in report
    assert type(report['SCHEDULER(S)']) == list

    assert 'POOLS' in report
    assert type(report['POOLS']) == dict

    assert 'ENVIRONMENT VARIABLES' in report
    assert type(report['ENVIRONMENT VARIABLES']) == dict

    assert 'USAGE STATISTICS' in report
    assert type(report['USAGE STATISTICS']) == dict
