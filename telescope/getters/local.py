import socket

from invoke import run

from telescope.getters import Getter
from telescope.util import get_json_or_clean_str


class LocalGetter(Getter):
    def get(self, cmd: str, **kwargs):
        """Utilize invoke to run locally
        http://docs.pyinvoke.org/en/stable/api/runners.html#invoke.runners.Runner.run
        """
        out = run(cmd, hide=True, warn=True, **kwargs).stdout  # other options: timeout, warn
        return get_json_or_clean_str(out)

    def get_report_key(self):
        return socket.gethostname()

    def __eq__(self, other):
        return type(self) == type(other)

    @staticmethod
    def get_type():
        return "local"
