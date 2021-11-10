import logging

import docker

from telescope.getters import Getter
from telescope.util import get_json_or_clean_str


class LocalDockerGetter(Getter):
    try:
        docker_client = docker.from_env()
    except Exception as e:
        logging.exception(e)
        docker_client = None

    def __init__(self, container_id: str = None):
        self.container_id = container_id

    def get(self, cmd: str):
        _container = LocalDockerGetter.docker_client.containers.get(self.container_id)
        exec_res = _container.exec_run(cmd)
        return get_json_or_clean_str(exec_res.output.decode('utf-8'))

    def __eq__(self, other):
        return type(self) == type(other) \
               and self.container_id == other.container_id

    @staticmethod
    def get_type():
        return 'docker'

    def get_report_key(self):
        return self.container_id
