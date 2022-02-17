from typing import Dict, List

from lazyimport import lazyimport

from telescope.getters.docker import LocalDockerGetter
from telescope.getters.kubernetes import KubernetesGetter

lazyimport(
    globals(),
    """
from telescope.getters.docker_client import docker_client
from telescope.getters.kubernetes_client import kube_client
from telescope.getters.kubernetes_client import api_client
""",
)


# noinspection PyUnresolvedReferences
def docker_autodiscover(**kwargs) -> List[Dict[str, str]]:
    if docker_client is not None:
        return [
            {"container_id": container.short_id}
            for container in docker_client.containers.list(filters={"name": "scheduler"})
        ]
    else:
        return []


# noinspection PyUnresolvedReferences
def kube_autodiscover(label_selector, **kwargs) -> List[Dict[str, str]]:
    """:returns List of Tuple containing - pod name, pod namespace, container name"""
    if kube_client is not None:
        return [
            {"name": r.metadata.name, "namespace": r.metadata.namespace, "container": "scheduler"}
            for r in kube_client.list_pod_for_all_namespaces(label_selector=label_selector).items
        ]
    else:
        return []


AUTODISCOVERERS = {
    "kubernetes": {"method": kube_autodiscover, "getter": KubernetesGetter},
    "docker": {"method": docker_autodiscover, "getter": LocalDockerGetter},
}
