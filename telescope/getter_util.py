from typing import Dict

import logging
import os

import yaml

import telescope
from telescope.functions.autodiscover import AUTODISCOVERERS, docker_autodiscover, kube_autodiscover
from telescope.getters import Getter
from telescope.getters.docker import LocalDockerGetter
from telescope.getters.kubernetes import KubernetesGetter
from telescope.getters.local import LocalGetter

log = logging.getLogger(__name__)

VERSION = os.getenv("TELESCOPE_REPORT_RELEASE_VERSION", "1.1.4")
AIRFLOW_REPORT_CMD = [
    "/bin/sh",
    "-c",
    "curl -sslL "
    f"https://github.com/astronomer/telescope/releases/download/v{VERSION}/airflow_report.pyz > "
    "airflow_report.pyz && chmod +x airflow_report.pyz && "
    "PYTHONWARNINGS=ignore ./airflow_report.pyz && "
    "rm -f ./airflow_report.pyz",
]


def parse_getters_from_hosts_file(hosts: dict, label_selector: str = "") -> Dict[str, list]:
    _getters = {}
    for host_type in hosts:
        hosts_of_type = [] if hosts[host_type] is None else hosts[host_type]
        if host_type != "local":
            log.info(f"Discovered {len(hosts_of_type)} {host_type} hosts in hosts file...")
        else:
            log.info(f"Discovered {host_type} host type in hosts file...")

        getter_of_type = telescope.getters.get_for_type(host_type)
        getter_type = getter_of_type.get_type()

        has_autodiscovery = getter_type in AUTODISCOVERERS.keys()

        # If the entry is a list, or we can autodiscover (it's probably empty)
        if type(hosts_of_type) == list or has_autodiscovery:
            # If we have an "autodiscovery" as a method, and the list is empty, do it
            if len(hosts_of_type) == 0 and has_autodiscovery:
                log.info(f"Attempting autodiscovery for {host_type} hosts...")
                hosts_of_type = AUTODISCOVERERS["method"][host_type](label_selector=label_selector)
                log.info(f"Adding {len(hosts_of_type)} discovered scheduler pods/containers...")
            else:
                log.info(f"Adding {len(hosts_of_type)} defined {host_type} hosts...")

            # append to any existing hosts of type, or set the key if it's not set
            _getters[getter_type] = _getters.get(getter_type, []) + [getter_of_type(**host) for host in hosts_of_type]
        else:
            log.warning(f"Unable to understand '{host_type}'... skipping...")
    return _getters


def gather_getters(
    use_local: bool = False,
    use_docker: bool = False,
    use_kubernetes: bool = False,
    hosts_file: str = "",
    label_selector: str = "",
) -> Dict[str, list]:
    _getters = {}

    # Parse hosts file via -f (can be local, ssh, docker, kubernetes)
    if hosts_file:
        log.info(f"Parsing user supplied hosts file... {hosts_file}")
        with open(hosts_file) as hosts_f:
            parsed_host_file = yaml.safe_load(hosts_f)
            return parse_getters_from_hosts_file(parsed_host_file, label_selector)

    # or use passed-in flags and autodiscovery
    else:
        for (host_type, getter, autodiscover, should) in [
            ("kubernetes", KubernetesGetter, kube_autodiscover, use_kubernetes),
            ("docker", LocalDockerGetter, docker_autodiscover, use_docker),
        ]:
            if should:
                log.info(f"Attempting autodiscovery for {host_type} hosts...")
                _getters[host_type] = [getter(**discovery) for discovery in autodiscover(label_selector=label_selector)]
                log.info(f"Discovered {len(_getters[host_type])} {host_type} scheduler pods/containers...")

        # Add local
        if use_local:
            _getters["local"] = [LocalGetter()]

    return _getters


def get_from_getter(getter: Getter) -> dict:
    getter_key = getter.get_report_key()
    host_type = getter.get_type()
    results = {}
    key = "airflow_report"
    full_key = (host_type, getter_key, key)
    log.debug(f"Fetching 'report[{full_key}]'...")
    try:
        results[full_key] = getter.get(AIRFLOW_REPORT_CMD)
    except Exception as e:
        log.exception(e)
        results[full_key] = str(e)
    return results
