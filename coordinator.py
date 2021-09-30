import json
import logging
from abc import abstractmethod
from datetime import datetime
from json import JSONDecodeError
from typing import List, Union, Dict

import docker
import yaml
from dotenv import load_dotenv
from fabric import Connection
from invoke import run
from kubernetes import client, config
from kubernetes.stream import stream

logging.basicConfig()
load_dotenv()


def get_json_or_clean_str(o: str) -> Union[List, Dict]:
    try:
        return json.loads(o)
    except JSONDecodeError:
        return o.strip().split('\n')


class Getter:
    @abstractmethod
    def get(self, cmd: str):
        pass


class KubernetesGetter(Getter):
    def __init__(self, context: str, name: str, namespace: str, container: str = 'scheduler'):
        config.load_kube_config()   # TODO: context=context
        self.client = client.CoreV1Api()
        self.name = name
        self.namespace = namespace
        self.container = container

    def get(self, cmd: List[str]):
        """Utilize kubernetes python client to exec in a container
        https://github.com/kubernetes-client/python/blob/master/examples/pod_exec.py
        """
        return get_json_or_clean_str(stream(
            self.client.connect_get_namespaced_pod_exec,
            name=self.name, namespace=self.namespace, command=cmd, container=self.container
        ))


class SSHGetter(Getter):
    def __init__(self, host):
        self.host = host

    def get(self, cmd: str):
        """Utilize fabric to run over SSH
        https://docs.fabfile.org/en/2.6/getting-started.html#run-commands-via-connections-and-run
        """
        return Connection(self.host).run(cmd, hide=True)


class LocalDockerGetter(Getter):
    def __init__(self, container: str):
        self.client = docker.from_env()
        self.container = container

    def get(self, cmd: str):
        return NotImplementedError


class LocalGetter(Getter):
    def get(self, cmd: str, **kwargs):
        """Utilize invoke to run locally
        http://docs.pyinvoke.org/en/stable/api/runners.html#invoke.runners.Runner.run
        """
        out = run(cmd, **kwargs).stdout
        return get_json_or_clean_str(out)


def main():
    report = {}
    with open('report.yaml') as input_f, open('hosts.yaml') as hosts_f, open('report.json', 'w') as report_f:
        inputs = yaml.safe_load(input_f)

        # Local
        local = LocalGetter()
        report['local'] = {"Report Created": str(datetime.now())}
        logging.debug("Fetching 'local' ...")
        for key, cmd in inputs['local'].items():
            logging.debug(f"Fetching '{key}'")
            try:
                report['local'][key] = local.get(cmd, echo=True, hide=True)  # other options: timeout, warn
            except Exception as e:
                logging.exception(e)

        # Hosts
        hosts = yaml.safe_load(hosts_f)
        if 'kubernetes' in hosts:
            for kube in hosts['kubernetes']:
                key = f"{kube['context']}|{kube['namespace']}|{kube['name']}"
                report[key] = {}
                KubernetesGetter(**kube).get("")

        report_f.write(json.dumps(report))


if __name__ == '__main__':
    main()
