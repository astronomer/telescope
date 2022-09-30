from typing import List, Type, Union

from abc import abstractmethod


class Getter:
    @abstractmethod
    def get(self, cmd: Union[List[str], str]) -> Union[dict, str]:
        pass

    @abstractmethod
    def get_report_key(self):
        pass

    @abstractmethod
    def __eq__(self, other):
        pass

    @staticmethod
    @abstractmethod
    def get_type():
        pass


# noinspection PyUnresolvedReferences
def get_for_type(host_type: str) -> Type[Union["KubernetesGetter", "LocalDockerGetter", "LocalGetter", "SSHGetter"]]:
    from astronomer_telescope.getters.docker import LocalDockerGetter
    from astronomer_telescope.getters.kubernetes import KubernetesGetter
    from astronomer_telescope.getters.local import LocalGetter
    from astronomer_telescope.getters.ssh import SSHGetter

    if host_type == "kubernetes":
        return KubernetesGetter
    elif host_type == "docker":
        return LocalDockerGetter
    elif host_type == "local":
        return LocalGetter
    elif host_type == "ssh":
        return SSHGetter
    else:
        raise RuntimeError(f"Unknown host type: {host_type}")
