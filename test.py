import logging
import os
import platform
import shlex
from abc import abstractmethod
from typing import Dict

import docker
from dotenv import load_dotenv
from fabric import Connection
from kubernetes import client, config
from invoke import run

logging.basicConfig()


class AirflowInfo:
    @abstractmethod
    def get(self):
        pass


class KubernetesAirflowInfo:
    def __init__(self):
        config.load_kube_config()
        self.client = client.CoreV1Api()

    def get(self):
        # https://github.com/kubernetes-client/python/blob/master/examples/pod_exec.py
        return NotImplementedError


class SSHAirflowInfo:
    def get(self):
        return Connection('web1.example.com').run('uname -s', hide=True)


class LocalDockerAirflowInfo:
    def __init__(self):
        self.client = docker.from_env()

    def get(self):
        return NotImplementedError


REQUIRED = [
    ('python', '--version'),
    ('helm', 'version', '--short'),
    ('kubectl', "version", '--client=true', "--short"),
    ('docker', 'version', '--format', 'json'),
    ('astro', 'version'),
    ('docker-compose', '--version')
]
REQUIRED_FOR_CLOUD = {
    "aws": ('aws', '--version'),
    'gcp': ('gcloud', 'version', '--format=json')
}
KUBE = [
    ('kubectl', 'cluster-info')
]
# airflow config list
# airflow dags report -o plain
# airflow info
# helm ls -aA -o json
# [{"name":"astronomer","namespace":"astronomer","revision":"5","updated":"2021-06-21 13:50:37.588983 -0400 EDT","status":"deployed","chart":"astronomer-0.25.2","app_version":"0.25.2"},{"name":"aws-efs-csi-driver","namespace":"kube-system","revision":"2","updated":"2021-07-02 13:08:37.766251 -0400 EDT","status":"deployed","chart":"aws-efs-csi-driver-2.1.3","app_version":"1.3.2"},{"name":"boreal-declination-7615","namespace":"astronomer-boreal-declination-7615","revision":"6","updated":"2021-06-21 17:54:16.734691146 +0000 UTC","status":"deployed","chart":"airflow-0.19.0","app_version":"2.0.0"}]


CONFIG_FILE = './config.yaml'
OS = [
    os.name,
    platform.system(),
    platform.release()
]


def get_airflow_info():
    pass
    # scenario 1: get airflow infos from an Astro EE installation
    # scenario 2: get airflow infos from an ssh-connect-able installation
    #
    # for each airflow:
    # - get executor
    # - get dags
    # - get success/fails of operators
    # - get operator types
    # - get connections
    # - get configurations (beyond defaults)


def get_astro_info():
    # https://docs.google.com/document/d/1yYTxkhfpRRrhcgjUN8YP3pYKNLDGmnYazAGNgZuhrNI/edit
    # get cloud provider
    # get kubernetes version
    # get database sanity
    #   rf"""kubectl run psql --rm -it --restart=Never -n {namespace} --image {image} --command -- psql {conn.out} -qtc "select 'healthy';" """
    # get certificate sanity
    # get cluster size (kubectl get nodes?)
    # get astro config file
    pass


def get_input() -> Dict:
    load_dotenv()
    return {}


def main():
    for required in REQUIRED:
        logging.debug(f"Fetching '{required}'")
        try:
            run(shlex.join(required))
        except Exception as e:
            logging.exception(e)
    print(OS)


if __name__ == '__main__':
    main()
