from typing import List, Union

import shlex

from fabric import Connection

from telescope.getters import Getter


class SSHGetter(Getter):
    def __init__(self, host):
        self.host = host

    def get(self, cmd: Union[List[str], str]):
        """Utilize fabric to run over SSH
        https://docs.fabfile.org/en/2.6/getting-started.html#run-commands-via-connections-and-run
        """
        return Connection(
            self.host,
        ).run(shlex.join(cmd), hide=True)

    def __eq__(self, other):
        return type(self) == type(other) and self.host == other.host

    def get_report_key(self):
        return self.host

    @staticmethod
    def get_type():
        return "ssh"
