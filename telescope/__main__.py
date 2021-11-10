from importlib.resources import path
import json
import logging
from functools import partial
from typing import Dict, Any, List

import click as click
import yaml
from click import Path, Choice
from tqdm.contrib.concurrent import process_map
from loguru import logger

import telescope
import telescope.getters
import telescope.util
from telescope.functions.astronomer_enterprise import precheck, verify
from telescope.functions.cluster_info import cluster_info
from telescope.getters import Getter
from telescope.getters.docker import LocalDockerGetter
from telescope.getters.local import LocalGetter
from telescope.getters.kubernetes import KubernetesGetter
from telescope.functions.autodiscover import docker_autodiscover, kube_autodiscover, AUTODISCOVERERS

with path(telescope, "config.yaml") as p:
    CONFIG_FILE = p.resolve()


def parse_getters_from_hosts_file(hosts: dict) -> Dict[str, list]:
    _getters = {}
    for host_type in hosts:
        hosts_of_type = [] if hosts[host_type] is None else hosts[host_type]
        if host_type != 'local':
            logger.info(f"Discovered {len(hosts_of_type)} {host_type} hosts in hosts file...")
        else:
            logger.info(f"Discovered {host_type} host type in hosts file...")

        getter_of_type = telescope.getters.get_for_type(host_type)
        getter_type = getter_of_type.get_type()

        has_autodiscovery = getter_type in AUTODISCOVERERS.keys()

        # If the entry is a list, or we can autodiscover (it's probably empty)
        if type(hosts_of_type) == list or has_autodiscovery:
            # If we have an "autodiscovery" as a method, and the list is empty, do it
            if len(hosts_of_type) == 0 and has_autodiscovery:
                logging.info(f"Attempting autodiscovery for {host_type} hosts...")
                hosts_of_type = AUTODISCOVERERS['method'][host_type]()
                logging.info(f"Adding {len(hosts_of_type)} discovered scheduler pods/containers...")
            else:
                logging.info(f"Adding {len(hosts_of_type)} defined {host_type} hosts...")

            # append to any existing hosts of type, or set the key if it's not set
            _getters[getter_type] = _getters.get(getter_type, []) + [getter_of_type(**host) for host in hosts_of_type]
        else:
            logging.warning(f"Unable to understand '{host_type}'... skipping...")
    return _getters


def gather_getters(use_local: bool = False, use_docker: bool = False, use_kubernetes : bool = False, hosts_file: str = "") -> Dict[str, list]:
    _getters = {}

    # Parse hosts file via -f (can be local, ssh, docker, kubernetes)
    if hosts_file:
        logging.info(f"Parsing user supplied hosts file... {hosts_file}")
        with open(hosts_file) as hosts_f:
            parsed_host_file = yaml.safe_load(hosts_f)
            return parse_getters_from_hosts_file(parsed_host_file)

    # or use passed-in flags and autodiscovery
    else:
        for (host_type, getter, autodiscover, should) in [
            ('kubernetes', KubernetesGetter, kube_autodiscover, use_kubernetes),
            ('docker', LocalDockerGetter, docker_autodiscover, use_docker)
        ]:
            if should:
                logging.info(f"Attempting autodiscovery for {host_type} hosts...")
                _getters[host_type] = [getter(**discovery) for discovery in autodiscover()]
                logging.info(f"Discovered {len(_getters[host_type])} {host_type} scheduler pods/containers...")

        # Add local
        if use_local:
            _getters['local'] = [LocalGetter()]

    return _getters


def get_from_getter(getter: Getter, config_inputs: dict) -> dict:
    getter_key = getter.get_report_key()
    host_type = getter.get_type()
    results = {}
    for key in config_inputs[host_type]:
        full_key = (host_type, getter_key, key)
        logging.debug(f"Fetching 'report[{full_key}]'...")
        try:
            results[full_key] = getter.get(config_inputs[host_type][key])
        except Exception as e:
            logging.exception(e)
            results[full_key] = str(e)
    return results

# TODO
# @click.option('-n', '--namespace', type=str, help="Only for Kubernetes - limit autodiscovery to a specific namespace")
# @click.option('--kube-config', type=str)


d = {"show_default": True, "show_envvar": True}
fd = {"show_default": True, "show_envvar": True, "is_flag": True}


@click.command()
@click.version_option()
@click.option('--local', 'use_local', **fd,
              help="checks versions of locally installed tools")
@click.option('--docker', 'use_docker', **fd,
              help="autodiscovery and airflow reporting for local docker")
@click.option('--kubernetes', 'use_kubernetes', **fd,
              help="autodiscovery and airflow reporting for kubernetes")
@click.option('--cluster-info', 'should_cluster_info', **fd,
              help="get cluster size and allocation in kubernetes")
@click.option('--verify', 'should_verify', **fd,
              help="adds helm installations to report")
@click.option('--precheck', 'should_precheck', **fd,
              help="runs Astronomer Enterprise pre-install sanity-checks in the report")
@click.option('-f', '--hosts-file', **d, default=None, type=Path(exists=True, readable=True),
              help="Hosts file to pass in various types of hosts (ssh, kubernetes, docker) - See README.md for sample")
@click.option('-o', '--output-file', **d, type=Path(), default='report.json',
              help="Output file to write report json, can be '-' for stdout")
@click.option('-p', '--parallelism', show_default='Number CPU', type=int, default=None,
              help="How many cores to use for multiprocessing")
@click.option('--gather', 'should_gather', **fd, default=True,
              help="gather data about Airflow environments")
@click.option('--report', 'should_report', **fd, default=True,
              help="generate report summary of gathered data")
@click.option('--report-type', type=Choice(['xlsx', 'html', 'md']), default='xlsx',
              help="What report type to generate")
def cli(use_local: bool, use_docker: bool, use_kubernetes: bool,
        should_verify: bool, should_precheck: bool, should_cluster_info: bool,
        hosts_file: str, output_file: str, parallelism: int,
        should_gather: bool, should_report: bool, report_type: str):
    """Telescope - A tool to observe distant (or local!) Airflow installations, and gather usage metadata"""
    with open(CONFIG_FILE) as input_f, click.open_file(output_file, 'w') as output:
        report = {}

        if should_gather:
            logging.info(f"Gathering data and saving to {output_file} ...")
            config_inputs = yaml.safe_load(input_f)

            # Add special method calls, don't know a better way to do this
            if should_cluster_info:
                report['cluster_info'] = cluster_info(KubernetesGetter())

            if should_precheck:
                report['precheck'] = precheck(KubernetesGetter())

            if should_verify:
                report['verify'] = verify(LocalGetter())

            # flatten getters - for multiproc
            all_getters = [
                getter
                for (_, getters) in gather_getters(use_local, use_docker, use_kubernetes, hosts_file).items()
                for getter in getters
            ]

            # get evverrryttthinngggg all at once
            results: List[Dict[Any, Any]] = process_map(partial(get_from_getter, config_inputs=config_inputs), all_getters, max_workers=parallelism)

            # unflatten and assemble into report
            for result in results:
                for (host_type, getter_key, key), value in result.items():
                    if host_type not in report:
                        report[host_type] = {}

                    if getter_key not in report[host_type]:
                        report[host_type][getter_key] = {}

                    report[host_type][getter_key][key] = value

            logging.info(f"Writing report to {output_file} ...")
            output.write(json.dumps(report, default=str))

        if should_report:
            # TODO
            pass


if __name__ == '__main__':
    cli(auto_envvar_prefix='TELESCOPE')
