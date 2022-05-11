from typing import List, Union

import logging
import shlex
import socket

from invoke import run

from telescope.getters import Getter
from telescope.util import clean_airflow_report_output

log = logging.getLogger(__name__)


class LocalGetter(Getter):
    def get(self, cmd: Union[List[str], str]) -> Union[dict, str]:
        """Utilize invoke to run locally
        http://docs.pyinvoke.org/en/stable/api/runners.html#invoke.runners.Runner.run
        """
        if type(cmd) == list:
            cmd = shlex.join(cmd)
        out = run(cmd, hide=True, warn=True)  # other options: timeout, warn
        if out.stdout:
            out = clean_airflow_report_output(out.stdout)
        elif out.stderr is not None:
            out = out.stderr
        else:
            out = "Unknown Error"
        return out

    def get_report_key(self):
        return socket.gethostname()

    def __eq__(self, other):
        return type(self) == type(other)

    @staticmethod
    def get_type():
        return "local"
