from typing import List, Union

import logging
import shlex

try:
    from shlex import join
except ImportError:

    def join(split_command):
        return " ".join(shlex.quote(arg) for arg in split_command)


import socket

from invoke import run

from astronomer_telescope.getters import Getter
from astronomer_telescope.util import clean_airflow_report_output

log = logging.getLogger(__name__)


class LocalGetter(Getter):
    def get(self, cmd: Union[List[str], str]) -> Union[dict, str]:
        """Utilize invoke to run locally
        http://docs.pyinvoke.org/en/stable/api/runners.html#invoke.runners.Runner.run
        """
        if type(cmd) == list:
            cmd = join(cmd)
        out = run(cmd, hide=True, warn=True)  # other options: timeout, warn
        if out.stdout:
            out = clean_airflow_report_output(out.stdout)
        elif out.stderr is not None:
            out = out.stderr
        else:
            raise RuntimeError("Unknown Error")
        return out

    def get_report_key(self):
        return socket.gethostname()

    def __eq__(self, other):
        return type(self) == type(other)

    @staticmethod
    def get_type():
        return "local"
