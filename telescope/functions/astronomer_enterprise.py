import logging

from invoke import run

from telescope.util import deep_clean, get_json_or_clean_str

log = logging.getLogger(__name__)

TO_CHECK = {
    "python": "python --version",
    "helm": "helm version --short",
    "kubectl": "kubectl version --client=true --short",
    "docker": "docker version --format json",
    "astro": "astro version",
    "docker-compose": "docker-compose --version",
    "os": "uname -a",
    "aws": "aws --version",
    "aws_id": "aws sts get-caller-identity",
    "gcp": "gcloud version --format=json",
    "az": "az version",
}


def versions():
    """Uses invoke.run directly to get versions of potentially installed tools"""
    return {program: get_json_or_clean_str(run(cmd, hide=True, warn=True).stdout) for program, cmd in TO_CHECK.items()}


def verify():
    """Uses invoke.run directly, runs Helm locally, which connects to a kube cluster
    runs "helm ls -aA -o json" and "helm get values"
    :return {"helm": [<helm install details>, ...]}
    """
    helm_installs = get_json_or_clean_str(run("helm ls -aA -o json").stdout)
    for helm_install in helm_installs:
        install_name = helm_install.get("name", "")
        install_namespace = helm_install.get("namespace", "")
        # if install_name == 'astronomer' or install_namespace == 'astronomer':
        helm_values = get_json_or_clean_str(
            run(f"helm get values {install_name} -n {install_namespace} -o json").stdout
        )
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
    raise NotImplementedError

    #  database: rf"""kubectl run psql --rm -it --restart=Never -n {namespace} --image {image} --command -- psql {conn.out} -qtc "select 'healthy';" """
    #  certificate: ""
    # set -euxo pipefail
    #
    # kubectl get secret -n astronomer astronomer-tls -o json | jq -r '.data."tls.crt"' | base64 -d > server.crt
    # kubectl get secret -n astronomer astronomer-tls -o json | jq -r '.data."tls.key"' | base64 -d > server.key
    # openssl x509 -noout -subject -in server.crt
    # openssl rsa -noout -modulus -in server.key | openssl md5 > key.md5
    # openssl x509 -noout -modulus -in server.crt | openssl md5 > crt.md5
    # diff key.md5 crt.md5
