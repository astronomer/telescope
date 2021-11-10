import json
import logging
from copy import deepcopy

from kubernetes import client, config
from kubernetes.client import ApiException, VersionApi
from kubernetes.stream import stream

from telescope.getters import Getter
from telescope.util import clean_airflow_report_output

log = logging.getLogger(__name__)


class KubernetesGetter(Getter):
    try:
        config.load_kube_config()  # TODO: context=context
        kube_client = client.CoreV1Api()
        new_conf = deepcopy(kube_client.api_client.configuration)
        new_conf.api_key = {}  # was getting "unauthorized" otherwise, weird.
        api_client = VersionApi(client.ApiClient(new_conf))
    except Exception as e:
        log.exception(e)
        kube_client = None
        api_client = None

    def __init__(self, name: str = None, namespace: str = None, container: str = "scheduler"):
        self.name = name
        self.namespace = namespace
        self.container = container

    def get(self, cmd: str):
        """Utilize kubernetes python client to exec in a container
        https://github.com/kubernetes-client/python/blob/master/examples/pod_exec.py
        """
        try:
            pod_res = self.kube_client.read_namespaced_pod(name=self.name, namespace=self.namespace)
            if not pod_res or pod_res.status.phase == "Pending":
                raise RuntimeError(
                    f"Kubernetes pod {self.name} in namespace {self.namespace} does not exist or is pending..."
                )
        except ApiException as e:
            if e.status != 404:
                raise RuntimeError(f"Unknown Kubernetes error: {e}")

        exec_res = stream(
            self.kube_client.connect_get_namespaced_pod_exec,
            name=self.name,
            namespace=self.namespace,
            command=cmd,
            container=self.container,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
        )
        # filter out any log lines
        try:
            exec_res = clean_airflow_report_output(exec_res)
            return json.loads(exec_res)
        except Exception as e:
            log.exception(e)
            log.exception(exec_res)

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and self.name == other.name
            and self.namespace == other.namespace
            and self.container == other.container
        )

    def get_report_key(self):
        return f"{self.namespace}|{self.name}"

    @staticmethod
    def get_type():
        return "kubernetes"
