import logging

import docker

log = logging.getLogger(__name__)

try:
    docker_client = docker.from_env()
except docker.errors.DockerException as e:
    log.exception(e)
    docker_client = None
