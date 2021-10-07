import ast
from abc import abstractmethod
from copy import deepcopy
from typing import Type, Union, List, Dict, Tuple

from telescope.util import get_json_or_clean_str


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
    from kubernetes import client, config

    config.load_kube_config()  # TODO: context=context
    kube_client = client.CoreV1Api()

    def __init__(self, name: str, namespace: str, container: str = 'scheduler'):
        self.name = name
        self.namespace = namespace
        self.container = container
        self.host_type = "kubernetes"

    @classmethod
    def autodiscover(cls) -> List[Dict[str, str]]:
        """:returns List of Tuple containing - pod name, pod namespace, container name"""
        return [
            {"name": r.metadata.name, "namespace": r.metadata.namespace, "container": 'scheduler'}
            for r in KubernetesGetter.kube_client.list_pod_for_all_namespaces(label_selector="component=scheduler").items
        ]

    def get(self, cmd: List[str]):
        from kubernetes.client import ApiException
        from kubernetes.stream import stream
        """Utilize kubernetes python client to exec in a container
        https://github.com/kubernetes-client/python/blob/master/examples/pod_exec.py
        """
        try:
            pod_res = KubernetesGetter.kube_client.read_namespaced_pod(name=self.name, namespace=self.namespace)
            if not pod_res or pod_res.status.phase == 'Pending':
                raise RuntimeError(f"Kubernetes pod {self.name} in namespace {self.namespace} does not exist or is pending...")
        except ApiException as e:
            if e.status != 404:
                raise RuntimeError(f"Unknown Kubernetes error: {e}")

        exec_res = stream(
            KubernetesGetter.kube_client.connect_get_namespaced_pod_exec,
            name=self.name, namespace=self.namespace, command=cmd, container=self.container,
            stderr=True, stdin=False, stdout=True, tty=False
        )
        # filter out any log lines
        return ast.literal_eval(exec_res)

    def get_report_key(self):
        return f"{self.namespace}|{self.name}"

    @classmethod
    def get_cluster_capacity(cls) -> Tuple[int, int]:
        """:return Tuple of vCPU capacity and GB Memory capacity across the cluster"""
        res = KubernetesGetter.kube_client.list_node()
        return (
            sum([int(r.status.capacity['cpu']) for r in res.items]),  # vcpu
            int(sum([int(r.status.capacity['memory'][:-2]) for r in res.items]) / 1024 ** 2)  # gb
        )

    @classmethod
    def get_cluster_allocated(cls) -> Tuple[int, int]:
        """:return Tuple of vCPU capacity and GB Memory capacity across the cluster"""
        res = KubernetesGetter.kube_client.list_node()
        return (
            sum([int(r.status.allocated['cpu']) for r in res.items]),  # vcpu
            int(sum([int(r.status.allocated['memory'][:-2]) for r in res.items]) / 1024 ** 2)  # gb
        )

    @classmethod
    def get_version_and_provider(cls):
        from kubernetes import client
        from kubernetes.client import VersionApi

        def cloud_provider(o):
            if 'gke' in o:
                return 'gke'
            elif 'eks' in o:
                return 'eks'
            elif 'az' in o:
                return 'aks'
            else:
                return None

        new_conf = deepcopy(KubernetesGetter.kube_client.api_client.configuration)
        new_conf.api_key = {}  # was getting "unauthorized" otherwise, weird.
        res = VersionApi(client.ApiClient(new_conf)).get_code()
        return res.git_version, cloud_provider(res.git_version)

    def preinstall(self):
        raise NotImplementedError
        #  database: rf"""kubectl run psql --rm -it --restart=Never -n {namespace} --image {image} --command -- psql {conn.out} -qtc "select 'healthy';" """
        #  certificate: ""


class SSHGetter(Getter):
    def __init__(self, host):
        self.host = host
        self.host_type = "ssh"

    def get(self, cmd: str):
        from fabric import Connection
        """Utilize fabric to run over SSH
        https://docs.fabfile.org/en/2.6/getting-started.html#run-commands-via-connections-and-run
        """
        return Connection(self.host).run(cmd, hide=True)

    def get_report_key(self):
        return self.host


class LocalDockerGetter(Getter):
    import docker
    docker_client = docker.from_env()

    def __init__(self, container_id: str):
        self.container_id = container_id

    @classmethod
    def autodiscover(cls) -> List[Dict[str, str]]:
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

    def get_report_key(self):
        return self.container_id


class LocalGetter(Getter):
    def get(self, cmd: str, **kwargs):
        from invoke import run
        """Utilize invoke to run locally
        http://docs.pyinvoke.org/en/stable/api/runners.html#invoke.runners.Runner.run
        """
        out = run(cmd, **kwargs).stdout
        return get_json_or_clean_str(out)

    def get_report_key(self):
        import socket
        return socket.gethostname()

    def verify(self):
        return NotImplementedError