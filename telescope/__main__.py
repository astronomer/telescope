from typing import Any, Dict, List

import json
import logging
import multiprocessing
from datetime import datetime

import click as click
from click import Path, echo
from click.exceptions import UsageError
from halo import Halo

import telescope
from telescope.functions.astronomer_enterprise import get_helm_info
from telescope.functions.cluster_info import cluster_info
from telescope.getter_util import gather_getters, get_from_getter
from telescope.getters.kubernetes import KubernetesGetter

log = logging.getLogger(__name__)

d = {"show_default": True, "show_envvar": True}
fd = {"show_default": True, "show_envvar": True, "is_flag": True}


# noinspection PyUnusedLocal
def version(ctx, self, value):
    if not value or ctx.resilient_parsing:
        return
    echo(f"Telescope, version {telescope.version}")
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
def cli(
    use_local: bool,
    use_docker: bool,
    use_kubernetes: bool,
    label_selector: str,
    hosts_file: str,
    parallelism: int,
    organization_name: str,
    data_file: str,
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
    data = {"report_date": date, "telescope_version": telescope.version, "organization_name": organization_name}

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

    # get all the Airflow Reports at once, in parallel
    spinner = Halo(
        text=f"Gathering Data from {len(all_getters)} Airflow Deployments...",
        spinner="moon",  # dots12, growHorizontal, arc, moon
    )
    spinner.start()

    # Check for helm secrets or get cluster info if we know we are running with Kubernetes
    if any([type(g) == KubernetesGetter for g in all_getters]):
        try:
            data["verify"] = get_helm_info()
        except:
            pass
        try:
            data["cluster_info"] = cluster_info()
        except:
            pass

    try:
        with multiprocessing.Pool(parallelism) as p:
            results: List[Dict[Any, Any]] = p.map(get_from_getter, all_getters)
        spinner.succeed(text=f"Gathering Data from {len(all_getters)} Airflow Deployments!")
    except (KeyboardInterrupt, SystemExit):
        spinner.stop()
        raise
    except Exception as e:
        spinner.fail(text=str(e))

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


if __name__ == "__main__":
    multiprocessing.freeze_support()
    cli(auto_envvar_prefix="TELESCOPE")
