import json

import pytest
from click.testing import CliRunner
from pytest_mock import MockerFixture

from telescope.__main__ import cli
from telescope.getter_util import gather_getters, parse_getters_from_hosts_file
from telescope.getters.docker import LocalDockerGetter
from telescope.getters.kubernetes import KubernetesGetter
from telescope.getters.local import LocalGetter
from telescope.getters.ssh import SSHGetter
from telescope.util import remove_initial_log_lines
from tests.conftest import manual_tests

SAMPLE_HOSTS = {
    "local": None,
    "ssh": [{"host": "foo.bar.baz"}, {"host": "1.2.3.4"}],
    "docker": [{"container_id": "demo9b25c0_scheduler_1"}],
    "kubernetes": [
        {
            "namespace": "astronomer-amateur-cosmos-2865",
            "name": "amateur-cosmos-2865-scheduler-bfcfbd7b5-dvqqr",
            "container": "scheduler",
        }
    ],
}


# noinspection PyTypeChecker
@manual_tests
def test_cli_docker():
    runner = CliRunner()
    result = runner.invoke(cli, "--docker -o '-'")
    if result.exit_code != 0:
        print(result.output)
    assert result.exit_code == 0
    actual = json.loads(result.output.split("\n")[-1])
    assert type(actual) == dict
    # TODO - fill out docker autodiscovery


# noinspection PyTypeChecker
@manual_tests
def test_cli_kubernetes():
    runner = CliRunner()
    result = runner.invoke(cli, "--kubernetes -o '-'")
    print(result.output)
    assert result.exit_code == 0
    actual = json.loads(remove_initial_log_lines(result.output))
    assert type(actual) == dict
    # TODO - fill out kube autodiscovery


# noinspection PyTypeChecker
@manual_tests
def test_cli_local():
    runner = CliRunner()
    result = runner.invoke(cli, "--local -o '-'")
    print(result.output)
    assert result.exit_code == 0
    actual = json.loads(remove_initial_log_lines(result.output))
    assert type(actual) == dict


def test_gather_getters_local():
    actual = gather_getters(use_local=True)
    expected = {"local": [LocalGetter()]}
    assert actual == expected


def test_mock_gather_getters_kube_autodiscovery(mocker):
    def _kube_autodiscover(**kwargs):
        return [{"name": "foo", "namespace": "bar", "container": "scheduler"}]

    mocker.patch("telescope.getter_util.kube_autodiscover", _kube_autodiscover)

    actual = gather_getters(use_kubernetes=True)
    expected = {"kubernetes": [KubernetesGetter(**_kube_autodiscover()[0])]}
    assert actual == expected


def test_mock_gather_getters_docker_autodiscovery(mocker: MockerFixture):
    def _docker_autodiscover(**kwargs):
        return [{"container_id": "foo"}]

    mocker.patch("telescope.getter_util.docker_autodiscover", _docker_autodiscover)

    actual = gather_getters(use_docker=True)
    expected = {"docker": [LocalDockerGetter(**_docker_autodiscover()[0])]}
    assert actual == expected


def test_parse_getters_from_hosts_file():
    actual = parse_getters_from_hosts_file(SAMPLE_HOSTS)
    expected = {
        "local": [],
        "ssh": [SSHGetter(**ssh) for ssh in SAMPLE_HOSTS["ssh"]],
        "kubernetes": [KubernetesGetter(**kube) for kube in SAMPLE_HOSTS["kubernetes"]],
        "docker": [LocalDockerGetter(**docker) for docker in SAMPLE_HOSTS["docker"]],
    }
    assert actual == expected
