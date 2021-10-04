import json
import logging
import os
import socket
from abc import abstractmethod
from datetime import datetime
from json import JSONDecodeError
from typing import List, Union, Dict, Type

import docker
import yaml
from dotenv import load_dotenv
from fabric import Connection
from invoke import run
from kubernetes import client, config
from kubernetes.client import ApiException
from kubernetes.stream import stream

logging.basicConfig(level=logging.INFO)
load_dotenv()


def get_json_or_clean_str(o: str) -> Union[List, Dict]:
    try:
        return json.loads(o)
    except (JSONDecodeError, TypeError):
        return o.strip().split('\n')


class Getter:
    @abstractmethod
    def get(self, cmd: str):
        pass

    @abstractmethod
    def get_report_key(self):
        pass

    @staticmethod
    def get_for_type(host_type: str) -> Type[Union['KubernetesGetter', 'LocalDockerGetter', 'LocalGetter', 'SSHGetter']]:
        if host_type == 'kubernetes':
            return KubernetesGetter
        elif host_type == 'docker':
            return LocalDockerGetter
        elif host_type == 'local':
            return LocalGetter
        elif host_type == 'ssh':
            return SSHGetter
        else:
            raise RuntimeError(f"Unknown host type: {host_type}")


class KubernetesGetter(Getter):
    def __init__(self, context: str, name: str, namespace: str, container: str = 'scheduler'):
        config.load_kube_config()   # TODO: context=context
        self.context = context
        self.client = client.CoreV1Api()
        self.name = name
        self.namespace = namespace
        self.container = container

    def get(self, cmd: List[str]):
        """Utilize kubernetes python client to exec in a container
        https://github.com/kubernetes-client/python/blob/master/examples/pod_exec.py
        """
        try:
            pod_res = self.client.read_namespaced_pod(name=self.name, namespace=self.namespace)
            if not pod_res or pod_res.status.phase == 'Pending':
                raise RuntimeError(f"Kubernetes pod {self.name} in namespace {self.namespace} does not exist or is pending...")
        except ApiException as e:
            if e.status != 404:
                raise RuntimeError(f"Unknown Kubernetes error: {e}")

        exec_res = stream(
            self.client.connect_get_namespaced_pod_exec,
            name=self.name, namespace=self.namespace, command=cmd, container=self.container, stderr=True, stdin=False, stdout=True, tty=False
        )
        return get_json_or_clean_str(exec_res)

    def get_report_key(self):
        return f"{self.context}|{self.namespace}|{self.name}"


class SSHGetter(Getter):
    def __init__(self, host):
        self.host = host

    def get(self, cmd: str):
        """Utilize fabric to run over SSH
        https://docs.fabfile.org/en/2.6/getting-started.html#run-commands-via-connections-and-run
        """
        return Connection(self.host).run(cmd, hide=True)

    def get_report_key(self):
        return self.host


class LocalDockerGetter(Getter):
    def __init__(self, container: str):
        self.client = docker.from_env()
        self.container = container

    def get(self, cmd: str):
        _container = self.client.containers.get(self.container)
        exec_res = _container.exec_run(cmd)
        return get_json_or_clean_str(exec_res.output.decode('utf-8'))

    def get_report_key(self):
        return self.container


class LocalGetter(Getter):
    def get(self, cmd: str, **kwargs):
        """Utilize invoke to run locally
        http://docs.pyinvoke.org/en/stable/api/runners.html#invoke.runners.Runner.run
        """
        out = run(cmd, **kwargs).stdout
        return get_json_or_clean_str(out)

    def get_report_key(self):
        return socket.gethostname()


def main(get_from_hosts=True, get_local=False):
    logging.info("Beginning report generation coordinator...")
    report = {}
    with open('report.yaml') as input_f, open('hosts.yaml') as hosts_f, open('report.json', 'w') as report_f:
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
                if type(hosts_of_type) == list:
                    for host in hosts_of_type:
                        getter = Getter.get_for_type(host_type)
                        report_key = getter.get_report_key()
                        logging.info(f"Fetching airflow report from {host_type} host {report_key} ...")
                        report[report_key] = getter(**host).get(inputs['airflow']['report'])
        report_f.write(json.dumps(report, default=str))


if __name__ == '__main__':
    main()
