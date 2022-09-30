from typing import List, Union

import logging
import os
import shlex

try:
    from shlex import join
except ImportError:

    def join(split_command):
        return " ".join(shlex.quote(arg) for arg in split_command)


from invoke import run
from lazyimport import lazyimport
from retrying import retry

from astronomer_telescope.config import AIRGAPPED, REPORT_PACKAGE
from astronomer_telescope.getters import Getter
from astronomer_telescope.util import clean_airflow_report_output

lazyimport(
    globals(),
    """
from astronomer_telescope.getters.kubernetes_client import kube_client
from astronomer_telescope.getters.kubernetes_client import api_client
from astronomer_telescope.getters.kubernetes_client import stream
from astronomer_telescope.getters.kubernetes_client import ApiException
""",
)
log = logging.getLogger(__name__)
log.setLevel(os.getenv("LOG_LEVEL", logging.WARNING))
log.addHandler(logging.StreamHandler())


class KubernetesGetter(Getter):
    def __init__(self, name: str = None, namespace: str = None, container: str = "scheduler"):
        self.name = name
        self.namespace = namespace
        self.container = container

    @retry(wait_random_min=1000, wait_random_max=2000, stop_max_attempt_number=3)
    def get(self, cmd: Union[List[str], str]) -> Union[dict, str]:
        """Utilize kubernetes python client to exec in a container
        https://github.com/kubernetes-client/python/blob/master/examples/pod_exec.py
        """

        if AIRGAPPED:
            cp_cmd = f"kubectl cp {REPORT_PACKAGE} -n {self.namespace} {self.name}:{REPORT_PACKAGE} -c {self.container}"
            log.debug(f"Running {cmd} for airgapped {self.namespace}")
            cp_result = run(cp_cmd, hide=True, warn=True)
            log.debug(cp_result.stdout)

        if os.getenv("TELESCOPE_KUBERNETES_METHOD", "") == "kubectl":
            if type(cmd) == list:
                cmd = join(cmd)

            cmd = f"kubectl exec -it -n {self.namespace} {self.name} -c {self.container} -- {cmd}"
            log.debug(f"Running {cmd}")
            result = clean_airflow_report_output(run(cmd, hide=True, warn=True).stdout)
        else:
            # noinspection PyUnresolvedReferences
            try:
                # noinspection PyUnresolvedReferences
                pod_res = kube_client.read_namespaced_pod(name=self.name, namespace=self.namespace)
                if not pod_res or pod_res.status.phase == "Pending":
                    raise RuntimeError(
                        f"Kubernetes pod {self.name} in namespace {self.namespace} does not exist or is pending..."
                    )
            except ApiException as e:
                if e.status != 404:
                    raise RuntimeError(f"Unknown Kubernetes error: {e}") from e

            log.debug(f"Running {cmd} on pod {self.name} in namespace {self.namespace} in container {self.container}")
            # noinspection PyUnresolvedReferences
            exec_res = stream(
                # noinspection PyUnresolvedReferences
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
            result = clean_airflow_report_output(exec_res)
        return result

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
