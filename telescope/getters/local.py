from typing import List, Union

import json
import socket

from invoke import run

from telescope.getters import Getter
from telescope.util import clean_airflow_report_output


class LocalGetter(Getter):
    def get(self, cmd: Union[List[str], str]):
        """Utilize invoke to run locally
        http://docs.pyinvoke.org/en/stable/api/runners.html#invoke.runners.Runner.run
        """
        out = run(cmd, hide=True, warn=True).stdout  # other options: timeout, warn
        return json.loads(clean_airflow_report_output(out.decode("utf-8")))

    def get_report_key(self):
        return socket.gethostname()

    def __eq__(self, other):
        return type(self) == type(other)

    @staticmethod
    def get_type():
        return "local"
