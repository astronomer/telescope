from typing import List, Dict

from telescope.getters.docker import LocalDockerGetter
from telescope.getters.kubernetes import KubernetesGetter


def docker_autodiscover() -> List[Dict[str, str]]:
    return [
        {'container_id': container.short_id}
        for container in LocalDockerGetter.docker_client.containers.list(
            filters={"name": "scheduler"}
        )
    ]


def kube_autodiscover() -> List[Dict[str, str]]:
    """:returns List of Tuple containing - pod name, pod namespace, container name"""
    return [
        {"name": r.metadata.name, "namespace": r.metadata.namespace, "container": 'scheduler'}
        for r in KubernetesGetter.kube_client.list_pod_for_all_namespaces(label_selector="component=scheduler").items
    ]


AUTODISCOVERERS = {
    'kubernetes': {"method": kube_autodiscover, "getter": KubernetesGetter},
    'docker': {"method": docker_autodiscover, "getter": LocalDockerGetter}
}
