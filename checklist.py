import os
from shutil import which
from typing import Optional, IO, List

import click
from click import echo, secho
from delegator import run

from labe.utils import log_and_run, log_error_and_exit, log_success

REQUIRED = [('python', '--version'), ('helm', 'version --short'), ('kubectl', "version --client=true --short"),
            ('docker', '--version'), ('astro', 'version', False), ('docker-compose', '--version', False)]
REQUIRED_FOR_CLOUD = {"aws": ('aws', '--version')}


def check_kubectl(file_output: Optional[IO]):
    secho("Checking Kubernetes Cluster Connectivity...", bold=True)
    cmd = log_and_run('kubectl cluster-info')
    if cmd.ok:
        log_success("Kubernetes Cluster accessible", file_output)
    else:
        log_error_and_exit("Kubernetes Cluster inaccessible", file_output, cmd)


def check_psql(file_output: Optional[IO], namespace: str = 'astronomer', secret: str = 'astronomer-bootstrap', image: str = 'bitnami/postgresql'):
    secho("Launching a Kubernetes Pod to check Database Connectivity from the Cluster...", bold=True)
    template = "{{.data.connection | base64decode }}"
    conn = log_and_run(f"kubectl get secret -n {namespace} {secret} --template='{template}' | sed 's/?.*//g'")
    if conn.ok:
        log_success(f'{secret} secret found in {namespace} namespace', file_output)
        cmd = log_and_run(
            rf"""kubectl run psql --rm -it --restart=Never -n {namespace} --image {image} --command -- psql {conn.out} -qtc "select 'healthy';" """
        )
        if cmd.ok and 'healthy' in cmd.out:
            log_success("Database connectivity established", file_output)
        else:
            log_error_and_exit("Database connectivity check failed", file_output, cmd)
    else:
        log_error_and_exit(f"{secret} does not exist in {namespace} namespace", file_output)


def check_cert(file_output: Optional[IO], secret='astronomer-tls', namespace='astronomer'):
    secho("Checking TLS Certificates...", bold=True)
    crt = log_and_run(
        rf"""kubectl get secret -n {namespace} {secret} -o json | jq -r '.data."tls.crt"' | base64 -d > c.crt"""
    )
    key = log_and_run(
        rf"""kubectl get secret -n {namespace} {secret} -o json | jq -r '.data."tls.key"' | base64 -d > c.key"""
    )
    if not crt.ok or not key.ok:
        log_error_and_exit(f"{secret} does not exist in {namespace} namespace", file_output, crt if not crt.ok else key)
    else:
        openssl_crt = log_and_run("openssl x509 -in c.crt -text -noout")
        if openssl_crt.ok:
            log_success(f"TLS Certificate in {secret} verified in namespace {namespace}", file_output)
        else:
            log_error_and_exit("TLS Certificate verification failure", file_output, openssl_crt)
        if os.path.isfile('c.crt'):
            os.remove('c.crt')

        openssl_key = log_and_run("openssl rsa -in c.key -check")
        if openssl_key.ok:
            log_success(f"TLS Private Key in {secret} verified in namespace {namespace}", file_output)
        else:
            log_error_and_exit("TLS Private Key verification failure", file_output, openssl_key)
        if os.path.isfile('c.key'):
            os.remove('c.key')


def check_installed_locally(file_output: Optional[IO]):
    secho("Checking local requirements...", bold=True)
    required = REQUIRED
    if os.getenv('CLOUD') and REQUIRED_FOR_CLOUD.get(os.getenv('CLOUD')):
        echo(f"CLOUD ({os.getenv('CLOUD')}) variable found, adding requirements...")
        required.append(REQUIRED_FOR_CLOUD.get(os.getenv('CLOUD'), []))

    for r in required:
        [requirement, version_cmd] = r[0:2]
        is_required = len(r) < 3 or r[2]  # if there's a False-y in the third position, or just no third thing
        if not which(requirement):
            log_error_and_exit(f'{requirement} is not installed!', file_output, warning=not is_required)
        else:
            version = run(requirement + ' ' + version_cmd).out.strip().replace("\n", "")
            log_success(f"{requirement} installed!   {version}", file_output)


@click.command()
@click.option('--output', '-o', 'output', type=click.Path(file_okay=True, dir_okay=False),
              help="Output Report to a file")
@click.option('--checks', '-c', default=['local', 'kube', 'psql', 'cert'], multiple=True,
              help="Inclusive list of checks to run - default: all")
def install_checklist(output: Optional[str], checks: List[str]):
    """Check requirements before installation

\b
Example - labe install-checklist -c kube -c local
'kube' - Check for Kubernetes Connectivity
'local' - Check local environment for compatibility
'psql' - Check for PostgreSQL connectivity from within Kubernetes
'cert' - Check for TLS certificate correctness from within Kubernetes
'dns' - Check that DNS is accessible"""
    file_output = open(output, 'w') if output else None  # stdout
    if 'local' in checks:
        check_installed_locally(file_output)
    else:
        secho('Skipping Local Environment Checks', bold=True)

    if 'kube' in checks:
        check_kubectl(file_output)
    else:
        secho('Skipping Kubernetes Connectivity Check', bold=True)

    if 'psql' in checks:
        check_psql(file_output)
    else:
        secho('Skipping PostgreSQL Connectivity Check', bold=True)

    if 'cert' in checks:
        check_cert(file_output)
    else:
        secho('Skipping Certificate Check', bold=True)

    if 'dns' in checks:
        raise NotImplementedError()  # TODO


# airflow config list
# airflow dags report -o plain
# airflow info
# helm ls -aA -o json
# [{"name":"astronomer","namespace":"astronomer","revision":"5","updated":"2021-06-21 13:50:37.588983 -0400 EDT","status":"deployed","chart":"astronomer-0.25.2","app_version":"0.25.2"},{"name":"aws-efs-csi-driver","namespace":"kube-system","revision":"2","updated":"2021-07-02 13:08:37.766251 -0400 EDT","status":"deployed","chart":"aws-efs-csi-driver-2.1.3","app_version":"1.3.2"},{"name":"boreal-declination-7615","namespace":"astronomer-boreal-declination-7615","revision":"6","updated":"2021-06-21 17:54:16.734691146 +0000 UTC","status":"deployed","chart":"airflow-0.19.0","app_version":"2.0.0"}]
