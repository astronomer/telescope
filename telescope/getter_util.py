from typing import Any, Callable, Dict, Union

import logging
import os
from pathlib import Path
from shlex import split

import yaml

import telescope
from telescope.functions.astronomer_enterprise import get_helm_info
from telescope.functions.autodiscover import AUTODISCOVERERS, docker_autodiscover, kube_autodiscover
from telescope.getters import Getter
from telescope.getters.docker import LocalDockerGetter
from telescope.getters.kubernetes import KubernetesGetter
from telescope.getters.local import LocalGetter

log = logging.getLogger(__name__)

VERSION = os.getenv("TELESCOPE_REPORT_RELEASE_VERSION", telescope.version)
if os.getenv("TELESCOPE_AIRFLOW_REPORT_CMD"):
    AIRFLOW_REPORT_CMD = split(os.getenv("TELESCOPE_AIRFLOW_REPORT_CMD"))
else:
    AIRFLOW_REPORT_CMD = split(
        'python -W ignore -c "'
        "import runpy,os;from urllib.request import urlretrieve as u;"
        f"a='airflow_report.pyz';"
        f"u('https://github.com/astronomer/telescope/releases/download/v{VERSION}/'+a,a);"
        f'runpy.run_path(a);os.remove(a)"'
    )
    # Alternatively?? - python -c "from zipimport import zipimporter; zipimporter('/dev/stdin').load_module('__main__')"


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
            _getters = parse_getters_from_hosts_file(parsed_host_file, label_selector)

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


def obfuscate(x: str) -> str:
    """
    >>> obfuscate("Hello World!")
    'Hel***********ld!'
    >>> obfuscate("")
    '***********'
    >>> obfuscate("/a/b/c/d/hello_world.py")
    '/a/b/c/d/hel***********rld.py'
    """
    if "/" not in x:
        return f"{x[:3]}***********{x[-3:]}"
    p = Path(x)
    return x.replace(p.stem, obfuscate(p.stem))


def get_from_getter(
    getter: Getter, dag_obfuscation: bool = False, dag_obfuscation_fn: Callable[[str], str] = obfuscate
) -> dict:
    getter_key = getter.get_report_key()
    host_type = getter.get_type()
    results = {}
    full_key = (host_type, getter_key, "airflow_report")
    helm_full_key = (host_type, getter_key, "helm")
    log.debug(f"Fetching 'report[{full_key}]'...")

    # get airflow report
    try:
        result: Union[Dict[Any, Any], str] = getter.get(AIRFLOW_REPORT_CMD)

        # bubble up exception to except clause
        if type(result) == str:
            log.error(f"\n{full_key} raised an error\n")
            raise Exception(result)

        if dag_obfuscation:
            for dag in result.get("dags_report", []):
                dag["dag_id"] = dag_obfuscation_fn(dag["dag_id"])
                dag["fileloc"] = dag_obfuscation_fn(dag["fileloc"])

        results[full_key] = result
    except Exception as e:
        log.exception(e)
        results[full_key] = str(e)

    # get helm report
    try:
        if type(getter) == KubernetesGetter:
            results[helm_full_key] = get_helm_info(namespace=getter_key.split("|")[0])
    except Exception as e:
        log.warning(f"\nFailure getting helm information for {helm_full_key} - {e}\n")
        results[helm_full_key] = str(e)

    return results
