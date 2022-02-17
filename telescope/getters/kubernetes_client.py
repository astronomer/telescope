import logging
from copy import deepcopy

from kubernetes import client, config
from kubernetes.client import ApiException, VersionApi
from kubernetes.stream import stream

log = logging.getLogger(__name__)

try:
    config.load_kube_config()
    kube_client = client.CoreV1Api()
    new_conf = deepcopy(kube_client.api_client.configuration)
    new_conf.api_key = {}  # was getting "unauthorized" otherwise, weird.
    api_client = VersionApi(client.ApiClient(new_conf))
except Exception as e:
    log.exception(e)
    api_client = None
    kube_client = None

stream = stream
ApiException = ApiException
