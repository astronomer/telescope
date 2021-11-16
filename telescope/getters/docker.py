import logging

from docker.errors import DockerException

import docker
from telescope.getters import Getter
from telescope.util import clean_airflow_report_output

log = logging.getLogger(__name__)


class LocalDockerGetter(Getter):
    try:
        docker_client = docker.from_env()
    except DockerException as e:
        log.warning("Unable to initialize docker!")
        docker_client = None

    def __init__(self, container_id: str = None):
        self.container_id = container_id

    def get(self, cmd: str):
        _container = LocalDockerGetter.docker_client.containers.get(self.container_id)
        exec_res = _container.exec_run(cmd)
        return clean_airflow_report_output(exec_res.output.decode("utf-8"))

    def __eq__(self, other):
        return type(self) == type(other) and self.container_id == other.container_id

    @staticmethod
    def get_type():
        return "docker"

    def get_report_key(self):
        return self.container_id
