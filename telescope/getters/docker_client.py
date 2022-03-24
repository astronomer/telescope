import logging

import docker
from docker.errors import DockerException

log = logging.getLogger(__name__)

try:
    docker_client = docker.from_env()
except DockerException as e:
    log.exception(e)
    docker_client = None
