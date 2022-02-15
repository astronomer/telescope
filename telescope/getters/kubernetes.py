from typing import List, Union

import json
import logging

from lazyimport import lazyimport

from telescope.getters import Getter
from telescope.util import clean_airflow_report_output

lazyimport(
    globals(),
    """
from telescope.getters.kubernetes_client import kube_client
from telescope.getters.kubernetes_client import api_client
from telescope.getters.kubernetes_client import stream
from telescope.getters.kubernetes_client import ApiExcepton
""",
)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


# noinspection PyUnresolvedReferences
class KubernetesGetter(Getter):
    def __init__(self, name: str = None, namespace: str = None, container: str = "scheduler"):
        self.name = name
        self.namespace = namespace
        self.container = container

    def get(self, cmd: Union[List[str], str]):
        """Utilize kubernetes python client to exec in a container
        https://github.com/kubernetes-client/python/blob/master/examples/pod_exec.py
        """
        try:
            pod_res = kube_client.read_namespaced_pod(name=self.name, namespace=self.namespace)
            if not pod_res or pod_res.status.phase == "Pending":
                raise RuntimeError(
                    f"Kubernetes pod {self.name} in namespace {self.namespace} does not exist or is pending..."
                )
        except ApiException as e:
            if e.status != 404:
                raise RuntimeError(f"Unknown Kubernetes error: {e}")

        log.debug(f"Running {cmd} on pod {self.name} in namespace {self.namespace} in container {self.container}")
        exec_res = stream(
            kube_client.connect_get_namespaced_pod_exec,
            name=self.name,
            namespace=self.namespace,
            command=cmd,
            container=self.container,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
        )
        log.debug(f"Got output: {exec_res}")

        # filter out any log lines
        try:
            exec_res = clean_airflow_report_output(exec_res)
            if type(exec_res) == list:
                # clean_airflow_report falls back to trimming and splitting strings - we probably got an error message
                raise RuntimeError(" ".join(exec_res))
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
