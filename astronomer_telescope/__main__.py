from typing import Any, Dict, List, Optional

import json
import logging
import multiprocessing
import os
import shutil
from datetime import datetime
from functools import partial
from urllib.request import urlopen

import click as click
import requests
from click import Path, echo
from click.exceptions import Exit, UsageError
from halo import Halo

import astronomer_telescope
from astronomer_telescope.config import AIRGAPPED, REPORT_PACKAGE, REPORT_PACKAGE_URL
from astronomer_telescope.functions.cluster_info import cluster_info
from astronomer_telescope.getter_util import gather_getters, get_from_getter
from astronomer_telescope.getters.kubernetes import KubernetesGetter

log = logging.getLogger(__name__)
log.setLevel(os.getenv("LOG_LEVEL", logging.WARNING))
log.addHandler(logging.StreamHandler())

d = {"show_default": True, "show_envvar": True}
fd = {"show_default": True, "show_envvar": True, "is_flag": True}


# noinspection PyUnusedLocal
def version(ctx, self, value):
    if not value or ctx.resilient_parsing:
        return
    echo(f"Telescope, version {astronomer_telescope.version}")
    ctx.exit()


@click.command()
@click.option(
    "--version", is_flag=True, expose_value=False, is_eager=True, help="Show the version and exit.", callback=version
)
@click.option("--local", "use_local", **fd, help="Airflow Reporting for local Airflow")
@click.option("--docker", "use_docker", **fd, help="Autodiscovery and Airflow reporting for local Docker")
@click.option("--kubernetes", "use_kubernetes", **fd, help="Autodiscovery and Airflow reporting for Kubernetes")
@click.option(
    "-l", "--label-selector", **d, default="component=scheduler", help="Label selector for Kubernetes Autodiscovery"
)
@click.option(
    "--dag-obfuscation",
    **fd,
    default=False,
    help="Obfuscate DAG IDs and filenames, keeping first and last 3 chars; my-dag-name => my-*****ame",
)
@click.option(
    "--dag-obfuscation-fn",
    **d,
    default=None,
    help="Obfuscate DAG IDs, defining a custom function that takes a string and returns a string; "
    "'lambda x: x[-5:]' would return only the last five letters of the DAG ID and fileloc",
)
@click.option(
    "-f",
    "--hosts-file",
    **d,
    default=None,
    type=Path(exists=True, readable=True),
    help="Hosts file to pass in various types of hosts (ssh, kubernetes, docker) - See README.md for sample",
)
@click.option(
    "-p",
    "--parallelism",
    show_default="Number CPU",
    type=int,
    default=None,
    help="How many cores to use for multiprocessing",
)
@click.option(
    "-n",
    "--organization-name",
    **d,
    type=str,
    help="Denote who this report belongs to, e.g. a company name",
)
@click.option(
    "-o",
    "--data-file",
    **d,
    type=Path(),
    help="Data file to write intermediate gathered data, can be '-' for stdout",
)
@click.option(
    "-u",
    "--presigned-url",
    **d,
    type=str,
    help="URL to write data directly to - given by an Astronomer Representative",
)
def telescope(
    use_local: bool,
    use_docker: bool,
    use_kubernetes: bool,
    label_selector: str,
    dag_obfuscation: bool,
    dag_obfuscation_fn: Optional[str],
    hosts_file: str,
    parallelism: int,
    organization_name: str,
    data_file: str,
    presigned_url: str,
) -> None:
    """Telescope - A tool to observe distant (or local!) Airflow installations, and gather usage metadata"""
    # date is today
    date = datetime.utcnow().isoformat()[:10]
    # or date is from the file parts, with organization name
    if data_file:
        try:
            # TODO - add path validation here
            # e.g. 1970-01-01.Astronomer.data.json
            [date, org] = data_file.replace(".json", "").replace(".data", "").split(".")
            organization_name = org
        except Exception as e:
            log.error(e)

    # prompt for Org if not found and not passed in
    if not organization_name:
        organization_name = click.prompt("Organization Name", type=str)

    # Initialize data with a few items
    data = {
        "report_date": date,
        "telescope_version": astronomer_telescope.version,
        "organization_name": organization_name,
    }

    # if the data file name wasn't given - assemble it
    if not data_file:
        data_file = f"{data['report_date']}.{data['organization_name']}.data.json"

    log.info(f"Gathering data and saving to {data_file} ...")

    # flatten getters - for multiproc
    all_getters = [
        getter
        for (_, getters) in gather_getters(use_local, use_docker, use_kubernetes, hosts_file, label_selector).items()
        for getter in getters
    ]
    if not len(all_getters):
        raise UsageError("No Airflow Deployments found, exiting...")

    # Check for helm secrets or get cluster info if we know we are running with Kubernetes
    if any(type(g) == KubernetesGetter for g in all_getters):
        cluster_spinner = Halo(
            text="Gathering cluster info",
            spinner="dots",
        )
        cluster_spinner.start()
        try:
            data["cluster_info"] = cluster_info()
            cluster_spinner.succeed()
        except Exception as e:
            cluster_spinner.warn("gathering cluster info failed")
            log.debug(e)
            data["cluster_info"] = {"error": str(e)}

        if AIRGAPPED:
            with urlopen(REPORT_PACKAGE_URL) as response, open(REPORT_PACKAGE, "wb") as out_file:
                shutil.copyfileobj(response, out_file)

    # get all the Airflow Reports at once, in parallel
    spinner = Halo(
        text=f"Gathering data from {len(all_getters)} Airflow Deployments...\n",
        spinner="moon",  # dots12, growHorizontal, arc, moon
    )
    spinner.start()
    try:
        if dag_obfuscation_fn:
            dag_obfuscation_fn = eval(dag_obfuscation_fn)
        get_from_getters_with_obfuscation = partial(
            get_from_getter, dag_obfuscation=dag_obfuscation, dag_obfuscation_fn=dag_obfuscation_fn
        )
        with multiprocessing.Pool(parallelism) as p:
            results: List[Dict[Any, Any]] = p.map(get_from_getters_with_obfuscation, all_getters)
        if all("error" in r for result in results for r in result.values()):
            raise RuntimeError("Unable to gather results, run with LOG_LEVEL=DEBUG for more information - exiting!")
        spinner.succeed(text=f"Data gathered from {len(all_getters)} Airflow Deployments!")
    except (KeyboardInterrupt, SystemExit) as e:
        spinner.stop()
        raise Exit(1) from e
    except Exception as e:
        spinner.fail(text=str(e))
        raise Exit(1) from e
    finally:
        if AIRGAPPED:
            os.remove(REPORT_PACKAGE)

    # unflatten and assemble into report
    for result in results:
        for (host_type, getter_key, key), value in result.items():
            if host_type not in data:
                data[host_type] = {}

            if getter_key not in data[host_type]:
                data[host_type][getter_key] = {}

            data[host_type][getter_key][key] = value

    log.info(f"Writing data to {data_file} ...")
    with click.open_file(data_file, "w") as output:
        output.write(json.dumps(data, default=str))
    if presigned_url:
        log.info(f"Uploading to {presigned_url} ...")
        requests.put(url=presigned_url, data=open(data_file))


if __name__ == "__main__":
    multiprocessing.freeze_support()
    telescope(auto_envvar_prefix="TELESCOPE")
