import json
import logging
from datetime import datetime

import click as click
import yaml

from telescope.getters import Getter, LocalDockerGetter, LocalGetter, KubernetesGetter
from telescope.util import get_and_validate_hosts_input

logging.basicConfig(level=logging.INFO)

HOSTS_JSON_SCHEMA = "../hosts.schema.json"  # Schema for the 'hosts.yaml' file
CONFIG_FILE = 'config.yaml'  # Configuration file that specifies which things to run when


def main(get_from_hosts=True, get_local=False):
    report = {}
    with open('config.yaml') as input_f, open('hosts.yaml') as hosts_f, open('report.json', 'w') as report_f:
        inputs = yaml.safe_load(input_f)

        if get_local:
            local = LocalGetter()
            report['local'] = {"Report Created": str(datetime.now())}
            logging.debug("Fetching 'local' ...")
            for key, cmd in inputs['local'].items():
                logging.debug(f"Fetching '{key}'")
                try:
                    report['local'][key] = local.get(cmd, echo=True, hide=True)  # other options: timeout, warn
                except Exception as e:
                    logging.exception(e)

        if get_from_hosts:
            hosts = yaml.safe_load(hosts_f)
            for host_type in hosts:
                hosts_of_type = [] if hosts[host_type] is None else hosts[host_type]
                logging.debug(f"Connecting to {len(hosts_of_type)} {host_type} hosts...")
                getter_type = Getter.get_for_type(host_type)
                maybe_autodiscover = getattr(getter_type, 'autodiscover', None)
                if type(hosts_of_type) == list or maybe_autodiscover:
                    if len(hosts_of_type) == 0 and maybe_autodiscover:
                        hosts_of_type = maybe_autodiscover()

                    for host in hosts_of_type:
                        getter = getter_type(**host)
                        report_key = getter.get_report_key()
                        logging.info(f"Fetching airflow report from {host_type} host {report_key} ...")
                        try:
                            report[report_key] = getter.get(inputs['airflow']['report'])
                        except Exception as e:
                            report[report_key] = str(e)
        report_f.write(json.dumps(report, default=str))


@click.command()
@click.option('--local', 'use_local', is_flag=True)
@click.option('--docker', 'use_docker', is_flag=True)
@click.option('--kubernetes', 'use_kubernetes', is_flag=True)
@click.option('--precheck', is_flag=True)
@click.option('--verify', is_flag=True)
@click.option('--kube-config', type=str)
@click.option('-n', '--namespace', type=str, help="Only for Kubernetes - limit autodiscovery to a specific namespace")
@click.option('-f', '--hosts-file', default=None, help="Hosts file to pass in various types of hosts (ssh, kubernetes, docker)")
@click.option('-o', '--output-file', default='-', help="Output file to write json to, can be '-' for stdout")
def cli(use_local: bool, use_docker: bool, use_kubernetes: bool,
        precheck: bool, verify: bool, kube_config, hosts_file: str,
        output_file: str):

    with open(CONFIG_FILE) as input_f, click.open_file(output_file, 'w') as output:
        config_inputs = yaml.safe_load(input_f)

        # determine hosts and types, via cmd args and hosts file
        getters = []

        # Parse hosts file
        if hosts_file:
            logging.info(f"Parsing user supplied hosts file... {hosts_file}")
            hosts = get_and_validate_hosts_input(hosts_file)
            for host_type in hosts:
                hosts_of_type = [] if hosts[host_type] is None else hosts[host_type]
                logging.info(f"Discovered {len(hosts_of_type)} {host_type} hosts in hosts file {hosts_file}...")
                getter_type = Getter.get_for_type(host_type)
                maybe_autodiscover = getattr(getter_type, 'autodiscover', None)
                if type(hosts_of_type) == list or maybe_autodiscover:
                    if len(hosts_of_type) == 0 and maybe_autodiscover:
                        hosts_of_type = maybe_autodiscover()

                    getters += [getter_type(**host) for host in hosts_of_type]
        else:
            # Add docker or kube via autodiscovery
            if use_docker:
                docker_getters = [LocalDockerGetter(**discovery) for discovery in LocalDockerGetter.autodiscover()]
                logging.info(f"Discovered {len(docker_getters)} docker scheduler containers...")
                getters += docker_getters

            if use_kubernetes:
                kube_getters = [KubernetesGetter(**discovery) for discovery in KubernetesGetter.autodiscover()]
                logging.info(f"Discovered {len(kube_getters)} kubernetes scheduler pods...")
                getters += kube_getters

            # Add local
            if use_local:
                getters += [LocalGetter()]

        # iterate over hosts and types via config inputs
        for getter in getters:
            pass


if __name__ == '__main__':
    cli(auto_envvar_prefix='TELESCOPE')