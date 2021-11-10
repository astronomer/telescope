import json

import pytest
from click.testing import CliRunner
from pytest_mock import MockerFixture

from telescope.__main__ import cli, parse_getters_from_hosts_file, gather_getters
from telescope.getters.docker import LocalDockerGetter
from telescope.getters.kubernetes import KubernetesGetter
from telescope.getters.local import LocalGetter
from telescope.getters.ssh import SSHGetter

from telescope.util import remove_initial_log_lines

SAMPLE_HOSTS = {
    "local": None,
    "ssh": [
        {"host": "foo.bar.baz"},
        {"host": "1.2.3.4"}
    ],
    "docker": [
        {"container_id": "demo9b25c0_scheduler_1"}
    ],
    "kubernetes": [
        {"namespace": "astronomer-amateur-cosmos-2865", "name": "amateur-cosmos-2865-scheduler-bfcfbd7b5-dvqqr", "container": "scheduler"}
    ]
}


# noinspection PyTypeChecker
@pytest.mark.slow_integration_test
def test_cli_local_json():
    """https://click.palletsprojects.com/en/8.0.x/testing/#basic-testing"""
    runner = CliRunner()
    result = runner.invoke(cli, "--local --report=false -o '-'")
    assert result.exit_code == 0
    actual = json.loads(remove_initial_log_lines(result.output))
    assert type(actual) == dict, 'the --local flag (with -o -) gives a dict for output'
    hostname = next(iter(actual['local']))
    assert 'python' in actual['local'][
        hostname], 'the --local flag retrieves the installed versions of things keyed by the hostname'


# noinspection PyTypeChecker
@pytest.mark.slow_integration_test
def test_cli_local_file():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, "--local --report=false")
        assert result.exit_code == 0
        with open('report.json') as f:
            actual = json.load(f)
            assert type(actual) == dict, 'we write a dict to report.json'
            hostname = next(iter(actual['local']))
            assert 'python' in actual['local'][
                hostname], 'the --local flag retrieves the installed versions of things keyed by the hostname'


# noinspection PyTypeChecker
@pytest.mark.integration_test
def test_cli_docker():
    runner = CliRunner()
    result = runner.invoke(cli, "--docker --report=false -o '-'")
    assert result.exit_code == 0
    actual = json.loads(remove_initial_log_lines(result.output))
    assert type(actual) == dict
    # TODO - fill out docker autodiscovery


# noinspection PyTypeChecker
@pytest.mark.slow_integration_test
def test_cli_kubernetes():
    runner = CliRunner()
    result = runner.invoke(cli, "--cluster-info --kubernetes --report=false -o '-'")
    assert result.exit_code == 0
    actual = json.loads(remove_initial_log_lines(result.output))
    assert type(actual) == dict
    # TODO - fill out kube autodiscovery


def test_gather_getters_local():
    actual = gather_getters(use_local=True)
    expected = {"local": [LocalGetter()]}
    assert actual == expected


def test_gather_getters_kube_autodiscovery(mocker):
    def _kube_autodiscover():
        return [{"name": "foo", "namespace": "bar", "container": "scheduler"}]

    mocker.patch(
        'telescope.__main__.kube_autodiscover',
        _kube_autodiscover
    )

    actual = gather_getters(use_kubernetes=True)
    expected = {"kubernetes": [KubernetesGetter(**_kube_autodiscover()[0])]}
    assert actual == expected


def test_gather_getters_docker_autodiscovery(mocker: MockerFixture):
    def _docker_autodiscover():
        return [{"container_id": "foo"}]

    mocker.patch(
        'telescope.__main__.docker_autodiscover',
        _docker_autodiscover
    )

    actual = gather_getters(use_docker=True)
    expected = {"docker": [LocalDockerGetter(**_docker_autodiscover()[0])]}
    assert actual == expected


def test_parse_getters_from_hosts_file():
    actual = parse_getters_from_hosts_file(SAMPLE_HOSTS)
    expected = {
        'local': [],
        'ssh': [SSHGetter(**ssh) for ssh in SAMPLE_HOSTS['ssh']],
        'kubernetes': [KubernetesGetter(**kube) for kube in SAMPLE_HOSTS['kubernetes']],
        'docker': [LocalDockerGetter(**docker) for docker in SAMPLE_HOSTS['docker']],
    }
    assert actual == expected
