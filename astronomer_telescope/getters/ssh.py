from typing import List, Union

import shlex

try:
    from shlex import join
except ImportError:

    def join(split_command):
        return " ".join(shlex.quote(arg) for arg in split_command)


from fabric import Connection

from astronomer_telescope.getters import Getter
from astronomer_telescope.util import clean_airflow_report_output


class SSHGetter(Getter):
    def __init__(self, host: str, **kwargs):
        self.host = host
        self.kwargs = kwargs

    def get(self, cmd: Union[List[str], str]):
        """Utilize fabric to run over SSH
        https://docs.fabfile.org/en/2.6/getting-started.html#run-commands-via-connections-and-run
        """
        out = Connection(self.host, **self.kwargs).run(join(cmd), hide=True)
        if out.stdout:
            out = clean_airflow_report_output(out.stdout)
        elif out.stderr is not None:
            out = out.stderr
        else:
            raise RuntimeError("Unknown Error")
        return out

    def __eq__(self, other):
        return type(self) == type(other) and self.host == other.host

    def get_report_key(self):
        return self.host

    @staticmethod
    def get_type():
        return "ssh"
