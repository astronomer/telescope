import json
import logging
from functools import partial
from multiprocessing import Pool
from typing import Dict

import click as click
import yaml
from click import Path
from tqdm.contrib.concurrent import process_map

from telescope.getters import LocalDockerGetter, KubernetesGetter, LocalGetter, Getter

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

HOSTS_JSON_SCHEMA = "../hosts.schema.json"  # Schema for the 'hosts.yaml' file
CONFIG_FILE = 'config.yaml'  # Configuration file that specifies which things to run when


def parse_getters_from_hosts_file(hosts: dict) -> Dict[str, list]:
    _getters = {}
    for host_type in hosts:
        hosts_of_type = [] if hosts[host_type] is None else hosts[host_type]
        logging.info(f"Discovered {len(hosts_of_type)} {host_type} hosts in hosts file...")
        getter_type = Getter.get_for_type(host_type)

        # If the Getter has "autodiscovery" as a method, and the list is empty, do it
        maybe_autodiscover = getattr(getter_type, 'autodiscover', None)
        if type(hosts_of_type) == list or maybe_autodiscover:
            if len(hosts_of_type) == 0 and maybe_autodiscover:
                logging.info(f"Attempting autodiscovery for {host_type} hosts...")
                hosts_of_type = maybe_autodiscover()
                logging.info(f"Adding {len(hosts_of_type)} discovered scheduler pods/containers...")
            else:
                logging.info(f"Adding {len(hosts_of_type)} defined {host_type} hosts...")
            _getters[getter_type.get_type()] = _getters.get(getter_type.get_type(), []) + [getter_type(**host) for host in hosts_of_type]
        else:
            logging.warning(f"Unable to understand '{host_type}'... skipping...")
    return _getters


def gather_getters(use_local, use_docker, use_kubernetes, hosts_file) -> Dict[str, list]:
    getters = {}

    # Parse hosts file via -f (can be local, ssh, docker, kubernetes)
    if hosts_file:
        logging.info(f"Parsing user supplied hosts file... {hosts_file}")
        with open(hosts_file) as hosts_f:
            # TODO - JSON SCHEMA VALIDATION
            parsed_host_file = yaml.safe_load(hosts_f)
            return parse_getters_from_hosts_file(parsed_host_file)

    # or use passed-in flags and autodiscovery
    else:
        # Add docker via autodiscovery
        for (host_type, getter, should) in [
            ('kubernetes', KubernetesGetter, use_kubernetes),
            ('docker', LocalDockerGetter, use_docker)
        ]:
            if should:
                logging.info(f"Attempting autodiscovery for {host_type} hosts...")
                getters[host_type] = [getter(**discovery) for discovery in getter.autodiscover()]
                logging.info(f"Discovered {len(getters[host_type])} {host_type} scheduler pods/containers...")

        # Add local
        if use_local:
            getters['local'] = [LocalGetter()]

    return getters


def get_from_getter(getter: Getter, config_inputs: dict):
    getter_key = getter.get_report_key()
    host_type = getter.get_type()
    for key in config_inputs[host_type]:
        full_key = (host_type, getter_key, key)
        logging.debug(f"Fetching 'report[{full_key}]'...")
        try:
            return full_key, getter.get(config_inputs[host_type][key])
        except Exception as e:
            logging.exception(e)
            return full_key, str(e)

# TODO
# @click.option('-n', '--namespace', type=str, help="Only for Kubernetes - limit autodiscovery to a specific namespace")
# @click.option('--kube-config', type=str)
# @click.option('--precheck', is_flag=True)


d = {"show_default": True, "show_envvar": True}
fd = {"show_default": True, "show_envvar": True, "is_flag": True}


@click.command()
@click.option('--local', 'use_local', default=True, **fd,
              help="checks versions of locally installed tools")
@click.option('--docker', 'use_docker', **fd,
              help="autodiscovery and airflow reporting for local docker")
@click.option('--kubernetes', 'use_kubernetes', **fd,
              help="autodiscovery and airflow reporting for kubernetes")
@click.option('--cluster-info', **fd,
              help="get cluster size and allocation in kubernetes")
@click.option('--verify', **fd,
              help="adds helm installations to report")
@click.option('-f', '--hosts-file', **d, default=None, type=Path(exists=True),
              help="Hosts file to pass in various types of hosts (ssh, kubernetes, docker) - See README.md for sample")
@click.option('-o', '--output-file', **d, type=Path(exists=True), default='report.json',
              help="Output file to write report json, can be '-' for stdout")
@click.option('-p', '--parallelism', show_default='Number CPU', type=int, default=None,
              help="How many cores to use for multiprocessing")
def cli(use_local: bool, use_docker: bool, use_kubernetes: bool,
        verify: bool, cluster_info: bool,
        hosts_file: str, output_file: str, parallelism: int):
    """Telescope - A tool to observe distant (or local!) Airflow installations, and gather metadata or other required data,"""
    with open(CONFIG_FILE) as input_f, click.open_file(output_file, 'w') as output:
        report = {}
        logging.info(f"Generating report to {output_file} ...")
        config_inputs = yaml.safe_load(input_f)

        # Add special method calls, don't know a better way to do this
        if cluster_info:
            report['kubernetes_cluster_info'] = KubernetesGetter.cluster_info()

        # if precheck:  # TODO
        #     report['precheck'] = KubernetesGetter.precheck()

        if verify:
            report['verify'] = LocalGetter.verify()

        with Pool(parallelism) as p:
            # flatten getters - for multiproc
            all_getters = [
                getter
                for (_, getters) in gather_getters(use_local, use_docker, use_kubernetes, hosts_file).items()
                for getter in getters
            ]

            # get evverrryttthinngggg all at once
            results = process_map(partial(get_from_getter, config_inputs=config_inputs), all_getters)

            # unflatten and assemble into report
            for (host_type, getter_key, key), value in results:
                if host_type not in report:
                    report[host_type] = {}

                if getter_key not in report[host_type]:
                    report[host_type][getter_key] = {}

                report[host_type][getter_key][key] = value

        logging.info(f"Writing report to {output_file} ...")
        output.write(json.dumps(report, default=str))


if __name__ == '__main__':
    cli(auto_envvar_prefix='TELESCOPE')