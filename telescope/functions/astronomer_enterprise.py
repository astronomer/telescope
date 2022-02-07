import logging

from telescope.getters.local import LocalGetter
from telescope.util import deep_clean

log = logging.getLogger(__name__)


def verify(getter: LocalGetter):
    """Requires a LocalGetter, runs Helm locally, which connects to a kube cluster
    runs "helm ls -aA -o json" and "helm get values"
    :return {"helm": [<helm install details>, ...]}
    """
    helm_installs = getter.get("helm ls -aA -o json")
    for helm_install in helm_installs:
        install_name = helm_install.get("name", "")
        install_namespace = helm_install.get("namespace", "")
        # if install_name == 'astronomer' or install_namespace == 'astronomer':
        helm_values = getter.get(f"helm get values {install_name} -n {install_namespace} -o json")
        try:
            for v in [
                ["data", "metadataConnection", "pass"],
                ["data", "resultBackendConnection", "pass"],
                ["data", "resultBackendConnection", "password"],
                ["elasticsearch", "connection", "pass"],
                ["fernetKey"],
                ["registry", "connection", "pass"],
                ["webserver", "defaultUser", "password"],
            ]:
                deep_clean(v, helm_values)
        except Exception as e:
            log.exception(e)
        helm_install["values"] = helm_values
    return {"helm": helm_installs}


def precheck():
    pass

    #  database: rf"""kubectl run psql --rm -it --restart=Never -n {namespace} --image {image} --command -- psql {conn.out} -qtc "select 'healthy';" """
    #  certificate: ""
