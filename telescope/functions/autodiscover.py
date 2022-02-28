from typing import Dict, List

import logging

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

log = logging.getLogger(__name__)


# noinspection PyUnresolvedReferences
def docker_autodiscover(**kwargs) -> List[Dict[str, str]]:
    if docker_client is not None:
        return [
            {"container_id": container.short_id}
            for container in docker_client.containers.list(filters={"name": "scheduler"})
        ]
    else:
        return []


def get_kubernetes_uniqueness(r: "kubernetes.clients.models.V1Pod"):
    # Attempt to get at least one (they should be ~equivalent, so both doesn't matter)
    # piece of unique identifying matter, to cover the case of "multiple airflow schedulers"
    uniqueness = ""
    try:
        # Try to get "generate_name", for: bitter-supernova-1993-scheduler-57678b77d-qh8zm
        # this should be: bitter-supernova-1993-scheduler-57678b77d-
        uniqueness += r.metadata.generate_name
    except Exception as e:
        log.debug(f"Unable to catch '.metadata.generate_name' - {e}")
    try:
        # Try to get the name of the owner reference, for:  bitter-supernova-1993-scheduler-57678b77d-qh8zm
        # this should be bitter-supernova-1993-scheduler-57678b77d
        uniqueness += r.metadata.owner_references[0].name
    except Exception as e:
        log.debug(f"Unable to catch '.metadata.owner_references[0].name' - {e}")
    return uniqueness


def kube_autodiscover(label_selector, **kwargs) -> List[Dict[str, str]]:
    """:returns List of Tuple containing - pod name, pod namespace, container name"""
    # noinspection PyUnresolvedReferences
    if kube_client is not None:
        seen_uniqueness = set()
        results = []
        # noinspection PyUnresolvedReferences
        for r in kube_client.list_pod_for_all_namespaces(label_selector=label_selector).items:
            uniqueness = get_kubernetes_uniqueness(r)

            if uniqueness:
                if uniqueness not in seen_uniqueness:
                    seen_uniqueness.add(uniqueness)
                    results.append(
                        {"name": r.metadata.name, "namespace": r.metadata.namespace, "container": "scheduler"}
                    )
            else:
                results.append({"name": r.metadata.name, "namespace": r.metadata.namespace, "container": "scheduler"})
        return results
    else:
        return []


AUTODISCOVERERS = {
    "kubernetes": {"method": kube_autodiscover, "getter": KubernetesGetter},
    "docker": {"method": docker_autodiscover, "getter": LocalDockerGetter},
}
