from typing import List, Union

import json
import logging

from lazyimport import lazyimport

from telescope.getters import Getter
from telescope.util import clean_airflow_report_output

lazyimport(
    globals(),
    """
from telescope.getters.docker_client import docker_client
""",
)

log = logging.getLogger(__name__)


# noinspection PyUnresolvedReferences
class LocalDockerGetter(Getter):
    def __init__(self, container_id: str = None):
        self.container_id = container_id

    def get(self, cmd: Union[List[str], str]):
        _container = docker_client.containers.get(self.container_id)
        exec_res = _container.exec_run(cmd)
        try:
            if type(exec_res) == list:
                raise RuntimeError(" ".join(exec_res))
            return json.loads(clean_airflow_report_output(exec_res.output.decode("utf-8")))
        except Exception as e:
            log.exception(e)
            log.exception(exec_res)

    def __eq__(self, other):
        return type(self) == type(other) and self.container_id == other.container_id

    @staticmethod
    def get_type():
        return "docker"

    def get_report_key(self):
        return self.container_id
