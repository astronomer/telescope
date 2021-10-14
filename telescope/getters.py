import ast
import json
import logging
from abc import abstractmethod
from copy import deepcopy
from json import JSONDecodeError
from typing import Type, Union, List, Dict
import socket
from kubernetes import client, config
from kubernetes.client import VersionApi
from kubernetes.client import ApiException
from kubernetes.stream import stream
from fabric import Connection
from invoke import run
import docker

log = logging.getLogger(__name__)


def get_json_or_clean_str(o: str) -> Union[List, Dict]:
    try:
        return json.loads(o)
    except (JSONDecodeError, TypeError) as e:
        log.debug(e)
        log.debug(o)
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

    @abstractmethod
    def get_type(self):
        pass


class KubernetesGetter(Getter):
    config.load_kube_config()  # TODO: context=context
    kube_client = client.CoreV1Api()
    new_conf = deepcopy(kube_client.api_client.configuration)
    new_conf.api_key = {}  # was getting "unauthorized" otherwise, weird.
    api_client = VersionApi(client.ApiClient(new_conf))

    def __init__(self, name: str = None, namespace: str = None, container: str = 'scheduler'):
        self.name = name
        self.namespace = namespace
        self.container = container
        self.host_type = "kubernetes"

    def autodiscover(self) -> List[Dict[str, str]]:
        """:returns List of Tuple containing - pod name, pod namespace, container name"""
        return [
            {"name": r.metadata.name, "namespace": r.metadata.namespace, "container": 'scheduler'}
            for r in self.kube_client.list_pod_for_all_namespaces(label_selector="component=scheduler").items
        ]

    def get(self, cmd: List[str]):
        """Utilize kubernetes python client to exec in a container
        https://github.com/kubernetes-client/python/blob/master/examples/pod_exec.py
        """
        try:
            pod_res = self.kube_client.read_namespaced_pod(name=self.name, namespace=self.namespace)
            if not pod_res or pod_res.status.phase == 'Pending':
                raise RuntimeError(f"Kubernetes pod {self.name} in namespace {self.namespace} does not exist or is pending...")
        except ApiException as e:
            if e.status != 404:
                raise RuntimeError(f"Unknown Kubernetes error: {e}")

        exec_res = stream(
            self.kube_client.connect_get_namespaced_pod_exec,
            name=self.name, namespace=self.namespace, command=cmd, container=self.container,
            stderr=True, stdin=False, stdout=True, tty=False
        )
        # filter out any log lines
        log.debug(exec_res)
        return ast.literal_eval(exec_res)

    def get_report_key(self):
        return f"{self.namespace}|{self.name}"

    def cluster_info(self):
        def cloud_provider(o):
            if 'gke' in o:
                return 'gke'
            elif 'eks' in o:
                return 'eks'
            elif 'az' in o:
                return 'aks'
            else:
                return None

        def parse_cpu(cpu):
            if 'm' in cpu:
                return int(cpu[:-1])/1000
            else:
                return int(cpu)

        def parse_mem(mem):
            # if 'Ki' in mem:
            return int(mem[:-2])

        res = self.api_client.get_code()
        nodes_res = self.kube_client.list_node()
        return {
            "version": res.git_version,
            "provider": cloud_provider(res.git_version),
            "allocatable_cpu": sum([parse_cpu(r.status.allocatable['cpu']) for r in nodes_res.items]),
            "allocatable_gb": int(sum([parse_mem(r.status.allocatable['memory']) for r in nodes_res.items]) / 1024 ** 2),
            "capacity_cpu": sum([parse_cpu(r.status.capacity['cpu']) for r in nodes_res.items]),
            "capacity_gb": int(sum([parse_mem(r.status.capacity['memory']) for r in nodes_res.items]) / 1024 ** 2)
        }

    def precheck(self):
        raise NotImplementedError
        #  database: rf"""kubectl run psql --rm -it --restart=Never -n {namespace} --image {image} --command -- psql {conn.out} -qtc "select 'healthy';" """
        #  certificate: ""

    def get_type(self):
        return 'kubernetes'


class SSHGetter(Getter):
    def __init__(self, host):
        self.host = host
        self.host_type = "ssh"

    def get(self, cmd: str):
        """Utilize fabric to run over SSH
        https://docs.fabfile.org/en/2.6/getting-started.html#run-commands-via-connections-and-run
        """
        return Connection(self.host).run(cmd, hide=True)

    def get_report_key(self):
        return self.host

    def get_type(self):
        return 'ssh'


class LocalDockerGetter(Getter):
    docker_client = docker.from_env()

    def __init__(self, container_id: str = None):
        self.container_id = container_id

    def autodiscover(self) -> List[Dict[str, str]]:
        return [
            {'container_id': container.short_id}
            for container in LocalDockerGetter.docker_client.containers.list(
                filters={"name": "scheduler"}
            )
        ]

    def get(self, cmd: str):
        _container = LocalDockerGetter.docker_client.containers.get(self.container_id)
        exec_res = _container.exec_run(cmd)
        return get_json_or_clean_str(exec_res.output.decode('utf-8'))

    def get_type(self):
        return 'docker'

    def get_report_key(self):
        return self.container_id


class LocalGetter(Getter):
    def get(self, cmd: str, **kwargs):
        """Utilize invoke to run locally
        http://docs.pyinvoke.org/en/stable/api/runners.html#invoke.runners.Runner.run
        """
        out = run(cmd, echo=True, hide=True, **kwargs).stdout   # other options: timeout, warn
        return get_json_or_clean_str(out)

    def get_report_key(self):
        return socket.gethostname()

    def get_type(self):
        return 'local'

    def verify(self):
        return {
            "helm": self.get('helm ls -aA -o json'),
            # "astro_config": LocalGetter.get("cat config.yaml") if os.path.exists('config.yaml') else "'config.yaml' not found"
        }
