import tarfile
from asyncio import FIRST_EXCEPTION, Future
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor

from io import BytesIO
from time import sleep, time

import pytest
from docker.models.containers import Container

from airflow_report.__main__ import dag_varconn_usage
from astronomer_telescope.util import clean_airflow_report_output
from tests.conftest import manual_tests

AIRFLOW_IMAGES = [
    "apache/airflow:slim-2.8.1",
    "apache/airflow:slim-2.7.3",
    "apache/airflow:slim-2.6.0",
    "apache/airflow:slim-2.5.3",
    "apache/airflow:slim-2.4.0",
    "apache/airflow:2.3.4",
    "apache/airflow:2.2.4",
    "apache/airflow:2.1.3",
    "apache/airflow:2.0.0",
    "apache/airflow:1.10.15",
    "apache/airflow:1.10.10",
    "bitnami/airflow:1.10.2",
]


def skip_no_docker(has_docker):
    """Skips this test if we don't have docker"""
    if not has_docker:
        pytest.skip("skipped, no docker")


@pytest.fixture(scope="session")
def docker_client():
    import docker

    return docker.from_env()


@pytest.fixture(scope="session")
def has_docker():
    from shutil import which

    return which("docker") is not None


@pytest.fixture()
def example_dag_path(project_root):
    return project_root / "tests/resources/example-dag.py"


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


@manual_tests  # requires docker
def test_airflow_report(has_docker, docker_client, project_root):
    skip_no_docker(has_docker)

    with ThreadPoolExecutor() as executor:

        def run_test_for_image(image: str):
            docker_scheduler = docker_client.containers.run(
                image,
                entrypoint="sh",
                command='-c "(airflow db upgrade || airflow upgradedb) && airflow scheduler"',
                detach=True,
                remove=True,
                platform="linux/x86_64",
            )
            timeout, elapsed_time = 120, 0
            sleep_time = 3
            status = docker_client.containers.get(docker_scheduler.id).status
            while status != "running" and elapsed_time < timeout:
                print("Not running, sleeping...")
                sleep(sleep_time)
                elapsed_time += sleep_time
                status = docker_client.containers.get(docker_scheduler.id)
            print("Scheduler started, waiting for db migrations and initialization...")
            for line in docker_scheduler.logs(stream=True):
                if b"Starting the scheduler" in line:
                    print("Scheduler started! Handing off container")
                    break

            airflow_report_path = project_root / "airflow_report/__main__.py"
            if "bitnami" in str(docker_scheduler.image):
                fpath = "/opt/bitnami/airflow/"
                run = "bash -c 'cd /opt/bitnami/airflow/ && source venv/bin/activate && python __main__.py'"
            else:
                fpath = "/opt/airflow/"
                run = "python __main__.py"

            copy_to_container(docker_scheduler, fpath, local_path=str(airflow_report_path), name="__main__.py")
            exit_code, output = docker_scheduler.exec_run(run)
            # print(output.decode("utf-8"))
            report = clean_airflow_report_output(output.decode("utf-8"))
            # print(report)
            docker_scheduler.stop()

            assert "airflow_version_report" in report  # '2.2.1'
            assert isinstance(report["airflow_version_report"], str), (
                f'[{image}] airflow_version_report: {report["airflow_version_report"]}'
                f' - {type(report["airflow_version_report"])} != str'
            )
            assert "." in report["airflow_version_report"]

            assert "hostname_report" in report  # '0ad460b0b358' # pragma: allowlist secret
            assert isinstance(
                report["hostname_report"], str
            ), f'[{image}] hostname_report: {report["hostname_report"]} - {type(report["hostname_report"])} != str'

            assert "providers_report" in report
            assert type(report["providers_report"]) in [
                type(None),
                dict,
            ], f"[{image}] providers_report is either a dict of providers or None if it's 1.x (not supported)"

            assert "installed_packages_report" in report
            assert isinstance(report["installed_packages_report"], dict), (
                f'[{image}] installed_packages_report: {report["installed_packages_report"]}'
                f' - {type(report["installed_packages_report"])} != dict'
            )

            assert "configuration_report" in report
            assert isinstance(report["configuration_report"], dict), (
                f'[{image}] configuration_report: {report["configuration_report"]}'
                f' - {type(report["configuration_report"])} != dict'
            )

            assert "pools_report" in report
            assert type(report["pools_report"]) in [
                list,
                dict,
            ], f'[{image}] pools_report: {report["pools_report"]} - {type(report["pools_report"])} not in [list, dict]'

            assert "dags_report" in report
            assert isinstance(
                report["dags_report"], list
            ), f'[{image}] dags_report: {report["dags_report"]} - {type(report["dags_report"])} != list'

            assert "env_vars_report" in report
            assert isinstance(
                report["env_vars_report"], dict
            ), f'[{image}] env_vars_report: {report["env_vars_report"]} - {type(report["env_vars_report"])} != dict'

            assert "usage_stats_report" in report
            assert isinstance(report["usage_stats_report"], list), (
                f'[{image}] usage_stats_report: {report["usage_stats_report"]}'
                f' - {type(report["usage_stats_report"])} != list'
            )
            # This won't succeed unless there are actual task runs in the database
            # assert len(report["usage_stats_report"]) and list(report["usage_stats_report"][0].keys()) in [
            #     "dag_id",
            #     "1_days_success",
            #     "1_days_failed",
            #     "min_duration_1_days_success",
            #     "max_duration_1_days_success",
            #     "avg_duration_1_days_success",
            #     "7_days_success",
            #     "7_days_failed",
            #     "min_duration_7_days_success",
            #     "max_duration_7_days_success",
            #     "avg_duration_7_days_success",
            #     "30_days_success",
            #     "30_days_failed",
            #     "min_duration_30_days_success",
            #     "max_duration_30_days_success",
            #     "avg_duration_30_days_success",
            #     "365_days_success",
            #     "365_days_failed",
            #     "min_duration_365_days_success",
            #     "max_duration_365_days_success",
            #     "avg_duration_365_days_success",
            #     "all_days_success",
            #     "all_days_failed",
            #     "min_duration_all_days_success",
            #     "max_duration_all_days_success",
            #     "avg_duration_all_days_success",
            # ], f'[{image}] usage_stats_report: {report["usage_stats_report"]} - doesn\'t have the expected keys'

            assert "usage_stats_dag_rollup_report" in report
            assert isinstance(report["usage_stats_dag_rollup_report"], list), (
                f'[{image}] usage_stats_dag_rollup_report: {report["usage_stats_dag_rollup_report"]}'
                f' - {type(report["usage_stats_dag_rollup_report"])} != list'
            )

            assert "connections_report" in report
            assert isinstance(report["connections_report"], list), (
                f'[{image}] connections_report: {report["connections_report"]}'
                f' - {type(report["connections_report"])} != list'
            )

            assert "variables_report" in report
            assert isinstance(
                report["variables_report"], list
            ), f'[{image}] variables_report: {report["variables_report"]} - {type(report["variables_report"])} != list'

            assert "user_report" in report
            if isinstance(report["user_report"], dict):
                assert list(report["user_report"].keys()) in [
                    [
                        "1_days_active_users",
                        "7_days_active_users",
                        "30_days_active_users",
                        "365_days_active_users",
                        "total_users",
                    ],
                    ["total_users"],
                ], (
                    f'[{image}] user_report: {report["user_report"]}'
                    f' - {type(report["user_report"])} != dict or keys are different'
                )

        tests = [executor.submit(run_test_for_image, image) for image in AIRFLOW_IMAGES]
        for test in futures.wait(tests, return_when=FIRST_EXCEPTION)[0]:
            test: Future
            if test.exception():
                raise test.exception()


def test_dag_varconn_usage(example_dag_path: str):
    actual = dag_varconn_usage(example_dag_path)
    expected_conns = {"easy_-conn", "harder_-conn", "macro_-conn"}
    expected_vars = {"easy_-var", "value_macro-var", "json_macro-var"}
    expected = (expected_vars, expected_conns)
    assert actual[0] == expected[0]
    assert actual[1] == expected[1]
