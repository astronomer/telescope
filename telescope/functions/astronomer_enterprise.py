from typing import Optional

import base64
import gzip
import json
import logging

from invoke import run
from lazyimport import lazyimport

from telescope.util import deep_clean, get_json_or_clean_str

lazyimport(
    globals(),
    """
from telescope.getters.kubernetes_client import kube_client
from telescope.getters.kubernetes_client import api_client
from telescope.getters.kubernetes_client import stream
from kubernetes.client import ApiException
""",
)

log = logging.getLogger(__name__)


def get_helm_info(namespace: Optional[str] = None):
    output = {}

    if not namespace:
        # noinspection PyUnresolvedReferences
        secrets = kube_client.list_secret_for_all_namespaces(field_selector="type=helm.sh/release.v1").items
    else:
        # noinspection PyUnresolvedReferences
        secrets = kube_client.list_namespaced_secret(
            namespace=namespace, field_selector="type=helm.sh/release.v1"
        ).items

    for secret in secrets:
        try:
            namespace = secret.metadata.namespace
            helm_contents = json.loads(
                gzip.decompress(  # gunzip
                    base64.b64decode(base64.b64decode(secret.data["release"]))  # helm b64  # kube secret b64
                ).decode()
            )
            # filter to only astronomer/airflow helm charts and only the most recent version
            if helm_contents["info"]["status"] == "deployed" or any(
                [word in helm_contents["chart"]["metadata"]["name"] for word in ["astronomer", "airflow"]]
            ):
                try:
                    for v in [
                        ["data", "metadataConnection", "pass"],
                        ["data", "resultBackendConnection", "pass"],
                        ["data", "resultBackendConnection", "password"],
                        ["elasticsearch", "connection", "pass"],
                        ["fernetKey"],
                        ["registry", "connection", "pass"],
                        ["webserver", "defaultUser", "password"],
                    ]:
                        deep_clean(v, helm_contents["chart"]["values"])
                except Exception as e:
                    log.exception(e)
                output[namespace] = {
                    "first_deployed": helm_contents["info"]["first_deployed"],
                    "last_deployed": helm_contents["info"]["last_deployed"],
                    "chart_metadata": helm_contents["chart"]["metadata"],
                    "chart_values": helm_contents["chart"]["values"],
                }
        except Exception as e:
            log.debug(e)
    return output
